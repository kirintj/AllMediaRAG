"""Tests for BundleFactory.

Verifies that the BundleFactory correctly creates RetrievalBundle,
ProcessingBundle, and GenerationBundle from an InfraBundle, centralising
dependency wiring so that callers (API layer, orchestrator) don't need
to know which Bundle classes exist or how to construct them.

TDD note: these tests are written BEFORE the implementation.  They
define the expected behaviour; the concrete class is built to make
them pass.

Why mock at the Bundle class level:
    Each Bundle class (RetrievalBundle, ProcessingBundle, GenerationBundle)
    is already tested in its own test module.  Here we only verify that
    BundleFactory delegates construction correctly -- the internal
    behaviour of each Bundle is out of scope.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_infra() -> MagicMock:
    """Build a minimal mock InfraBundle.

    Why mock at this level:
        BundleFactory accepts an InfraBundle and passes it to each Bundle
        constructor.  We mock InfraBundle so the factory doesn't need
        real embedding services, vector stores, or LLM clients.
    """
    infra = MagicMock(name="InfraBundle")
    return infra


# ---------------------------------------------------------------------------
# TestBundleFactory
# ---------------------------------------------------------------------------


class TestBundleFactory:
    """Core behaviour tests for the BundleFactory."""

    @patch("core.services.bundle_factory.GenerationBundle")
    @patch("core.services.bundle_factory.ProcessingBundle")
    @patch("core.services.bundle_factory.RetrievalBundle")
    def test_create_retrieval_bundle(
        self, MockRetrieval, MockProcessing, MockGeneration
    ):
        """create_retrieval_bundle must construct a RetrievalBundle from
        the InfraBundle and return it.

        Why this test matters:
            The API layer and GenerationService depend on the factory
            producing a correctly wired RetrievalBundle.  If the factory
            passes the wrong object or forgets to construct the bundle,
            retrieval calls fail at runtime with AttributeError.
        """
        from core.services.bundle_factory import BundleFactory

        infra = _make_infra()
        factory = BundleFactory(infra)

        bundle = factory.create_retrieval_bundle()

        # Must construct RetrievalBundle with the InfraBundle
        MockRetrieval.assert_called_once_with(infra)
        # Must return the constructed instance
        assert bundle is MockRetrieval.return_value, (
            "create_retrieval_bundle should return the RetrievalBundle instance"
        )

    @patch("core.services.bundle_factory.GenerationBundle")
    @patch("core.services.bundle_factory.ProcessingBundle")
    @patch("core.services.bundle_factory.RetrievalBundle")
    def test_create_processing_bundle(
        self, MockRetrieval, MockProcessing, MockGeneration
    ):
        """create_processing_bundle must construct a ProcessingBundle from
        the InfraBundle and return it.

        Why this test matters:
            The ingestion pipeline and API layer depend on the factory
            producing a correctly wired ProcessingBundle.  If the factory
            passes the wrong object or forgets to construct the bundle,
            document processing calls fail at runtime.
        """
        from core.services.bundle_factory import BundleFactory

        infra = _make_infra()
        factory = BundleFactory(infra)

        bundle = factory.create_processing_bundle()

        # Must construct ProcessingBundle with the InfraBundle
        MockProcessing.assert_called_once_with(infra)
        # Must return the constructed instance
        assert bundle is MockProcessing.return_value, (
            "create_processing_bundle should return the ProcessingBundle instance"
        )

    @patch("core.services.bundle_factory.GenerationBundle")
    @patch("core.services.bundle_factory.ProcessingBundle")
    @patch("core.services.bundle_factory.RetrievalBundle")
    def test_create_generation_bundle(
        self, MockRetrieval, MockProcessing, MockGeneration
    ):
        """create_generation_bundle must construct a GenerationBundle from
        the InfraBundle and return it.

        Why this test matters:
            The API layer depends on the factory producing a correctly
            wired GenerationBundle.  If the factory passes the wrong
            object or forgets to construct the bundle, streaming
            generation calls fail at runtime.
        """
        from core.services.bundle_factory import BundleFactory

        infra = _make_infra()
        factory = BundleFactory(infra)

        bundle = factory.create_generation_bundle()

        # Must construct GenerationBundle with the InfraBundle
        MockGeneration.assert_called_once_with(infra)
        # Must return the constructed instance
        assert bundle is MockGeneration.return_value, (
            "create_generation_bundle should return the GenerationBundle instance"
        )
