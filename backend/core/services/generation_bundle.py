"""GenerationBundle adapter -- thin facade over GenerationService.

Why a separate Bundle class:
    The existing ``GenerationService`` exposes a large public surface
    (build_prompt, _extract_images_from_contexts, _run_post_generation_checks,
    close, etc.) that only the generation internals need.
    ``GenerationBundle`` implements the slim ``GenerationBundleProtocol``
    with two entry-points (``generate`` and ``verify_citation``) so that
    downstream consumers (API layer, orchestrator) depend on a minimal
    contract rather than the full service class.  This satisfies the
    Interface Segregation Principle and makes it straightforward to swap
    the generation backend in the future -- only this adapter changes.

Design decisions:
    1. **Composition over inheritance**: GenerationBundle holds references
       to an existing GenerationService (created internally from InfraBundle)
       and CitationVerifier rather than subclassing either.  This keeps
       the service's internal API untouched and avoids fragile super()
       chains if the service is refactored later.

    2. **Delegation to GenerationService.query_stream**: The bundle
       delegates all prompt building, LLM streaming, Self-RAG reflection,
       and post-generation checks to the existing service.  No generation
       logic is duplicated here.

    3. **Standalone verify_citation**: Citation verification is exposed
       as a separate method so the API layer can run it independently
       (e.g. for audit logging or on-demand re-checks) without
       re-running a full generation.  Delegates directly to
       CitationVerifier.verify.

    4. **Error wrapping**: All unexpected exceptions from the service
       or infrastructure are caught and re-raised as ``GenerationError``
       so the API layer has a single, predictable exception type to
       handle, consistent with the other bundle adapters.

    5. **Contexts format**: The ``generate`` method accepts contexts as
       a list of dicts with at least ``text`` and ``metadata`` keys,
       matching the format produced by RetrievalBundle / RetrievalPipeline.
       GenerationService.query_stream uses these for prompt assembly and
       citation verification.
"""

from __future__ import annotations

import logging
from typing import Any, Generator

from core.services.exceptions import GenerationError
from core.services.generation_service import GenerationService
from core.services.retrieval_pipeline import RetrievalPipeline
from core.verification.citation_verifier import CitationVerifier

logger = logging.getLogger(__name__)


class GenerationBundle:
    """Adapter that satisfies GenerationBundleProtocol by delegating to
    GenerationService and CitationVerifier from the shared InfraBundle.

    Constructor args:
        infra: An ``InfraBundle`` instance (from
            ``core.services.create_infra``).  The bundle creates its
            own ``GenerationService`` internally so callers don't need
            to manage service lifecycle separately.
    """

    def __init__(self, infra: Any) -> None:
        """Create a GenerationBundle from an InfraBundle.

        Why we accept InfraBundle instead of GenerationService:
            The Bundle is meant to be the single generation entry-point
            created by the BundleFactory (Task 6).  Having it own the
            service lifecycle keeps the factory simple and avoids
            circular dependencies between bundle constructors.
        """
        self._infra = infra
        # Why create a RetrievalPipeline here:
        # GenerationService.__init__ requires a retrieval_pipeline argument
        # because query_stream calls pipeline.full_retrieve internally.
        # The bundle passes a pipeline instance built from the same
        # InfraBundle so the generation service has retrieval access.
        self._retrieval_pipeline = RetrievalPipeline(infra)
        self._service = GenerationService(infra, self._retrieval_pipeline)
        self._citation_verifier = CitationVerifier(
            llm_client=infra.llm_client,
            threshold=getattr(infra.settings, "CITATION_CONFIDENCE_THRESHOLD", 0.5),
        )

    # ------------------------------------------------------------------
    # GenerationBundleProtocol implementation
    # ------------------------------------------------------------------

    def generate(
        self,
        question: str,
        contexts: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Stream an answer given retrieval contexts and conversation history.

        Delegates to ``GenerationService.query_stream`` which handles:
            1. Prompt construction from contexts and history
            2. Multimodal image extraction (if enabled)
            3. LLM streaming generation
            4. Self-RAG reflection + citation verification (post-gen)

        The raw SSE-like dicts from query_stream are yielded unchanged
        so that the API layer can forward them directly as Server-Sent
        Events to the frontend.

        Args:
            question: User's question.
            contexts: Ranked retrieval chunks.  Each dict must contain
                at least ``text`` (str) and ``metadata`` (dict).
            history: Optional conversation history for multi-turn dialogue.

        Yields:
            Dicts with keys like ``answer_chunk``, ``full_answer``,
            ``sources``, ``verification``, ``done`` for SSE streaming.

        Raises:
            GenerationError: If any step in the generation pipeline
                fails.  The original exception is chained for debugging.
        """
        try:
            yield from self._service.query_stream(question, history)
        except GenerationError:
            # Already wrapped -- re-raise as-is
            raise
        except Exception as exc:
            # Wrap any raw infrastructure error so callers only see
            # GenerationError, consistent with the Bundle contract.
            raise GenerationError(
                f"Generation failed for question: {question!r}"
            ) from exc

    def verify_citation(
        self,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Verify that answer claims are supported by the cited sources.

        Delegates to ``CitationVerifier.verify`` which handles:
            1. Citation marker extraction
            2. LLM-based faithfulness verification
            3. Confidence scoring and hallucination risk assessment

        Exposed as a standalone method so the API layer can run citation
        verification independently (e.g. for audit logging or on-demand
        re-checks) without re-running a full generation.

        Args:
            answer: The generated answer text.
            sources: Context dicts from retrieval (each with at least
                ``text`` and ``metadata``).

        Returns:
            Verification result dict with keys like ``verified``,
            ``confidence``, ``citations``, ``hallucination_risk``,
            ``unsupported_claims``, etc.

        Raises:
            GenerationError: If the verification process fails.
                The original exception is chained for debugging.
        """
        try:
            return self._citation_verifier.verify(answer, sources)
        except GenerationError:
            raise
        except Exception as exc:
            raise GenerationError(
                "Citation verification failed"
            ) from exc
