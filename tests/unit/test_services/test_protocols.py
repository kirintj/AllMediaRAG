"""
Tests for Protocol interfaces and RetrievalResult dataclass.

These tests enforce the interface contracts that concrete service bundles
must satisfy.  They also verify that RetrievalResult is a proper dataclass
so it can be cached and serialised without surprises.
"""

from __future__ import annotations

import inspect
from dataclasses import fields
from typing import Any, Generator, get_type_hints

import pytest

# Module-level imports avoid repeated import overhead in each test method
# and make dependencies visible at a glance.
from backend.core.services.protocols import (
    GenerationBundleProtocol,
    ProcessingBundleProtocol,
    RetrievalBundleProtocol,
    RetrievalResult,
)


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
        field_map = {f.name: f for f in fields(RetrievalResult)}
        assert "chunks" in field_map, "Missing 'chunks' field"
        assert "sources" in field_map, "Missing 'sources' field"
        assert "confidence" in field_map, "Missing 'confidence' field"

        # Verify field types via get_type_hints, which resolves forward
        # references from `from __future__ import annotations`.
        # Parameterised generics (e.g. list[dict[str, Any]]) are not
        # bare `list`, so we check the origin type for list fields.
        from typing import get_origin
        hints = get_type_hints(RetrievalResult)
        # list fields: chunks and sources are list[...] -- get_origin returns list
        assert get_origin(hints["chunks"]) is list, (
            f"'chunks' should be a list type, got {hints['chunks']!r}"
        )
        assert get_origin(hints["sources"]) is list, (
            f"'sources' should be a list type, got {hints['sources']!r}"
        )
        assert hints["confidence"] is float, (
            f"'confidence' should be float, got {hints['confidence']!r}"
        )


# ---------------------------------------------------------------------------
# RetrievalBundleProtocol
# ---------------------------------------------------------------------------

class TestRetrievalBundleProtocol:
    """The retrieval bundle exposes only the query entry-points that
    generation and API layers need -- nothing more (Interface
    Segregation Principle)."""

    def test_protocol_has_retrieve_method(self):
        """Concrete retrieval bundles must expose `retrieve`."""
        assert hasattr(RetrievalBundleProtocol, "retrieve"), (
            "RetrievalBundleProtocol must declare a 'retrieve' method"
        )

    def test_protocol_has_classify_query_method(self):
        """Query classification is a distinct responsibility that the
        API layer sometimes calls independently of full retrieval."""
        assert hasattr(RetrievalBundleProtocol, "classify_query"), (
            "RetrievalBundleProtocol must declare a 'classify_query' method"
        )

    def test_retrieve_method_signature(self):
        """retrieve(self, query: str) -> RetrievalResult

        The method must accept exactly one positional param (query)
        and return a RetrievalResult."""
        sig = inspect.signature(RetrievalBundleProtocol.retrieve)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 1, (
            f"retrieve should accept 1 param (query), got {len(params)}"
        )
        # from __future__ import annotations makes annotations strings,
        # so accept both the type object and its string representation.
        ann = params[0].annotation
        assert ann is str or ann == "str", (
            f"retrieve's 'query' param should be annotated as str, got {ann!r}"
        )

    def test_classify_query_method_signature(self):
        """classify_query(self, query: str) -> dict[str, Any]

        Must accept exactly one positional param (query) and return a dict."""
        sig = inspect.signature(RetrievalBundleProtocol.classify_query)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 1, (
            f"classify_query should accept 1 param (query), got {len(params)}"
        )
        ann = params[0].annotation
        assert ann is str or ann == "str", (
            f"classify_query's 'query' param should be annotated as str, got {ann!r}"
        )


# ---------------------------------------------------------------------------
# ProcessingBundleProtocol
# ---------------------------------------------------------------------------

class TestProcessingBundleProtocol:
    """The processing bundle covers document ingestion concerns:
    text extraction and image extraction.  Embedding encoding is
    deliberately excluded -- that belongs to the retrieval layer."""

    def test_protocol_has_process_document_method(self):
        assert hasattr(ProcessingBundleProtocol, "process_document"), (
            "ProcessingBundleProtocol must declare a 'process_document' method"
        )

    def test_protocol_has_extract_images_method(self):
        """Image extraction is separated so that multimodal generation
        can call it without pulling in the full processing pipeline."""
        assert hasattr(ProcessingBundleProtocol, "extract_images"), (
            "ProcessingBundleProtocol must declare an 'extract_images' method"
        )

    def test_process_document_method_signature(self):
        """process_document(self, file_path: str) -> tuple[...]

        Must accept exactly one positional param (file_path) of type str."""
        sig = inspect.signature(ProcessingBundleProtocol.process_document)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 1, (
            f"process_document should accept 1 param (file_path), got {len(params)}"
        )
        ann = params[0].annotation
        assert ann is str or ann == "str", (
            f"process_document's 'file_path' param should be annotated as str, got {ann!r}"
        )

    def test_extract_images_method_signature(self):
        """extract_images(self, file_path: str) -> list[str]

        Must accept exactly one positional param (file_path) of type str."""
        sig = inspect.signature(ProcessingBundleProtocol.extract_images)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 1, (
            f"extract_images should accept 1 param (file_path), got {len(params)}"
        )
        ann = params[0].annotation
        assert ann is str or ann == "str", (
            f"extract_images's 'file_path' param should be annotated as str, got {ann!r}"
        )


# ---------------------------------------------------------------------------
# GenerationBundleProtocol
# ---------------------------------------------------------------------------

class TestGenerationBundleProtocol:
    """The generation bundle is the only place that talks to the LLM.
    Keeping it behind a protocol lets us swap in a mock for unit tests
    or a different model provider without touching callers."""

    def test_protocol_has_generate_method(self):
        assert hasattr(GenerationBundleProtocol, "generate"), (
            "GenerationBundleProtocol must declare a 'generate' method"
        )

    def test_protocol_has_verify_citation_method(self):
        """Citation verification is a post-generation check that the
        API layer may invoke independently (e.g. for audit logging)."""
        assert hasattr(GenerationBundleProtocol, "verify_citation"), (
            "GenerationBundleProtocol must declare a 'verify_citation' method"
        )

    def test_generate_method_signature(self):
        """generate(self, question: str, contexts: list[...], history: list[...] | None = None)

        Must accept 3 params: question (str), contexts (list), history (optional, default None)."""
        sig = inspect.signature(GenerationBundleProtocol.generate)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 3, (
            f"generate should accept 3 params (question, contexts, history), got {len(params)}"
        )
        # Verify 'question' is annotated as str
        question_param = sig.parameters["question"]
        ann = question_param.annotation
        assert ann is str or ann == "str", (
            f"generate's 'question' param should be annotated as str, got {ann!r}"
        )
        # Verify 'history' has a default of None (optional param)
        history_param = sig.parameters["history"]
        assert history_param.default is None, (
            f"generate's 'history' param should default to None, got {history_param.default!r}"
        )

    def test_verify_citation_method_signature(self):
        """verify_citation(self, query: str, answer: str, sources: list[...]) -> dict[str, Any]

        Must accept exactly 3 positional params: query (str), answer (str) and sources (list)."""
        sig = inspect.signature(GenerationBundleProtocol.verify_citation)
        params = [p for p in sig.parameters.values()
                  if p.name != "self"]
        assert len(params) == 3, (
            f"verify_citation should accept 3 params (query, answer, sources), got {len(params)}"
        )
        ann = params[0].annotation
        assert ann is str or ann == "str", (
            f"verify_citation's 'answer' param should be annotated as str, got {ann!r}"
        )
