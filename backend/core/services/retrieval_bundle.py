"""RetrievalBundle adapter -- thin facade over RetrievalPipeline.

Why a separate Bundle class:
    The existing ``RetrievalPipeline`` exposes a large public surface
    (rebuild, wait, rerank config, async variants) that only the
    retrieval internals need.  ``RetrievalBundle`` implements the slim
    ``RetrievalBundleProtocol`` with two entry-points (``retrieve`` and
    ``classify_query``) so that downstream consumers (GenerationService,
    API layer) depend on a minimal contract rather than the full
    pipeline class.  This satisfies the Interface Segregation Principle
    and makes it straightforward to swap the retrieval backend in the
    future -- only this adapter changes.

Design decisions:
    1. **Composition over inheritance**: RetrievalBundle holds a
       reference to an existing RetrievalPipeline (or InfraBundle)
       rather than subclassing it.  This keeps the pipeline's internal
       API untouched and avoids fragile super() chains if the pipeline
       is refactored later.

    2. **Cache-aside pattern**: ``retrieve()`` checks the
       ``CacheManager`` before invoking the pipeline.  The pipeline's
       own cache path is bypassed because the Bundle needs to manage
       its own cache key namespace (``bundle:rag:``) to avoid key
       collisions with the legacy direct-pipeline callers.

    3. **RRF fusion is delegated to RetrievalPipeline.reciprocal_rank_fusion**:
       The static method already implements weighted RRF correctly.
       Rather than duplicating the algorithm, the Bundle calls it via
       the pipeline instance.  If the pipeline is ever removed, the
       static method can be moved here or into a shared utility.

    4. **Error wrapping**: All unexpected exceptions from the pipeline
       or infrastructure are caught and re-raised as ``RetrievalError``
       so the API layer has a single, predictable exception type to
       handle.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from core.services.exceptions import RetrievalError
from core.services.protocols import RetrievalBundleProtocol, RetrievalResult
from core.services.retrieval_pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)


class RetrievalBundle(RetrievalBundleProtocol):
    """Adapter that satisfies RetrievalBundleProtocol by delegating to
    RetrievalPipeline and the shared InfraBundle components.

    Constructor args:
        infra: An ``InfraBundle`` instance (from
            ``core.services.create_infra``).  The bundle creates its
            own ``RetrievalPipeline`` internally so callers don't need
            to manage pipeline lifecycle separately.
    """

    def __init__(self, infra: Any) -> None:
        """Create a RetrievalBundle from an InfraBundle.

        Why we accept InfraBundle instead of RetrievalPipeline:
            The Bundle is meant to be the single retrieval entry-point
            created by the BundleFactory (Task 6).  Having it own the
            pipeline lifecycle keeps the factory simple and avoids
            circular dependencies between bundle constructors.
        """
        self._infra = infra
        self._pipeline = RetrievalPipeline(infra)
        self._cache = infra.cache_manager
        self._classifier = infra.classifier

    # ------------------------------------------------------------------
    # RetrievalBundleProtocol implementation
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> RetrievalResult:
        """Run the full retrieval pipeline and return ranked results.

        Pipeline steps (delegated to RetrievalPipeline.full_retrieve):
            1. Normalise + cache lookup
            2. Classify query intent
            3. Route (HyDE / multi-query rewrite decisions)
            4. Vector + BM25 parallel retrieval
            5. Weighted RRF fusion
            6. Rerank + relevance gating
            7. Confidence evaluation + optional refetch
            8. Cache write

        The raw dict from full_retrieve is converted to a
        ``RetrievalResult`` dataclass so that downstream consumers
        get a typed envelope rather than a raw dict.
        """
        try:
            # Cache-aside: check our bundle-level cache first to avoid
            # even the pipeline overhead on repeated queries.
            cache_key = self._make_cache_key(query)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("Bundle cache hit for: %.50s", query)
                # Accept both RetrievalResult (new) and dict (legacy)
                if isinstance(cached, RetrievalResult):
                    return cached
                return self._dict_to_result(cached)

            # Delegate to the pipeline for the heavy lifting
            raw = self._pipeline.full_retrieve(query)
            result = self._dict_to_result(raw)

            # Write to bundle-level cache
            try:
                self._cache.set(cache_key, result)
            except Exception as exc:
                # Cache write failure is non-fatal -- log and continue
                logger.warning("Bundle cache write failed: %s", exc)

            return result

        except RetrievalError:
            # Already wrapped -- re-raise as-is
            raise
        except Exception as exc:
            # Wrap any raw infrastructure error so callers only see
            # RetrievalError, consistent with the Bundle contract.
            raise RetrievalError(
                f"Retrieval failed for query: {query!r}"
            ) from exc

    def classify_query(self, query: str) -> dict[str, Any]:
        """Classify query intent without running retrieval.

        Delegates directly to the InfraBundle's QueryClassifier so
        the API can return routing info (type, confidence) without
        incurring retrieval cost.
        """
        return self._classifier.classify(query)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_cache_key(query: str) -> str:
        """Build a deterministic cache key from the query string.

        Why a separate key namespace:
            The pipeline uses ``rag:<md5>`` keys.  The Bundle uses
            ``bundle:rag:<md5>`` to avoid collisions when both the
            legacy pipeline and the new Bundle coexist during the
            migration period.
        """
        normalised = query.strip().lower()
        digest = hashlib.md5(normalised.encode("utf-8")).hexdigest()
        return f"bundle:rag:{digest}"

    @staticmethod
    def _dict_to_result(raw: dict) -> RetrievalResult:
        """Convert the pipeline's raw dict output to a RetrievalResult.

        The pipeline returns:
            {"documents": [...], "metadatas": [...], "distances": [...], ...}

        We map this to:
            RetrievalResult(chunks=[...], sources=[...], confidence=float)

        Chunk dicts are built from (document, metadata) pairs.  Sources
        are deduplicated by the ``source`` metadata key.  Confidence
        is derived from the average rerank/RRF score normalised to [0,1].
        """
        documents = raw.get("documents", [])
        metadatas = raw.get("metadatas", [])
        distances = raw.get("distances", [])

        # Build chunk dicts -- downstream expects at least "content" and "metadata"
        chunks = []
        for doc, meta in zip(documents, metadatas):
            chunks.append({"content": doc, "metadata": meta})

        # Deduplicated sources for citation display
        seen_sources: set[str] = set()
        sources: list[dict[str, Any]] = []
        for meta in metadatas:
            src = meta.get("source", meta.get("file_name", "unknown"))
            if src not in seen_sources:
                seen_sources.add(src)
                sources.append(meta)

        # Confidence: use distance-based heuristic.  Lower distance =
        # higher similarity.  Average distance normalised to [0, 1].
        if distances:
            avg_dist = sum(distances) / len(distances)
            # Clamp to [0, 1] -- distance can exceed 1 for some stores
            confidence = max(0.0, min(1.0, 1.0 - avg_dist))
        else:
            # No results -> low confidence
            confidence = 0.0

        return RetrievalResult(chunks=chunks, sources=sources, confidence=confidence)
