"""Bundle service exception hierarchy.

Design rationale
----------------
A single base class (``BundleError``) lets callers catch *all*
service-layer exceptions in one clause when they need a catch-all
(e.g. the FastAPI global error handler).  Subclasses allow
fine-grained catching closer to the call site so that retry logic,
alerting, or user-facing messages can vary by failure domain.

Inheritance layout::

    Exception
      └─ BundleError        # catch-all for the service layer
           ├─ RetrievalError  # vector-store lookups, reranking, embedding
           ├─ ProcessingError # document parsing, chunking, ingestion
           └─ GenerationError # LLM calls, prompt assembly, streaming

Each subclass is intentionally empty -- its *type* is the signal.
Extra context (query, document id, provider name) should be attached
via the standard ``raise ... from`` chain or by passing a structured
message string.  This avoids coupling the exception hierarchy to any
specific request schema.
"""

from __future__ import annotations


class BundleError(Exception):
    """Base exception for all Bundle service-layer failures.

    Catch this when you want a single handler for any service error
    (e.g. in an API endpoint or background worker).
    """


class RetrievalError(BundleError):
    """Raised when retrieval operations fail.

    Covers vector-store queries, embedding generation, reranking,
    and any other step in the retrieval pipeline.
    """


class ProcessingError(BundleError):
    """Raised when document processing fails.

    Covers parsing, chunking, metadata extraction, and ingestion
    into the vector store.
    """


class GenerationError(BundleError):
    """Raised when text generation fails.

    Covers LLM provider calls, prompt assembly, streaming, and
    response post-processing.
    """
