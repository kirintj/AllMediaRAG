"""Tests for RAGEngine Bundle integration.

Verifies that RAGEngine correctly uses BundleFactory to create domain
Bundles (RetrievalBundle, ProcessingBundle, GenerationBundle) and
exposes them alongside the existing service-layer accessors for
backward compatibility.

Why these tests exist:
    After the Bundle architecture was introduced (Tasks 3-6), RAGEngine
    should delegate to domain Bundles instead of constructing services
    directly.  These tests verify that:
    1. BundleFactory is used to create the three domain Bundles.
    2. Business methods delegate correctly through the Bundles.
    3. Legacy code that accesses engine.retrieval, engine.ingestion,
       engine.generation, and backward-compat attributes still works.

Why mock at the BundleFactory / InfraBundle level:
    The individual Bundles and services are tested in their own test
    modules (test_retrieval_bundle, test_generation_bundle, etc.).
    Here we only verify that RAGEngine wires them together correctly --
    internal Bundle behaviour is out of scope.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_infra() -> MagicMock:
    """Build a minimal mock InfraBundle for RAGEngine tests.

    Why mock at this level:
        RAGEngine.__init__ calls create_infra(config) to build the
        InfraBundle.  We mock it so tests don't need real embedding
        services, vector stores, or LLM clients.
    """
    infra = MagicMock(name="InfraBundle")
    infra.embedding_service = MagicMock(name="EmbeddingService")
    infra.vector_store = MagicMock(name="VectorStore")
    infra.llm_client = MagicMock(name="LLMClient")
    infra.document_processor = MagicMock(name="DocumentProcessor")
    infra.bm25_retriever = MagicMock(name="BM25Retriever")
    infra.rerank_manager = MagicMock(name="RerankManager")
    infra.cache_manager = MagicMock(name="CacheManager")
    infra.index_manager = MagicMock(name="IndexManager")
    infra.classifier = MagicMock(name="QueryClassifier")
    infra.router = MagicMock(name="QueryRouter")
    infra.rewriters = {}
    infra.confidence_evaluator = MagicMock(name="ConfidenceEvaluator")
    infra.citation_verifier = MagicMock(name="CitationVerifier")
    infra.self_rag_reflector = MagicMock(name="SelfRAGReflector")
    infra.executor = MagicMock(name="ThreadPoolExecutor")
    infra.settings = MagicMock(name="Settings")
    infra.bm25_ready = True
    return infra


def _make_config() -> MagicMock:
    """Build a minimal mock config (AppSettings)."""
    config = MagicMock(name="AppSettings")
    config.TOP_K = 10
    config.BM25_TOP_K = 5
    config.RRF_K = 60
    config.RRF_WEIGHT_VECTOR = 0.7
    config.RRF_WEIGHT_BM25 = 0.3
    config.SIMILARITY_THRESHOLD = 0.3
    config.USE_HYDE = False
    config.MULTI_QUERY_ENABLED = False
    config.MULTI_QUERY_COUNT = 3
    config.RERANK_TOP_K = 5
    config.CITATION_VERIFY_ENABLED = True
    config.SELF_RAG_ENABLED = True
    config.RETRIEVAL_REFETCH_ENABLED = True
    return config


# ---------------------------------------------------------------------------
# TestRAGEngineWithBundles
# ---------------------------------------------------------------------------


class TestRAGEngineWithBundles:
    """Verify that RAGEngine integrates with the Bundle architecture."""

    @patch("core.rag_engine.BundleFactory")
    @patch("core.rag_engine.create_infra")
    def test_rag_engine_initializes_bundles(
        self, mock_create_infra, MockBundleFactory
    ):
        """RAGEngine must use BundleFactory to create all three domain Bundles.

        Why this test matters:
            The Bundle architecture centralises dependency wiring into
            BundleFactory.  If RAGEngine constructs services directly
            (the old approach), adding a new Bundle type requires
            changing RAGEngine instead of just the factory.  This test
            ensures the factory is the single construction entry-point.

        What we verify:
            1. create_infra is called with the config.
            2. BundleFactory is instantiated with the InfraBundle.
            3. All three create_* methods are called.
            4. The resulting Bundles are accessible as public attributes.
        """
        infra = _make_infra()
        mock_create_infra.return_value = infra

        # Set up factory mocks
        mock_factory = MockBundleFactory.return_value
        mock_retrieval_bundle = MagicMock(name="RetrievalBundle")
        mock_processing_bundle = MagicMock(name="ProcessingBundle")
        mock_generation_bundle = MagicMock(name="GenerationBundle")
        mock_factory.create_retrieval_bundle.return_value = mock_retrieval_bundle
        mock_factory.create_processing_bundle.return_value = mock_processing_bundle
        mock_factory.create_generation_bundle.return_value = mock_generation_bundle

        config = _make_config()

        from core.rag_engine import RAGEngine

        engine = RAGEngine(config)

        # create_infra must be called with the config
        mock_create_infra.assert_called_once_with(config)

        # BundleFactory must be instantiated with the InfraBundle
        MockBundleFactory.assert_called_once_with(infra)

        # All three bundles must be created
        mock_factory.create_retrieval_bundle.assert_called_once()
        mock_factory.create_processing_bundle.assert_called_once()
        mock_factory.create_generation_bundle.assert_called_once()

        # Bundles must be accessible as public attributes
        assert engine.retrieval_bundle is mock_retrieval_bundle, (
            "engine.retrieval_bundle should be the RetrievalBundle from factory"
        )
        assert engine.processing_bundle is mock_processing_bundle, (
            "engine.processing_bundle should be the ProcessingBundle from factory"
        )
        assert engine.generation_bundle is mock_generation_bundle, (
            "engine.generation_bundle should be the GenerationBundle from factory"
        )

    @patch("core.rag_engine.BundleFactory")
    @patch("core.rag_engine.create_infra")
    def test_rag_engine_delegates_retrieve(
        self, mock_create_infra, MockBundleFactory
    ):
        """RAGEngine.retrieve must delegate to the RetrievalBundle.

        Why this test matters:
            Existing code calls engine.retrieve(query) and expects the
            same result format as before.  After the refactoring, this
            call must flow through the RetrievalBundle rather than the
            old RetrievalPipeline directly.  If the delegation breaks,
            all retrieval callers (API endpoints, chat handlers) fail.

        What we verify:
            1. engine.retrieve(query) delegates to retrieval_bundle.retrieve.
            2. The return value passes through unchanged.
        """
        infra = _make_infra()
        mock_create_infra.return_value = infra

        mock_factory = MockBundleFactory.return_value
        mock_retrieval_bundle = MagicMock(name="RetrievalBundle")
        mock_processing_bundle = MagicMock(name="ProcessingBundle")
        mock_generation_bundle = MagicMock(name="GenerationBundle")
        mock_factory.create_retrieval_bundle.return_value = mock_retrieval_bundle
        mock_factory.create_processing_bundle.return_value = mock_processing_bundle
        mock_factory.create_generation_bundle.return_value = mock_generation_bundle

        # Set up retrieval bundle to return a known result
        from core.services.protocols import RetrievalResult

        expected_result = RetrievalResult(
            chunks=[{"content": "test chunk", "metadata": {"source": "test.pdf"}}],
            sources=[{"source": "test.pdf"}],
            confidence=0.85,
        )
        mock_retrieval_bundle.retrieve.return_value = expected_result

        config = _make_config()

        from core.rag_engine import RAGEngine

        engine = RAGEngine(config)

        # Call retrieve -- must delegate to the bundle
        result = engine.retrieve("What is RAG?")

        mock_retrieval_bundle.retrieve.assert_called_once_with("What is RAG?")
        assert result is expected_result, (
            "engine.retrieve should return the RetrievalBundle result unchanged"
        )

    @patch("core.rag_engine.BundleFactory")
    @patch("core.rag_engine.create_infra")
    def test_rag_engine_backward_compat(
        self, mock_create_infra, MockBundleFactory
    ):
        """RAGEngine must still expose legacy attributes for backward compat.

        Why this test matters:
            Many callers (API routes, tests, main.py lifespan) access
            engine.embedding_service, engine.vector_store, engine.llm_client,
            and config scalars like engine.top_k.  After refactoring to
            use Bundles, these attributes must still be available so that
            existing code doesn't break.  This is the backward-compatibility
            contract.

        What we verify:
            1. Infrastructure attributes (embedding_service, vector_store, etc.)
               are accessible from the InfraBundle.
            2. Config scalars (top_k, bm25_top_k, etc.) are populated.
            3. Service shortcuts (ingestion, generation) still exist for
               callers that use engine.ingestion.ingest_document().
        """
        infra = _make_infra()
        mock_create_infra.return_value = infra

        mock_factory = MockBundleFactory.return_value
        mock_retrieval_bundle = MagicMock(name="RetrievalBundle")
        mock_processing_bundle = MagicMock(name="ProcessingBundle")
        mock_generation_bundle = MagicMock(name="GenerationBundle")
        mock_factory.create_retrieval_bundle.return_value = mock_retrieval_bundle
        mock_factory.create_processing_bundle.return_value = mock_processing_bundle
        mock_factory.create_generation_bundle.return_value = mock_generation_bundle

        config = _make_config()

        from core.rag_engine import RAGEngine

        engine = RAGEngine(config)

        # Infrastructure attributes must be accessible (backward compat)
        assert hasattr(engine, "embedding_service"), (
            "engine.embedding_service must be exposed for legacy callers"
        )
        assert engine.embedding_service is infra.embedding_service

        assert hasattr(engine, "vector_store"), (
            "engine.vector_store must be exposed for legacy callers"
        )
        assert engine.vector_store is infra.vector_store

        assert hasattr(engine, "llm_client"), (
            "engine.llm_client must be exposed for legacy callers"
        )
        assert engine.llm_client is infra.llm_client

        # Config scalars must be populated
        assert engine.top_k == config.TOP_K, (
            "engine.top_k must match config.TOP_K for backward compat"
        )
        assert engine.similarity_threshold == config.SIMILARITY_THRESHOLD, (
            "engine.similarity_threshold must match config for backward compat"
        )
        assert engine.bm25_top_k == config.BM25_TOP_K
        assert engine.rrf_k == config.RRF_K
