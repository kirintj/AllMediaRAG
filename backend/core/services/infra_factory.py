"""基础设施工厂函数。

create_infra 按 AppSettings 构建所有共享依赖并返回 InfraBundle。
组装顺序：
1. 核心三件套（embedding / vector_store / llm）
2. 可选组件（OCR / VLM / 文件读取器 / 分块策略）
3. 检索增强（query understanding / reranking / cache）
4. 验证与可观测性（citation / self-rag / confidence / metrics）
5. 知识图谱（Neo4j / extractor / retriever）
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from core.models.llm_bundle import LLMBundle
from core.document_processor import DocumentProcessor
from core.query_understanding.classifier import QueryClassifier
from core.query_understanding.router import QueryRouter
from core.query_understanding.rewriters import HyDERewriter, MultiQueryRewriter
from core.reranking.manager import RerankManager
from core.performance.cache.manager import CacheManager
from core.index_manager import IndexManager
from core.verification.citation_verifier import CitationVerifier
from core.retrieval.confidence_evaluator import ConfidenceEvaluator
from core.observability.metrics_collector import metrics_collector
from core.kg.graph_store import Neo4jGraphStore

from .infra_bundle import InfraBundle
from .infra_init import (
    _try_init,
    _init_ocr_provider,
    _init_vlm_provider,
    _init_vlm_extractor,
    _init_image_store,
    _init_chunking_strategy,
    _build_file_reader_registry,
)

logger = logging.getLogger(__name__)


def create_infra(settings) -> InfraBundle:
    """从 AppSettings 构建所有共享依赖，返回 InfraBundle。"""

    config = settings

    # ---- 1. 核心三件套 -----------------------------------------------
    _embedding_provider = getattr(config, "EMBEDDING_PROVIDER", "sentence-transformer")
    if _embedding_provider == "siliconflow":
        embedding_service = LLMBundle.from_config(
            model_type="embedding",
            llm_factory="SILICONFLOW",
            llm_name=getattr(config, "SILICONFLOW_EMBEDDING_MODEL", "BAAI/bge-m3"),
            api_key=getattr(config, "SILICONFLOW_API_KEY", ""),
        )
    else:
        embedding_service = LLMBundle.from_config(
            model_type="embedding",
            llm_factory="HuggingFace",
            llm_name=getattr(config, "EMBEDDING_MODEL_PATH", "./models/bge-m3"),
            api_key="",
        )

    # Elasticsearch 唯一后端
    from core.providers.elasticsearch_store import ElasticsearchStore

    vector_store = ElasticsearchStore(
        hosts=getattr(config, "ES_HOSTS", "http://localhost:9200"),
        index_prefix=getattr(config, "ES_INDEX_PREFIX", "allrag"),
        tenant_id=getattr(config, "DEFAULT_TENANT_ID", "default"),
        username=getattr(config, "ES_USERNAME", ""),
        password=getattr(config, "ES_PASSWORD", ""),
        embedding_dim=getattr(config, "EMBEDDING_DIM", 1024),
        number_of_shards=getattr(config, "ES_NUMBER_OF_SHARDS", 1),
        number_of_replicas=getattr(config, "ES_NUMBER_OF_REPLICAS", 0),
    )

    llm_client = LLMBundle.from_config(
        model_type="chat",
        llm_factory="OpenAI",
        llm_name=config.MIMO_MODEL,
        api_key=config.MIMO_API_KEY,
        api_base=config.MIMO_API_BASE,
    )

    # ---- 2. 可选组件（OCR / VLM / 文件读取器 / 分块策略）------------
    ocr_provider = _init_ocr_provider(config)
    vlm_provider = _init_vlm_provider(config)
    file_reader_registry = _build_file_reader_registry(ocr_provider, vlm_provider)
    chunking_strategy = _init_chunking_strategy(config)

    vlm_extractor = _init_vlm_extractor(config)
    image_store = _init_image_store(config)

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

    # ---- 3. 检索增强 ---------------------------------------------------
    classifier = QueryClassifier()
    router = QueryRouter()

    rewriters: dict = {}
    if config.USE_HYDE:
        rewriters["hyde"] = HyDERewriter(llm_client)
    if config.MULTI_QUERY_ENABLED:
        rewriters["multi_query"] = MultiQueryRewriter(
            llm_client, num_queries=config.MULTI_QUERY_COUNT
        )

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

    index_manager = IndexManager(state_file="./index_state.json")

    # ---- 4. 验证与可观测性 ---------------------------------------------
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

    # ---- 5. 知识图谱 ---------------------------------------------------
    graph_store = None
    graph_retriever = None
    kg_extractor = None

    if config.USE_KNOWLEDGE_GRAPH:
        graph_store = _try_init(
            "Neo4j graph store",
            lambda: Neo4jGraphStore(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD),
        )
        if graph_store:
            from core.kg.extractor import KGExtractor
            from core.kg.graph_retriever import GraphRetriever
            kg_extractor = KGExtractor(llm_client)
            graph_retriever = GraphRetriever(graph_store)
            graph_retriever.load_aliases()

    # ---- 组装 ----------------------------------------------------------
    infra = InfraBundle(
        settings=config,
        embedding_service=embedding_service,
        vector_store=vector_store,
        llm_client=llm_client,
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
        executor=ThreadPoolExecutor(max_workers=3),
        image_store=image_store,
        graph_store=graph_store,
        graph_retriever=graph_retriever,
        kg_extractor=kg_extractor,
    )

    return infra
