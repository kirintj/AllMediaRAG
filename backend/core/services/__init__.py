"""Shared infrastructure bundle and factory for RAG services."""

from __future__ import annotations

import os
import logging
import threading
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from core.embedding_service import EmbeddingService
from core.vector_store import VectorStore
from core.llm_client import LLMClient
from core.document_processor import DocumentProcessor
from core.bm25_retriever import BM25Retriever
from core.query_understanding.classifier import QueryClassifier
from core.query_understanding.router import QueryRouter
from core.query_understanding.rewriters import HyDERewriter, MultiQueryRewriter
from core.reranking.manager import RerankManager
from core.performance.cache.manager import CacheManager
from core.index_manager import IndexManager
from core.verification.citation_verifier import CitationVerifier
from core.retrieval.confidence_evaluator import ConfidenceEvaluator
from core.observability.metrics_collector import metrics_collector
from core.ocr.paddle_provider import PaddleOCRProvider
from core.ocr.tesseract_provider import TesseractOCRProvider
from core.ocr.vlm_provider import VLMProvider

logger = logging.getLogger(__name__)


@dataclass
class InfraBundle:
    """Holds all shared dependencies required by RAG services."""

    settings: Any  # AppSettings
    embedding_service: Any
    vector_store: Any
    llm_client: Any
    bm25_retriever: Any
    document_processor: Any
    rerank_manager: Any
    cache_manager: Any
    index_manager: Any
    classifier: Any
    router: Any
    rewriters: dict = field(default_factory=dict)
    confidence_evaluator: Any = None
    citation_verifier: Any = None
    self_rag_reflector: Any = None
    metrics_collector: Any = None
    executor: Any = None  # ThreadPoolExecutor
    image_store: Any = None
    bm25_ready: bool = False


# ---------------------------------------------------------------------------
# Private helpers (replicate RAGEngine._init_ocr_provider / _init_vlm_provider
# / _init_chunking_strategy / _build_file_reader_registry)
# ---------------------------------------------------------------------------


def _init_ocr_provider(config):
    """Initialise OCR provider (mirrors RAGEngine._init_ocr_provider)."""
    ocr_type = config.OCR_PROVIDER.lower()
    if ocr_type == "none":
        logger.info("OCR disabled by config")
        return None
    if ocr_type == "paddle":
        try:
            provider = PaddleOCRProvider(
                lang=config.OCR_LANG,
                use_gpu=config.OCR_USE_GPU,
            )
            logger.info("PaddleOCR provider initialized")
            return provider
        except Exception as e:
            logger.warning("Failed to init PaddleOCR: %s", e)
            return None
    elif ocr_type == "tesseract":
        try:
            provider = TesseractOCRProvider(lang="chi_sim+eng")
            logger.info("TesseractOCR provider initialized")
            return provider
        except Exception as e:
            logger.warning("Failed to init TesseractOCR: %s", e)
            return None
    logger.warning("Unknown OCR_PROVIDER: %s", ocr_type)
    return None


def _init_vlm_provider(config):
    """Initialise VLM provider (mirrors RAGEngine._init_vlm_provider)."""
    if not config.USE_VLM:
        logger.info("VLM disabled by config")
        return None
    if not config.VLM_MODEL or not config.VLM_API_BASE:
        logger.warning("VLM_MODEL or VLM_API_BASE not configured")
        return None
    try:
        provider = VLMProvider(
            api_key=config.MIMO_API_KEY,
            api_base=config.VLM_API_BASE,
            model=config.VLM_MODEL,
        )
        logger.info("VLM provider initialized (model=%s)", config.VLM_MODEL)
        return provider
    except Exception as e:
        logger.warning("Failed to init VLM: %s", e)
        return None


def _init_vlm_extractor(config):
    """初始化 VLMExtractor（新版统一提取器）

    为什么与 _init_vlm_provider 分开：
    两者使用不同的 API（DashScope vs SiliconFlow/MIMO），
    配置项也不同，分开初始化避免混淆。
    """
    if not config.USE_VLM_EXTRACTOR:
        logger.info("VLM Extractor disabled by config")
        return None
    if not config.VLM_EXTRACTOR_API_KEY:
        logger.warning("VLM_EXTRACTOR_API_KEY not configured, VLM Extractor disabled")
        return None
    try:
        from core.ocr.vlm_extractor import VLMExtractor
        extractor = VLMExtractor(
            api_key=config.VLM_EXTRACTOR_API_KEY,
            api_base=config.VLM_EXTRACTOR_API_BASE,
            model=config.VLM_EXTRACTOR_MODEL,
            max_tokens=config.VLM_EXTRACTOR_MAX_TOKENS,
            timeout=config.VLM_EXTRACTOR_TIMEOUT,
            max_image_size=config.VLM_EXTRACTOR_MAX_IMAGE_SIZE,
        )
        logger.info("VLM Extractor initialized (model=%s)", config.VLM_EXTRACTOR_MODEL)
        return extractor
    except Exception as e:
        logger.warning("Failed to init VLM Extractor: %s", e)
        return None


def _init_image_store(config):
    """初始化 ImageStore

    为什么与 VLMExtractor 分开初始化：
    ImageStore 的生命周期独立于 VLMExtractor，
    即使 VLMExtractor 未启用，旧管线未来也可能需要图片存储。
    """
    if not config.IMAGE_STORE_ENABLED:
        logger.info("ImageStore disabled by config")
        return None
    try:
        from core.image_store import ImageStore
        store = ImageStore(base_dir=config.IMAGE_STORE_DIR)
        logger.info("ImageStore initialized (dir=%s)", config.IMAGE_STORE_DIR)
        return store
    except Exception as e:
        logger.warning("Failed to init ImageStore: %s", e)
        return None


def _init_chunking_strategy(config):
    """Initialise chunking strategy (mirrors RAGEngine._init_chunking_strategy)."""
    from core.chunking import (
        SemanticChunking,
        FixedSizeChunking,
        RecursiveChunking,
        ParentChildChunking,
    )

    strategy_name = getattr(config, "CHUNKING_STRATEGY", "semantic")

    if strategy_name == "fixed_size":
        strategy = FixedSizeChunking(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
    elif strategy_name == "recursive":
        strategy = RecursiveChunking(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
    elif strategy_name == "parent_child":
        strategy = ParentChildChunking(
            child_sentences=getattr(config, "PC_CHILD_SENTENCES", 3),
            parent_groups=getattr(config, "PC_PARENT_GROUPS", 4),
            overlap_sentences=getattr(config, "PC_OVERLAP_SENTENCES", 1),
        )
    else:
        strategy = SemanticChunking(
            percentile=config.SEMANTIC_CHUNK_PERCENTILE,
            min_sentences=config.SEMANTIC_CHUNK_MIN_SENTENCES,
            max_sentences=config.SEMANTIC_CHUNK_MAX_SENTENCES,
        )

    logger.info("Chunking strategy initialized: %s", strategy.name)
    return strategy


def _build_file_reader_registry(ocr_provider, vlm_provider) -> dict:
    """Build file reader registry (mirrors RAGEngine._build_file_reader_registry)."""
    from core.providers.readers import (
        EnhancedPDFReader,
        MarkdownReader,
        DocxReader,
        HtmlReader,
        ImageReader,
    )

    readers = [
        EnhancedPDFReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
        MarkdownReader(),
        DocxReader(),
        HtmlReader(),
        ImageReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
    ]
    registry: dict = {}
    for reader in readers:
        for ext in reader.supported_extensions():
            registry[ext] = reader
    logger.info("File reader registry built: %s", list(registry.keys()))
    return registry


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_infra(settings) -> InfraBundle:
    """Construct an InfraBundle from application settings.

    Replicates the component-construction logic that previously lived in
    RAGEngine.__init__ and RAGEngine._init_shared_components.
    """
    config = settings

    # ---- core triple (direct mode) ------------------------------------
    embedding_provider = getattr(config, "EMBEDDING_PROVIDER", "sentence-transformer")
    if embedding_provider == "siliconflow":
        from core.providers.siliconflow_adapter import SiliconFlowEmbeddingAdapter

        embedding_service = SiliconFlowEmbeddingAdapter(
            api_key=getattr(config, "SILICONFLOW_API_KEY", ""),
            model=getattr(config, "SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3"),
        )
        logger.info(
            "Using SiliconFlow cloud embedding: %s",
            getattr(config, "SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3"),
        )
    else:
        embedding_service = EmbeddingService(config.EMBEDDING_MODEL_PATH)

    if getattr(config, "VECTOR_STORE_PROVIDER", "chroma") == "pgvector":
        from core.providers.pgvector_adapter import PgVectorStoreAdapter

        vector_store = PgVectorStoreAdapter(database_url=config.database_url)
    else:
        vector_store = VectorStore(config.CHROMA_PERSIST_DIR)

    llm_client = LLMClient(
        config.MIMO_API_KEY,
        config.MIMO_API_BASE,
        config.MIMO_MODEL,
    )

    # ---- thread pool --------------------------------------------------
    executor = ThreadPoolExecutor(max_workers=3)

    # ---- OCR / VLM / readers / chunking -------------------------------
    ocr_provider = _init_ocr_provider(config)
    vlm_provider = _init_vlm_provider(config)
    file_reader_registry = _build_file_reader_registry(ocr_provider, vlm_provider)
    chunking_strategy = _init_chunking_strategy(config)

    vlm_extractor = _init_vlm_extractor(config)
    image_store = _init_image_store(config)

    # 为什么配置依赖检查：MULTIMODAL_GENERATION 需要 USE_VLM_EXTRACTOR=True
    # 才能生效，因为旧管线不产出 figure chunk 的 image_path。
    if getattr(config, "MULTIMODAL_GENERATION", False) and not config.USE_VLM_EXTRACTOR:
        logger.warning("MULTIMODAL_GENERATION=True but USE_VLM_EXTRACTOR=False, "
                        "multimodal generation will have no effect")

    document_processor = DocumentProcessor(
        config,
        ocr_provider,
        vlm_provider,
        file_reader_registry=file_reader_registry,
        chunking_strategy=chunking_strategy,
        image_pipeline=vlm_extractor,
        image_store=image_store,
    )
    document_processor.set_embedding_service(embedding_service)

    # ---- BM25 ---------------------------------------------------------
    bm25_base_dir = getattr(config, "BM25_PERSIST_DIR", "") or config.CHROMA_PERSIST_DIR
    bm25_path = os.path.join(bm25_base_dir, "bm25_index.pkl")
    bm25_retriever = BM25Retriever(persist_path=bm25_path)

    bm25_loaded = bm25_retriever.load()
    bm25_lock = threading.Lock()

    # ---- query understanding ------------------------------------------
    classifier = QueryClassifier()
    router = QueryRouter()

    rewriters: dict = {}
    if config.USE_HYDE:
        rewriters["hyde"] = HyDERewriter(llm_client)
    if config.MULTI_QUERY_ENABLED:
        rewriters["multi_query"] = MultiQueryRewriter(
            llm_client, num_queries=config.MULTI_QUERY_COUNT
        )

    # ---- reranking / cache / index ------------------------------------
    rerank_manager = RerankManager(config)

    cache_manager = CacheManager(
        {
            "use_cache": config.USE_CACHE,
            "l1_max_size": config.CACHE_L1_MAX_SIZE,
            "l1_ttl": config.CACHE_L1_TTL,
            "use_redis": config.USE_REDIS,
            "redis_host": config.REDIS_HOST,
            "redis_port": config.REDIS_PORT,
            "l2_ttl": getattr(config, "CACHE_L2_TTL", 600),
        }
    )

    if getattr(config, "VECTOR_STORE_PROVIDER", "chroma") == "pgvector":
        from core.providers.pgvector_index_adapter import PgIndexManager

        index_manager = PgIndexManager(database_url=config.database_url)
    else:
        index_manager = IndexManager(
            state_file=os.path.join(config.CHROMA_PERSIST_DIR, "index_state.json"),
        )

    # ---- verification / reflection / confidence -----------------------
    citation_verifier = CitationVerifier(
        llm_client=llm_client,
        threshold=getattr(config, "CITATION_CONFIDENCE_THRESHOLD", 0.5),
    )

    from core.verification.self_rag_reflector import SelfRAGReflector

    self_rag_reflector = SelfRAGReflector(llm_client=llm_client)

    confidence_evaluator = ConfidenceEvaluator(
        threshold=config.SIMILARITY_THRESHOLD,
        min_docs=2,
    )

    # ---- assemble bundle ----------------------------------------------
    infra = InfraBundle(
        settings=config,
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_client=llm_client,
        bm25_retriever=bm25_retriever,
        document_processor=document_processor,
        rerank_manager=rerank_manager,
        cache_manager=cache_manager,
        index_manager=index_manager,
        classifier=classifier,
        router=router,
        rewriters=rewriters,
        confidence_evaluator=confidence_evaluator,
        citation_verifier=citation_verifier,
        self_rag_reflector=self_rag_reflector,
        metrics_collector=metrics_collector,
        executor=executor,
        image_store=image_store,
        bm25_ready=bm25_loaded,
    )

    # Kick off background BM25 rebuild if the on-disk index was not found.
    if not bm25_loaded:

        def _rebuild():
            try:
                docs = vector_store.get_all_documents()
                if docs:
                    with bm25_lock:
                        bm25_retriever.build_index(docs)
                    logger.info("BM25 index rebuilt: %d documents", len(docs))
                else:
                    logger.info("Vector store is empty, BM25 index not built")
            except Exception as e:
                logger.warning("Failed to rebuild BM25 index: %s", e)
            finally:
                infra.bm25_ready = True

        threading.Thread(target=_rebuild, daemon=True).start()

    return infra
