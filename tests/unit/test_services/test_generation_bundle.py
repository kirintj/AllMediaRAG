"""Tests for GenerationBundle.

Verifies that the GenerationBundle adapter correctly wraps the existing
GenerationService to satisfy the GenerationBundleProtocol contract,
including streaming generation, citation verification, and error handling.

TDD note: these tests are written BEFORE the implementation.  They
define the expected behaviour; the concrete class is built to make
them pass.

Why mock at the GenerationService level:
    GenerationService internally orchestrates prompt building, LLM
    streaming, Self-RAG reflection, and citation verification.
    Mocking all of them in every test is fragile and couples tests
    to service internals.  Instead, we mock GenerationService.query_stream
    and CitationVerifier.verify as black boxes and verify that
    GenerationBundle correctly wraps their output and converts raw
    exceptions into GenerationError.

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

from core.services.exceptions import GenerationError


# ---------------------------------------------------------------------------
# Helpers for building mock infrastructure
# ---------------------------------------------------------------------------


def _make_infra() -> MagicMock:
    """Build a minimal mock InfraBundle for GenerationBundle tests.

    Why mock at this level:
        GenerationBundle delegates to GenerationService and
        CitationVerifier via InfraBundle.  We mock InfraBundle so the
        bundle can be constructed without a fully wired infrastructure.
    """
    infra = MagicMock()
    infra.settings.CITATION_VERIFY_ENABLED = False
    infra.settings.SELF_RAG_ENABLED = False
    infra.settings.MULTIMODAL_GENERATION = False
    return infra


# ---------------------------------------------------------------------------
# Sample data that GenerationService.query_stream yields
# ---------------------------------------------------------------------------


def _fake_stream(chunks: list[str], sources: list[dict] | None = None):
    """Simulate GenerationService.query_stream yielding SSE-like dicts.

    Each intermediate yield carries ``answer_chunk`` and ``full_answer``.
    The final yield carries ``done=True`` and optional ``verification``.
    """
    sources = sources or [{"source": "paper.pdf", "section": "Intro", "text": "chunk text..."}]
    full = ""
    for chunk in chunks:
        full += chunk
        yield {
            "answer_chunk": chunk,
            "full_answer": full,
            "sources": sources,
        }
    yield {
        "answer_chunk": "",
        "full_answer": full,
        "sources": sources,
        "verification": {"confidence": 0.85, "hallucination_risk": "low"},
        "done": True,
    }


# ---------------------------------------------------------------------------
# TestGenerationBundle
# ---------------------------------------------------------------------------


class TestGenerationBundle:
    """Core behaviour tests for the GenerationBundle adapter."""

    @patch("core.services.generation_bundle.CitationVerifier")
    @patch("core.services.generation_bundle.GenerationService")
    def test_generate_should_return_answer(
        self, MockGenService, MockCitationVerifier,
    ):
        """generate() must delegate to GenerationService.query_stream,
        collect streamed chunks, and yield SSE-style dicts including
        the final result with ``done=True``.

        Why this test matters:
            The API layer streams generate() output as Server-Sent Events.
            If chunks are not forwarded correctly, the frontend receives
            incomplete or missing answer text.
        """
        from core.services.generation_bundle import GenerationBundle

        sources = [
            {"source": "paper.pdf", "section": "Intro", "text": "chunk text..."},
        ]
        MockGenService.return_value.query_stream.return_value = _fake_stream(
            ["RAG is ", "Retrieval-Augmented ", "Generation."],
            sources,
        )

        infra = _make_infra()
        bundle = GenerationBundle(infra)

        results = list(bundle.generate("What is RAG?", [{"text": "context", "metadata": {}}]))

        # Must have at least one intermediate chunk and one final done marker
        assert len(results) >= 2, (
            f"Expected at least 2 yields (chunks + done), got {len(results)}"
        )
        # Final result must signal completion
        final = results[-1]
        assert final.get("done") is True, (
            "Final yield must contain 'done': True"
        )
        # Final result must contain the full assembled answer
        assert "RAG" in final.get("full_answer", ""), (
            f"full_answer should contain the answer, got {final.get('full_answer')}"
        )
        # Sources must be forwarded from the underlying service
        assert len(final.get("sources", [])) > 0, (
            "Final yield must include sources from retrieval"
        )

    @patch("core.services.generation_bundle.CitationVerifier")
    @patch("core.services.generation_bundle.GenerationService")
    def test_generate_should_handle_errors(
        self, MockGenService, MockCitationVerifier,
    ):
        """generate() must wrap unexpected failures in GenerationError
        rather than letting raw exceptions propagate.

        Why this test matters:
            The API layer catches GenerationError to return a clean 500
            response.  If a raw LLM provider or network error leaks
            through, the FastAPI error handler produces an opaque stack
            trace instead of a structured JSON error.
        """
        from core.services.generation_bundle import GenerationBundle

        def _failing_stream(*args, **kwargs):
            raise RuntimeError("LLM provider unavailable")
            yield  # make it a generator

        MockGenService.return_value.query_stream.return_value = _failing_stream()

        infra = _make_infra()
        bundle = GenerationBundle(infra)

        with pytest.raises(GenerationError) as exc_info:
            list(bundle.generate("test query", []))

        # The original cause must be preserved for debugging
        assert exc_info.value.__cause__ is not None, (
            "GenerationError should chain the original exception"
        )
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    @patch("core.services.generation_bundle.CitationVerifier")
    @patch("core.services.generation_bundle.GenerationService")
    def test_verify_citation_should_delegate(
        self, MockGenService, MockCitationVerifier,
    ):
        """verify_citation() must delegate to CitationVerifier.verify
        and return its result as-is.

        Why this test matters:
            The API layer calls verify_citation() independently for
            audit logging or on-demand re-checks.  If delegation is
            wrong, the API returns stale or incorrect verification data.
        """
        from core.services.generation_bundle import GenerationBundle

        expected_verification = {
            "verified": True,
            "confidence": 0.92,
            "citations": [{"marker": "[来源 1]", "index": 1, "position": 0}],
            "hallucination_risk": "low",
            "unsupported_claims": [],
        }
        MockCitationVerifier.return_value.verify.return_value = expected_verification

        infra = _make_infra()
        bundle = GenerationBundle(infra)

        sources = [{"source": "paper.pdf", "text": "context text"}]
        result = bundle.verify_citation("The answer", sources)

        # Must return the verifier's result unchanged
        assert result == expected_verification, (
            f"Expected verifier result, got {result}"
        )
        # The verifier must have been called with correct arguments
        MockCitationVerifier.return_value.verify.assert_called_once_with(
            "The answer", sources,
        )

    @patch("core.services.generation_bundle.CitationVerifier")
    @patch("core.services.generation_bundle.GenerationService")
    def test_verify_citation_wraps_unexpected_errors(
        self, MockGenService, MockCitationVerifier,
    ):
        """verify_citation() must wrap non-GenerationError exceptions as
        GenerationError so the API layer has a single exception type to
        catch, consistent with the Bundle contract.

        Why this test matters:
            CitationVerifier.verify may raise raw infrastructure errors
            (e.g. LLM provider timeout, network failure).  The Bundle
            must convert these into GenerationError so the API error
            handler produces a clean JSON response instead of a stack
            trace.
        """
        from core.services.generation_bundle import GenerationBundle

        MockCitationVerifier.return_value.verify.side_effect = (
            RuntimeError("LLM provider timeout")
        )

        infra = _make_infra()
        bundle = GenerationBundle(infra)

        with pytest.raises(GenerationError) as exc_info:
            bundle.verify_citation("The answer", [{"text": "src"}])

        # The original cause must be preserved for debugging
        assert exc_info.value.__cause__ is not None, (
            "GenerationError should chain the original exception"
        )
        assert isinstance(exc_info.value.__cause__, RuntimeError)

    @patch("core.services.generation_bundle.CitationVerifier")
    @patch("core.services.generation_bundle.GenerationService")
    def test_verify_citation_passes_through_existing_generation_error(
        self, MockGenService, MockCitationVerifier,
    ):
        """verify_citation() must re-raise an existing GenerationError
        as-is (not double-wrap it) so that the error chain stays clean
        and callers see a single GenerationError, not
        GenerationError(GenerationError(...)).

        Why this test matters:
            If an upstream component (e.g. a future LLM wrapper) already
            raises GenerationError, re-wrapping would corrupt the error
            chain and make debugging harder.
        """
        from core.services.generation_bundle import GenerationBundle

        original_error = GenerationError("upstream generation failure")
        MockCitationVerifier.return_value.verify.side_effect = original_error

        infra = _make_infra()
        bundle = GenerationBundle(infra)

        with pytest.raises(GenerationError) as exc_info:
            bundle.verify_citation("The answer", [{"text": "src"}])

        # Must be the exact same exception object, not a new wrapper
        assert exc_info.value is original_error, (
            "verify_citation should pass through existing GenerationError "
            "without double-wrapping"
        )
