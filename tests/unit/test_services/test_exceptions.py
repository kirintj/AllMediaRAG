"""Tests for Bundle exception hierarchy.

Verifies that the custom exception classes follow a clean inheritance
structure so callers can catch domain-specific errors or a single base
class depending on their needs.
"""

import pytest

from backend.core.services.exceptions import (
    BundleError,
    GenerationError,
    ProcessingError,
    RetrievalError,
)


class TestExceptionHierarchy:
    """Verify subclass relationships across the hierarchy."""

    def test_retrieval_error_is_bundle_error(self):
        """RetrievalError must be catchable as a BundleError."""
        assert issubclass(RetrievalError, BundleError)

    def test_processing_error_is_bundle_error(self):
        """ProcessingError must be catchable as a BundleError."""
        assert issubclass(ProcessingError, BundleError)

    def test_generation_error_is_bundle_error(self):
        """GenerationError must be catchable as a BundleError."""
        assert issubclass(GenerationError, BundleError)


class TestExceptionBehavior:
    """Verify runtime behaviour: message preservation and chaining."""

    def test_exception_message_preserved(self):
        """The message passed at construction must survive retrieval via str().

        Each exception subclass should behave like a standard Exception --
        the first positional argument is the human-readable message, and
        ``str(exc)`` must return it unchanged.
        """
        message = "vector store timed out"
        for cls in (BundleError, RetrievalError, ProcessingError, GenerationError):
            exc = cls(message)
            assert str(exc) == message

    def test_exception_chaining(self):
        """Exceptions must support PEP-3134 chaining via ``raise ... from``.

        Callers often wrap a low-level error in a domain exception; the
        original cause must remain accessible through ``__cause__`` so that
        stack traces are informative.
        """
        original = ValueError("disk full")
        with pytest.raises(ProcessingError) as exc_info:
            try:
                raise original
            except ValueError as e:
                raise ProcessingError("document ingestion failed") from e

        assert exc_info.value.__cause__ is original
