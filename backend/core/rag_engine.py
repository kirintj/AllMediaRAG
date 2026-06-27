"""RAG Engine: thin facade over InfraBundle + domain Bundles.

After refactoring, this class constructs the infrastructure bundle and
uses BundleFactory to create the three domain Bundles
(RetrievalBundle, ProcessingBundle, GenerationBundle).

Why use BundleFactory instead of constructing services directly:
    BundleFactory encapsulates all Bundle wiring in one place.  Adding
    a new Bundle type only requires a new factory method, not changes
    to RAGEngine.  This also satisfies the Dependency Inversion
    Principle -- RAGEngine depends on the factory abstraction rather
    than knowing each Bundle's constructor signature.

Backward-compatible attributes are exposed via the infra bundle so
that legacy code (tests, API routes) can still access
``engine.embedding_service``, ``engine.vector_store``, etc.
"""

import logging
from typing import Generator

from core.services import create_infra
from core.services.bundle_factory import BundleFactory
from core.services.retrieval_pipeline import RetrievalPipeline
from core.services.ingestion_service import IngestionService
from core.services.generation_service import GenerationService

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine -- thin facade that composes InfraBundle + domain Bundles.

    Supports two initialization modes (backward compat):
    1. Direct mode: instantiate concrete implementations (default)
    2. Factory mode: use ProviderFactory for pluggable components

    After the Bundle refactoring (Tasks 3-7), the engine uses
    BundleFactory to create RetrievalBundle, ProcessingBundle, and
    GenerationBundle.  These are exposed as public attributes
    (``engine.retrieval_bundle``, etc.) for callers that want the
    slim Bundle protocol.  Legacy callers that access
    ``engine.retrieval``, ``engine.ingestion``, ``engine.generation``
    continue to work unchanged.
    """

    def __init__(self, config, use_factory: bool = False):
        """Initialize RAG engine.

        Args:
            config: AppSettings configuration object
            use_factory: whether to use factory mode for component creation
        """
        self._config = config
        self._use_factory = use_factory

        # Build shared infrastructure
        self._infra = create_infra(config)

        # Use BundleFactory to create the three domain Bundles.
        # Why BundleFactory: centralises Bundle wiring so that adding
        # a new Bundle type only requires a new factory method.
        self._bundle_factory = BundleFactory(self._infra)
        self.retrieval_bundle = self._bundle_factory.create_retrieval_bundle()
        self.processing_bundle = self._bundle_factory.create_processing_bundle()
        self.generation_bundle = self._bundle_factory.create_generation_bundle()

        # Instantiate the three legacy services (backward compat).
        # These still exist because some callers (IngestionService,
        # build_prompt, query_stream) use the full service API rather
        # than the slim Bundle protocol.
        self.retrieval = RetrievalPipeline(self._infra)
        self.ingestion = IngestionService(self._infra)
        self.generation = GenerationService(self._infra, self.retrieval)

        self._setup_backward_compat(config)

    @classmethod
    def from_services(cls, config, infra, retrieval, ingestion, generation):
        """Construct facade from pre-existing infra bundle and services.

        Avoids duplicate ``create_infra()`` calls when the caller already
        owns the infrastructure (e.g. lifespan startup in main.py).

        Note: When using from_services, domain Bundles are also created
        from the InfraBundle via BundleFactory to maintain the full
        facade contract.
        """
        instance = cls.__new__(cls)
        instance._config = config
        instance._use_factory = False
        instance._infra = infra

        # Create domain Bundles via BundleFactory even when pre-existing
        # services are provided, so that engine.retrieval_bundle etc. are
        # always available for callers using the slim Bundle protocol.
        instance._bundle_factory = BundleFactory(infra)
        instance.retrieval_bundle = instance._bundle_factory.create_retrieval_bundle()
        instance.processing_bundle = instance._bundle_factory.create_processing_bundle()
        instance.generation_bundle = instance._bundle_factory.create_generation_bundle()

        instance.retrieval = retrieval
        instance.ingestion = ingestion
        instance.generation = generation
        instance._setup_backward_compat(config)
        return instance

    def _setup_backward_compat(self, config):
        """Populate backward-compatible attribute aliases from infra."""
        self.embedding_service = self._infra.embedding_service
        self.vector_store = self._infra.vector_store
        self.llm_client = self._infra.llm_client
        self.document_processor = self._infra.document_processor
        self.bm25_retriever = self._infra.bm25_retriever
        self.rerank_manager = self._infra.rerank_manager
        self.cache_manager = self._infra.cache_manager
        self.index_manager = self._infra.index_manager
        self.classifier = self._infra.classifier
        self.router = self._infra.router
        self.rewriters = self._infra.rewriters
        self.confidence_evaluator = self._infra.confidence_evaluator
        self.citation_verifier = self._infra.citation_verifier
        self.self_rag_reflector = self._infra.self_rag_reflector
        self._executor = self._infra.executor

        # Expose commonly used config scalars (backward compat)
        self._citation_verify_enabled = getattr(config, 'CITATION_VERIFY_ENABLED', True)
        self._self_rag_enabled = getattr(config, 'SELF_RAG_ENABLED', True)
        self._refetch_enabled = getattr(config, 'RETRIEVAL_REFETCH_ENABLED', True)
        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.rrf_weight_vector = config.RRF_WEIGHT_VECTOR
        self.rrf_weight_bm25 = config.RRF_WEIGHT_BM25
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
        self.use_hyde = config.USE_HYDE
        self.multi_query_enabled = config.MULTI_QUERY_ENABLED
        self.multi_query_count = config.MULTI_QUERY_COUNT
        self.rerank_top_k = config.RERANK_TOP_K
        self.rerank_gate_threshold = getattr(config, 'RERANK_GATE_THRESHOLD', 0.3)

        logger.info("RAGEngine facade initialized (infra + 3 services)")

    # ------------------------------------------------------------------
    # _init_* helpers kept as static / class methods for backward compat
    # (tests or other code may call them directly)
    # ------------------------------------------------------------------

    @staticmethod
    def _init_ocr_provider(config):
        """Initialize OCR provider (delegates to services.__init__._init_ocr_provider)."""
        from core.services import _init_ocr_provider
        return _init_ocr_provider(config)

    @staticmethod
    def _init_vlm_provider(config):
        """Initialize VLM provider (delegates to services.__init__._init_vlm_provider)."""
        from core.services import _init_vlm_provider
        return _init_vlm_provider(config)

    @staticmethod
    def _init_chunking_strategy(config):
        """Initialize chunking strategy (delegates to services.__init__._init_chunking_strategy)."""
        from core.services import _init_chunking_strategy
        return _init_chunking_strategy(config)

    @classmethod
    def _build_file_reader_registry(cls, ocr_provider, vlm_provider) -> dict:
        """Build file reader registry (delegates to services.__init__)."""
        from core.services import _build_file_reader_registry
        return _build_file_reader_registry(ocr_provider, vlm_provider)

    # ------------------------------------------------------------------
    # BM25 readiness helpers (backward compat)
    # ------------------------------------------------------------------

    def _wait_bm25_ready(self, timeout: float = 30.0):
        """Wait for BM25 index to be ready (sync)."""
        self.retrieval._wait_bm25_ready(timeout)

    async def _wait_bm25_ready_async(self, timeout: float = 30.0):
        """Wait for BM25 index to be ready (async)."""
        await self.retrieval._wait_bm25_ready_async(timeout)

    # ------------------------------------------------------------------
    # Static/class helpers (backward compat)
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize query for cache key dedup."""
        return RetrievalPipeline._normalize_query(query)

    # Non-document query pattern (backward compat class attribute)
    _GREETING_RE = RetrievalPipeline._GREETING_RE

    @classmethod
    def _is_non_document_query(cls, query: str) -> bool:
        """Check if query is non-document (greeting / short noise)."""
        return RetrievalPipeline._is_non_document_query(query)

    # ------------------------------------------------------------------
    # Business methods -- all delegate to services
    # ------------------------------------------------------------------

    # -- Retrieval -------------------------------------------------------

    def retrieve(self, query: str, top_k: int = None) -> dict:
        """Retrieve relevant documents (full pipeline).

        Why delegate to RetrievalBundle instead of RetrievalPipeline directly:
            RetrievalBundle implements the slim RetrievalBundleProtocol and
            adds bundle-level caching and error wrapping.  Using the bundle
            ensures callers benefit from these improvements while the
            RetrievalPipeline reference (self.retrieval) remains available
            for legacy callers that bypass the bundle.

        Args:
            query: user query
            top_k: unused, kept for interface compat

        Returns:
            Retrieval results (RetrievalResult dataclass)
        """
        return self.retrieval_bundle.retrieve(query)

    def full_retrieve(self, query: str) -> dict:
        """Full retrieval pipeline (sync)."""
        return self.retrieval.full_retrieve(query)

    async def full_retrieve_async(self, query: str) -> dict:
        """Full retrieval pipeline (async)."""
        return await self.retrieval.full_retrieve_async(query)

    # -- Ingestion -------------------------------------------------------

    def ingest_document(self, file_path: str) -> int:
        """Ingest document, return chunk count."""
        return self.ingestion.ingest_document(file_path)

    def delete_by_source(self, source: str):
        """Delete documents by source."""
        self.ingestion.delete_by_source(source)

    def delete_all(self):
        """Delete all documents."""
        self.ingestion.delete_all()

    def sync_index(self, data_dir: str) -> dict:
        """Incremental index sync."""
        return self.ingestion.sync_index(data_dir)

    def get_index_stats(self) -> dict:
        """Get index statistics."""
        return self.ingestion.get_index_stats()

    # -- Generation ------------------------------------------------------

    def build_prompt(self, query: str, contexts: list[dict], history: list[dict] = None) -> str:
        """Build structured prompt."""
        return self.generation.build_prompt(query, contexts, history=history)

    def query_stream(self, question: str, history: list[dict] = None) -> Generator[dict, None, None]:
        """Streaming query with verification."""
        yield from self.generation.query_stream(question, history=history)

    # -- Utility (backward compat, delegates to RetrievalPipeline) -------

    def filter_by_similarity(self, results: dict, threshold: float) -> dict:
        """Filter results by similarity threshold."""
        return RetrievalPipeline.filter_by_similarity(results, threshold)

    def reciprocal_rank_fusion(self, results_list, weights, k):
        """Weighted RRF fusion."""
        return RetrievalPipeline.reciprocal_rank_fusion(results_list, weights, k)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Close engine and release all resources."""
        try:
            # Clear model references before shutting down executor
            if hasattr(self, 'embedding_service') and self.embedding_service:
                self.embedding_service._model = None

            if hasattr(self, 'rerank_manager') and self.rerank_manager:
                if hasattr(self.rerank_manager, '_model'):
                    self.rerank_manager._model = None

            # Release PyTorch GPU cache
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            # Close services (retrieval shuts down the shared executor)
            self.retrieval.close()
            self.ingestion.close()
            self.generation.close()

            # Close infra components that have their own resources
            if hasattr(self.vector_store, 'close'):
                self.vector_store.close()
            if hasattr(self.index_manager, 'close'):
                self.index_manager.close()

            logger.info("RAGEngine closed")
        except Exception as e:
            logger.warning("Error closing RAGEngine: %s", e)
