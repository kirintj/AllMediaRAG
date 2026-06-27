"""Tests for ProcessingBundle.

Verifies that the ProcessingBundle adapter correctly wraps the existing
DocumentProcessor to satisfy the ProcessingBundleProtocol contract,
including document processing, image extraction, and error handling.

TDD note: these tests are written BEFORE the implementation.  They
define the expected behaviour; the concrete class is built to make
them pass.

Why mock at the DocumentProcessor level:
    DocumentProcessor internally orchestrates file reading, HTML parsing,
    chunking strategies, OCR providers, and VLM pipelines.  Mocking all
    of them in every test is fragile and couples tests to processor
    internals.  Instead, we mock DocumentProcessor.process_file and
    verify that ProcessingBundle correctly wraps its output and
    converts raw exceptions into ProcessingError.

Why use ``core.services.*`` imports (not ``backend.core.services.*``):
    The implementation lives in ``backend/core/services/`` and uses
    ``from core.services.X import Y`` (the conftest adds ``backend/``
    to sys.path).  The test must use the same import path so that
    ``isinstance`` and ``is`` checks resolve to the same class objects.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from core.services.exceptions import ProcessingError
from core.services.protocols import ProcessingBundleProtocol


# ---------------------------------------------------------------------------
# Helpers for building mock infrastructure
# ---------------------------------------------------------------------------


def _make_infra() -> MagicMock:
    """Build a minimal mock InfraBundle for ProcessingBundle tests.

    Why mock at this level:
        ProcessingBundle delegates to DocumentProcessor and InfraBundle.
        We mock InfraBundle so the bundle can be constructed without
        a fully wired infrastructure.
    """
    infra = MagicMock()
    return infra


# ---------------------------------------------------------------------------
# Sample data that DocumentProcessor.process_file returns
# ---------------------------------------------------------------------------

_SAMPLE_CHUNKS = [
    {"text": "chunk about RAG", "metadata": {"source": "paper.pdf", "section": "Intro"}},
    {"text": "chunk about vectors", "metadata": {"source": "paper.pdf", "section": "Methods"}},
]
_SAMPLE_EMBEDDINGS: list[list[float] | None] = [
    [0.1, 0.2, 0.3],
    None,
]


# ---------------------------------------------------------------------------
# TestProcessingBundle
# ---------------------------------------------------------------------------


class TestProcessingBundle:
    """Core behaviour tests for the ProcessingBundle adapter."""

    def test_process_document_should_return_chunks(self):
        """process_document() must delegate to DocumentProcessor.process_file
        and return the (chunks, embeddings) tuple unchanged.

        Why this test matters:
            The API layer and ingestion pipeline depend on process_document()
            returning a well-formed tuple.  If chunks is empty or embeddings
            are missing, downstream vector store insertion and indexing fail
            silently with partial data.
        """
        from core.services.processing_bundle import ProcessingBundle

        infra = _make_infra()
        bundle = ProcessingBundle(infra)

        # Mock the DocumentProcessor's process_file method
        infra.document_processor.process_file.return_value = (
            _SAMPLE_CHUNKS,
            _SAMPLE_EMBEDDINGS,
        )

        chunks, embeddings = bundle.process_document("paper.pdf")

        # Chunks must match the processor output
        assert len(chunks) == 2, (
            f"Expected 2 chunks, got {len(chunks)}"
        )
        assert chunks == _SAMPLE_CHUNKS, (
            "process_document should return chunks unchanged from DocumentProcessor"
        )
        # Embeddings must match the processor output
        assert len(embeddings) == 2, (
            f"Expected 2 embeddings, got {len(embeddings)}"
        )
        # The processor must have been called exactly once
        infra.document_processor.process_file.assert_called_once_with("paper.pdf")

    def test_process_document_should_handle_errors(self):
        """process_document() must wrap unexpected failures in ProcessingError
        rather than letting raw exceptions propagate.

        Why this test matters:
            The API layer catches ProcessingError to return a clean 500
            response.  If a raw file-not-found or encoding error leaks
            through, the FastAPI error handler produces an opaque stack
            trace instead of a structured JSON error.
        """
        from core.services.processing_bundle import ProcessingBundle

        infra = _make_infra()
        bundle = ProcessingBundle(infra)

        # Simulate a low-level failure from DocumentProcessor
        infra.document_processor.process_file.side_effect = (
            FileNotFoundError("document not found: missing.pdf")
        )

        with pytest.raises(ProcessingError) as exc_info:
            bundle.process_document("missing.pdf")

        # The original cause must be preserved for debugging
        assert exc_info.value.__cause__ is not None, (
            "ProcessingError should chain the original exception"
        )
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_extract_images_should_delegate(self):
        """extract_images() must process the document and collect image paths
        from chunk metadata (the ``image_path`` key added by RegionChunker).

        Separated from process_document so that multimodal generation
        can retrieve images without pulling in the full chunking pipeline.

        Why this implementation approach:
            DocumentProcessor doesn't expose a standalone image extraction
            method.  Image paths are embedded in chunk metadata by the
            VLMExtractor + RegionChunker pipeline.  The bundle processes
            the file via process_file and collects all non-empty
            ``image_path`` values from chunk metadata, which is the
            most reliable way to get image references without duplicating
            the extraction logic.

        Why this test matters:
            The GenerationService needs image paths for multimodal
            prompt assembly.  If extract_images doesn't delegate
            correctly, multimodal generation silently falls back to
            text-only mode, degrading answer quality for visual content.
        """
        from core.services.processing_bundle import ProcessingBundle

        infra = _make_infra()
        bundle = ProcessingBundle(infra)

        # Chunks with image_path in metadata (as produced by RegionChunker)
        chunks_with_images = [
            {"text": "figure 1", "metadata": {"source": "report.pdf", "image_path": "images/fig1.png"}},
            {"text": "text chunk", "metadata": {"source": "report.pdf"}},
            {"text": "figure 2", "metadata": {"source": "report.pdf", "image_path": "images/fig2.png"}},
        ]
        infra.document_processor.process_file.return_value = (
            chunks_with_images,
            [None, None, None],
        )

        images = bundle.extract_images("report.pdf")

        # Only chunks with image_path should be collected
        assert images == ["images/fig1.png", "images/fig2.png"], (
            f"Expected 2 image paths, got {images}"
        )
        # The processor must have been called to process the file
        infra.document_processor.process_file.assert_called_once_with("report.pdf")
