"""ProcessingBundle adapter -- thin facade over DocumentProcessor.

Why a separate Bundle class:
    The existing ``DocumentProcessor`` exposes a large public surface
    (parse_html, split_by_headings, semantic_chunk, read_file, etc.)
    that only the processing internals need.  ``ProcessingBundle``
    implements the slim ``ProcessingBundleProtocol`` with two
    entry-points (``process_document`` and ``extract_images``) so that
    downstream consumers (API layer, ingestion pipeline, multimodal
    generation) depend on a minimal contract rather than the full
    processor class.  This satisfies the Interface Segregation Principle
    and makes it straightforward to swap the processing backend in the
    future -- only this adapter changes.

Design decisions:
    1. **Composition over inheritance**: ProcessingBundle holds a
       reference to an existing DocumentProcessor (via InfraBundle)
       rather than subclassing it.  This keeps the processor's internal
       API untouched and avoids fragile super() chains if the processor
       is refactored later.

    2. **Delegation to process_file**: The bundle delegates to
       ``DocumentProcessor.process_file`` which already handles
       format detection, VLMExtractor routing, and the legacy HTML
       pipeline.  No processing logic is duplicated here.

    3. **Image extraction via chunk metadata**: Image paths are not
       a first-class output of DocumentProcessor -- they are embedded
       in chunk metadata by the VLMExtractor + RegionChunker pipeline.
       ``extract_images`` processes the file and collects all non-empty
       ``image_path`` values from chunk metadata.  This avoids
       duplicating the extraction logic while keeping the contract
       simple for multimodal generation callers.

    4. **Error wrapping**: All unexpected exceptions from the processor
       or infrastructure are caught and re-raised as ``ProcessingError``
       so the API layer has a single, predictable exception type to
       handle, consistent with the other bundle adapters.
"""

from __future__ import annotations

import logging
from typing import Any

from core.services.exceptions import ProcessingError
from core.services.protocols import ProcessingBundleProtocol

logger = logging.getLogger(__name__)


class ProcessingBundle(ProcessingBundleProtocol):
    """Adapter that satisfies ProcessingBundleProtocol by delegating to
    DocumentProcessor and the shared InfraBundle components.

    Constructor args:
        infra: An ``InfraBundle`` instance (from
            ``core.services.create_infra``).  The bundle accesses
            ``infra.document_processor`` for file processing.
    """

    def __init__(self, infra: Any) -> None:
        """Create a ProcessingBundle from an InfraBundle.

        Why we accept InfraBundle instead of DocumentProcessor:
            The Bundle is meant to be the single processing entry-point
            created by the BundleFactory (Task 6).  Having it access
            the processor through InfraBundle keeps the factory simple
            and ensures all bundles share the same dependency wiring
            pattern.
        """
        self._infra = infra
        self._processor = infra.document_processor

    # ------------------------------------------------------------------
    # ProcessingBundleProtocol implementation
    # ------------------------------------------------------------------

    def process_document(
        self, file_path: str
    ) -> tuple[list[dict[str, Any]], list[list[float] | None]]:
        """Extract and chunk text from a document file.

        Delegates to ``DocumentProcessor.process_file`` which handles
        format detection, VLMExtractor routing for images/PDFs, and the
        legacy HTML parsing + semantic chunking pipeline for other
        formats.

        Args:
            file_path: Absolute or project-relative path to the document.

        Returns:
            Tuple of (chunks, embeddings) where chunks is a list of
            dicts with ``text`` and ``metadata`` keys, and embeddings
            is a parallel list of embedding vectors (or None for chunks
            that need subsequent encoding).

        Raises:
            ProcessingError: If any step in the processing pipeline
                fails.  The original exception is chained for debugging.
        """
        try:
            chunks, embeddings = self._processor.process_file(file_path)
            logger.info(
                "Processed %s: %d chunks, %d embeddings",
                file_path, len(chunks), len(embeddings),
            )
            return chunks, embeddings
        except ProcessingError:
            # Already wrapped -- re-raise as-is
            raise
        except Exception as exc:
            # Wrap any raw infrastructure error so callers only see
            # ProcessingError, consistent with the Bundle contract.
            raise ProcessingError(
                f"Document processing failed for: {file_path!r}"
            ) from exc

    def extract_images(self, file_path: str) -> list[str]:
        """Extract image paths from a document.

        Processes the file via DocumentProcessor and collects all
        non-empty ``image_path`` entries from chunk metadata.  These
        paths are produced by the VLMExtractor + RegionChunker pipeline
        when processing images and PDFs with visual content.

        Separated from process_document so that multimodal generation
        can retrieve images without pulling in the full chunking
        pipeline or needing to re-process the document.

        Args:
            file_path: Path to the source document.

        Returns:
            List of image path strings (relative to image store base
            dir).  Returns an empty list if no images were extracted.

        Raises:
            ProcessingError: If document processing fails during image
                extraction.
        """
        try:
            chunks, _ = self._processor.process_file(file_path)
            image_paths = [
                chunk["metadata"]["image_path"]
                for chunk in chunks
                if chunk.get("metadata", {}).get("image_path")
            ]
            logger.info(
                "Extracted %d images from %s", len(image_paths), file_path
            )
            return image_paths
        except ProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError(
                f"Image extraction failed for: {file_path!r}"
            ) from exc
