"""Tests for RetrievalBundle.

Verifies that the RetrievalBundle adapter correctly wraps the existing
RetrievalPipeline to satisfy the RetrievalBundleProtocol contract,
including result fusion, caching, error handling, and query classification.

TDD note: these tests are written BEFORE the implementation.  They
define the expected behaviour; the concrete class is built to make
them pass.

Why mock at the RetrievalPipeline level:
    The pipeline internally orchestrates classifier, router, rewriters,
    vector store, BM25, reranker, and cache manager.  Mocking all of
    them in every test is fragile and couples tests to pipeline internals.
    Instead, we mock RetrievalPipeline.full_retrieve as a black box and
    verify that RetrievalBundle correctly wraps its output, handles
    caching, and converts dicts to RetrievalResult.

Why use ``core.services.*`` imports (not ``backend.core.services.*``):
    The implementation lives in ``backend/core/services/`` and uses
    ``from core.services.X import Y`` (the conftest adds ``backend/``
    to sys.path).  The test must use the same import path so that
    ``isinstance`` and ``is`` checks resolve to the same class objects.
    Using ``backend.core.services.*`` would create a second module entry
    in ``sys.modules`` pointing to the same file but with different
    class identities, breaking type checks.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from core.services.exceptions import RetrievalError
from core.services.protocols import RetrievalBundleProtocol, RetrievalResult


# ---------------------------------------------------------------------------
# Helpers for building mock infrastructure
# ---------------------------------------------------------------------------


def _make_infra(
    *,
    cache_hit: bool = False,
    cache_store: dict | None = None,
) -> MagicMock:
    """Build a minimal mock InfraBundle.

    Why mock at this level:
        RetrievalBundle delegates to RetrievalPipeline and InfraBundle.
        We mock the InfraBundle but patch RetrievalPipeline at import
        time so the Bundle doesn't need a fully wired pipeline.
    """
    infra = MagicMock()
    infra.classifier.classify.return_value = {
        "type": "factual",
        "confidence": 0.9,
    }

    # Cache mock with controllable get/set behaviour
    if cache_store is None:
        cache_store = {}
    infra.cache_manager.get.side_effect = lambda key: cache_store.get(key)

    def _cache_set(key, value, **kwargs):
        cache_store[key] = value

    infra.cache_manager.set.side_effect = _cache_set

    return infra, cache_store


# ---------------------------------------------------------------------------
# Raw dict that RetrievalPipeline.full_retrieve returns
# ---------------------------------------------------------------------------

_RAW_PIPELINE_RESULT = {
    "documents": ["Chunk A about RAG", "Chunk B about vectors"],
    "metadatas": [
        {"source": "paper_a.pdf", "page": 1},
        {"source": "paper_b.pdf", "page": 3},
    ],
    "distances": [0.3, 0.5],
    "reranked": True,
}


# ---------------------------------------------------------------------------
# TestRetrievalBundle
# ---------------------------------------------------------------------------


class TestRetrievalBundle:
    """Core behaviour tests for the RetrievalBundle adapter."""

    @patch("core.services.retrieval_bundle.RetrievalPipeline")
    def test_retrieve_should_return_results(self, MockPipeline):
        """retrieve() must return a RetrievalResult with chunks, sources, and confidence.

        Why this test matters:
            The GenerationService and API layer depend on retrieve()
            returning a well-formed RetrievalResult.  If chunks is
            empty or confidence is missing, downstream prompt assembly
            and Self-RAG reflection break silently.
        """
        from core.services.retrieval_bundle import RetrievalBundle

        MockPipeline.return_value.full_retrieve.return_value = _RAW_PIPELINE_RESULT

        infra, _ = _make_infra()
        bundle = RetrievalBundle(infra)

        result = bundle.retrieve("What is RAG?")

        # Must return the protocol's dataclass
        assert isinstance(result, RetrievalResult), (
            f"Expected RetrievalResult, got {type(result).__name__}"
        )
        # Chunks must match the pipeline output count
        assert len(result.chunks) == 2, (
            f"Expected 2 chunks, got {len(result.chunks)}"
        )
        # Each chunk must have at least 'content' and 'metadata'
        for chunk in result.chunks:
            assert "content" in chunk, "Chunk missing 'content' key"
            assert "metadata" in chunk, "Chunk missing 'metadata' key"
        # Sources must be deduplicated by source name
        assert len(result.sources) == 2, (
            f"Expected 2 unique sources, got {len(result.sources)}"
        )
        # Confidence must be a float in [0, 1]
        assert isinstance(result.confidence, float), "confidence should be a float"
        assert 0.0 <= result.confidence <= 1.0, (
            f"confidence should be in [0,1], got {result.confidence}"
        )
        # The pipeline must have been called exactly once
        MockPipeline.return_value.full_retrieve.assert_called_once_with("What is RAG?")

    @patch("core.services.retrieval_bundle.RetrievalPipeline")
    def test_retrieve_should_use_cache(self, MockPipeline):
        """retrieve() must return cached results when available, skipping
        the expensive vector + BM25 retrieval.

        Why this test matters:
            Cache hits avoid repeated embedding calls and vector store
            queries.  If the cache path is broken, every request pays
            the full retrieval cost even for repeated queries, which
            degrades latency and increases infrastructure spend.
        """
        from core.services.retrieval_bundle import RetrievalBundle

        infra, cache_store = _make_infra()
        bundle = RetrievalBundle(infra)

        # Pre-populate the bundle-level cache with a known key
        cached_result = RetrievalResult(
            chunks=[{"content": "cached chunk", "metadata": {}}],
            sources=[],
            confidence=0.95,
        )
        cache_key = bundle._make_cache_key("cached query")
        cache_store[cache_key] = cached_result

        result = bundle.retrieve("cached query")

        # Must return the cached object (identity check)
        assert result is cached_result, (
            "Should return the exact cached object, not a copy"
        )
        # The pipeline must NOT have been called (cache hit)
        MockPipeline.return_value.full_retrieve.assert_not_called()

    @patch("core.services.retrieval_bundle.RetrievalPipeline")
    def test_retrieve_should_handle_errors(self, MockPipeline):
        """retrieve() must wrap unexpected failures in RetrievalError
        rather than letting raw exceptions propagate.

        Why this test matters:
            The API layer catches RetrievalError to return a clean 500
            response.  If a raw ChromaDB or network error leaks through,
            the FastAPI error handler produces an opaque stack trace
            instead of a structured JSON error.
        """
        from core.services.retrieval_bundle import RetrievalBundle

        MockPipeline.return_value.full_retrieve.side_effect = (
            RuntimeError("vector store down")
        )

        infra, _ = _make_infra()
        bundle = RetrievalBundle(infra)

        with pytest.raises(RetrievalError) as exc_info:
            bundle.retrieve("this will fail")

        # The original cause must be preserved for debugging
        assert exc_info.value.__cause__ is not None, (
            "RetrievalError should chain the original exception"
        )
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    def test_classify_query_should_delegate(self):
        """classify_query() must delegate to the InfraBundle's classifier
        and return its result unchanged.

        Why this test matters:
            The API layer calls classify_query() independently to
            return routing info without running retrieval.  If the
            delegation is wrong, the API returns stale or default
            classification data.
        """
        from core.services.retrieval_bundle import RetrievalBundle

        infra, _ = _make_infra()
        bundle = RetrievalBundle(infra)

        result = bundle.classify_query("What is machine learning?")

        infra.classifier.classify.assert_called_once_with("What is machine learning?")
        assert isinstance(result, dict), "classify_query should return a dict"
        assert "type" in result, "result must contain 'type' key"
        assert "confidence" in result, "result must contain 'confidence' key"
