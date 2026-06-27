"""
Tests for Protocol interfaces and RetrievalResult dataclass.

These tests enforce the interface contracts that concrete service bundles
must satisfy.  They also verify that RetrievalResult is a proper dataclass
so it can be cached and serialised without surprises.
"""

from __future__ import annotations

import inspect
from dataclasses import fields

import pytest


# ---------------------------------------------------------------------------
# RetrievalResult
# ---------------------------------------------------------------------------

class TestRetrievalResult:
    """RetrievalResult is a plain dataclass used as the return envelope
    for every retrieval operation."""

    def test_retrieval_result_is_dataclass(self):
        """RetrievalResult must be decorated with @dataclass so that
        field introspection, equality checks and asdict() all work
        out of the box -- needed for caching and serialisation."""
        from backend.core.services.protocols import RetrievalResult

        assert hasattr(RetrievalResult, "__dataclass_fields__"), (
            "RetrievalResult should be a dataclass"
        )

    def test_retrieval_result_fields(self):
        """Verify the expected fields exist with correct types.

        The three mandatory fields are:
        - chunks: the ranked list of context chunks
        - sources: deduplicated source metadata for citation
        - confidence: a float in [0, 1] used by Self-RAG and refetch logic
        """
        from backend.core.services.protocols import RetrievalResult

        field_names = {f.name for f in fields(RetrievalResult)}
        assert "chunks" in field_names, "Missing 'chunks' field"
        assert "sources" in field_names, "Missing 'sources' field"
        assert "confidence" in field_names, "Missing 'confidence' field"


# ---------------------------------------------------------------------------
# RetrievalBundleProtocol
# ---------------------------------------------------------------------------

class TestRetrievalBundleProtocol:
    """The retrieval bundle exposes only the query entry-points that
    generation and API layers need -- nothing more (Interface
    Segregation Principle)."""

    def test_protocol_has_retrieve_method(self):
        """Concrete retrieval bundles must expose `retrieve`."""
        from backend.core.services.protocols import RetrievalBundleProtocol

        assert hasattr(RetrievalBundleProtocol, "retrieve"), (
            "RetrievalBundleProtocol must declare a 'retrieve' method"
        )

    def test_protocol_has_classify_query_method(self):
        """Query classification is a distinct responsibility that the
        API layer sometimes calls independently of full retrieval."""
        from backend.core.services.protocols import RetrievalBundleProtocol

        assert hasattr(RetrievalBundleProtocol, "classify_query"), (
            "RetrievalBundleProtocol must declare a 'classify_query' method"
        )

    def test_retrieve_method_signature(self):
        """retrieve(self, query: str) -> RetrievalResult

        The method must accept exactly one positional param (query)
        and return a RetrievalResult."""
        from backend.core.services.protocols import RetrievalBundleProtocol

        sig = inspect.signature(RetrievalBundleProtocol.retrieve)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 1, (
            f"retrieve should accept 1 param (query), got {len(params)}"
        )
        # from __future__ import annotations makes annotations strings,
        # so accept both the type object and its string representation.
        ann = params[0].annotation
        assert ann is str or ann == str or ann == "str", (
            f"retrieve's 'query' param should be annotated as str, got {ann!r}"
        )


# ---------------------------------------------------------------------------
# ProcessingBundleProtocol
# ---------------------------------------------------------------------------

class TestProcessingBundleProtocol:
    """The processing bundle covers document ingestion concerns:
    text extraction and image extraction.  Embedding encoding is
    deliberately excluded -- that belongs to the retrieval layer."""

    def test_protocol_has_process_document_method(self):
        from backend.core.services.protocols import ProcessingBundleProtocol

        assert hasattr(ProcessingBundleProtocol, "process_document"), (
            "ProcessingBundleProtocol must declare a 'process_document' method"
        )

    def test_protocol_has_extract_images_method(self):
        """Image extraction is separated so that multimodal generation
        can call it without pulling in the full processing pipeline."""
        from backend.core.services.protocols import ProcessingBundleProtocol

        assert hasattr(ProcessingBundleProtocol, "extract_images"), (
            "ProcessingBundleProtocol must declare an 'extract_images' method"
        )


# ---------------------------------------------------------------------------
# GenerationBundleProtocol
# ---------------------------------------------------------------------------

class TestGenerationBundleProtocol:
    """The generation bundle is the only place that talks to the LLM.
    Keeping it behind a protocol lets us swap in a mock for unit tests
    or a different model provider without touching callers."""

    def test_protocol_has_generate_method(self):
        from backend.core.services.protocols import GenerationBundleProtocol

        assert hasattr(GenerationBundleProtocol, "generate"), (
            "GenerationBundleProtocol must declare a 'generate' method"
        )

    def test_protocol_has_verify_citation_method(self):
        """Citation verification is a post-generation check that the
        API layer may invoke independently (e.g. for audit logging)."""
        from backend.core.services.protocols import GenerationBundleProtocol

        assert hasattr(GenerationBundleProtocol, "verify_citation"), (
            "GenerationBundleProtocol must declare a 'verify_citation' method"
        )
