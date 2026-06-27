"""Protocol interfaces for RAG service bundles.

Why a separate protocols module:
    Concrete service classes (RetrievalPipeline, DocumentProcessor,
    GenerationService) currently live in different files and carry
    large public surfaces.  Defining slim Protocol interfaces here
    lets the API layer and cross-service wiring depend on *contracts*
    rather than implementations, satisfying the Interface Segregation
    Principle and making future refactors (e.g. swapping retrieval
    backends) a matter of changing one import.

Design decisions:
    1. RetrievalResult is a plain dataclass, not a TypedDict or Pydantic
       model.  Dataclasses are hashable-by-default (when fields are
       hashable), support ``dataclasses.asdict`` for serialisation,
       and have zero third-party dependencies -- important because
       retrieval results may cross process boundaries in a future
       distributed deployment.

    2. Each Protocol declares only the methods that *other* bundles or
       the API layer actually call.  Private helpers, configuration
       plumbing, and close/shutdown are deliberately omitted so that
       implementors keep freedom to restructure internals.

    3. Method signatures use concrete types (str, list, dict) rather
       than generics to keep the surface approachable for the team.
       Narrower return types (e.g. RetrievalResult instead of dict)
       are used where the contract is unambiguous.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generator, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Shared data structures
# ---------------------------------------------------------------------------


@dataclass
class RetrievalResult:
    """Uniform return envelope for every retrieval operation.

    Fields:
        chunks: Ranked list of context chunk dicts.  Each dict contains
            at least ``content`` (str) and ``metadata`` (dict).  The exact
            shape is an internal detail of the retrieval layer; downstream
            consumers treat it as opaque.
        sources: Deduplicated source metadata suitable for citation
            display.  Populated by the retrieval pipeline so that the
            generation layer does not need to re-parse chunk metadata.
        confidence: Float in [0, 1] summarising retrieval quality.
            Used by Self-RAG reflection and the refetch-with-expanded-query
            logic to decide whether results are good enough to answer.
    """

    chunks: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    confidence: float


# ---------------------------------------------------------------------------
# Bundle protocols (Interface Segregation Principle)
# ---------------------------------------------------------------------------


@runtime_checkable
class RetrievalBundleProtocol(Protocol):
    """Contract for the retrieval bundle.

    Exposes only the two entry-points that the generation service and
    the REST API need:
      - ``retrieve``: the full retrieval pipeline (classify, route,
        rewrite, fetch, fuse, rerank).
      - ``classify_query``: standalone query classification so that the
        API can return routing info without running retrieval.

    Why ``runtime_checkable``:
        Allows ``isinstance(obj, RetrievalBundleProtocol)`` checks in
        dependency-injection wiring and integration tests.
    """

    def retrieve(self, query: str) -> RetrievalResult:
        """Run the full retrieval pipeline and return ranked results.

        Args:
            query: Raw user question.

        Returns:
            RetrievalResult with ranked chunks, deduped sources, and
            a confidence score.
        """
        ...

    def classify_query(self, query: str) -> dict[str, Any]:
        """Classify query intent without running retrieval.

        Args:
            query: Raw user question.

        Returns:
            Dict with at least ``type`` (str) and ``confidence`` (float).
        """
        ...


@runtime_checkable
class ProcessingBundleProtocol(Protocol):
    """Contract for the document processing bundle.

    Covers text extraction (process_document) and image extraction
    (extract_images).  Embedding encoding is deliberately excluded --
    it belongs to the retrieval layer which owns the embedding model
    lifecycle.
    """

    def process_document(
        self, file_path: str
    ) -> tuple[list[dict[str, Any]], list[list[float] | None]]:
        """Extract and chunk text from a document file.

        Args:
            file_path: Absolute or project-relative path to the document.

        Returns:
            Tuple of (chunks, embeddings) where chunks is a list of
            dicts with ``content`` and ``metadata`` keys, and embeddings
            is a parallel list of embedding vectors (or None for chunks
            that failed encoding).
        """
        ...

    def extract_images(self, file_path: str) -> list[str]:
        """Extract image paths or base64 representations from a document.

        Separated from process_document so that multimodal generation
        can retrieve images without pulling in the full chunking pipeline.

        Args:
            file_path: Path to the source document.

        Returns:
            List of image identifiers (file paths or base64 strings).
        """
        ...


@runtime_checkable
class GenerationBundleProtocol(Protocol):
    """Contract for the generation bundle.

    This is the only bundle that talks to the LLM.  Keeping it behind
    a protocol lets us swap in a mock for unit tests or a different
    model provider without touching callers.
    """

    def generate(
        self,
        question: str,
        contexts: list[dict[str, Any]],
        history: list[dict[str, Any]] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Stream an answer given retrieval contexts and conversation history.

        Args:
            question: User's question.
            contexts: Ranked retrieval chunks (from RetrievalResult.chunks).
            history: Optional conversation history for multi-turn dialogue.

        Yields:
            Dicts with keys like ``answer_chunk``, ``full_answer``,
            ``sources``, ``verification``, ``done`` for SSE streaming.
        """
        ...

    def verify_citation(
        self,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Verify that answer claims are supported by the cited sources.

        Exposed as a standalone method so that the API layer can run
        citation verification independently (e.g. for audit logging or
        on-demand re-checks).

        Args:
            answer: The generated answer text.
            sources: Source metadata from retrieval.

        Returns:
            Verification result dict with at least ``score`` (float)
            and ``details`` (list).
        """
        ...
