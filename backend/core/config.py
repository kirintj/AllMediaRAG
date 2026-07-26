"""Unified application configuration.

Merges the former ``config.py`` (core settings) and ``advanced_config.py``
(advanced RAG / performance / observability settings) into a single
``pydantic_settings.BaseSettings`` class.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Unified application settings -- reads from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- LLM (MiMo) --------------------------------------------------
    MIMO_API_KEY: str = "tp-c425x60lbjmab4i9imp1m414gjw4h67n2pmj30tmujlba0fy"
    MIMO_API_BASE: str = "https://token-plan-cn.xiaomimimo.com/v1"
    MIMO_MODEL: str = "mimo-v2.5"

    # -- Embedding ----------------------------------------------------
    EMBEDDING_MODEL_PATH: str = "./models/bge-m3"

    # -- Data directory -----------------------------------------------
    DATA_DIR: str = "./data/knowledge-base"

    # -- Elasticsearch ------------------------------------------------
    ES_HOSTS: str = "http://localhost:9200"
    ES_USERNAME: str = ""
    ES_PASSWORD: str = ""
    ES_INDEX_PREFIX: str = "allrag"
    ES_NUMBER_OF_SHARDS: int = 1
    ES_NUMBER_OF_REPLICAS: int = 0
    EMBEDDING_DIM: int = 1024
    DEFAULT_TENANT_ID: str = "default"

    # -- PostgreSQL ---------------------------------------------------
    DATABASE_URL: str = ""
    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_USER: str = "rag_user"
    PG_PASSWORD: str = "rag_password"
    PG_DATABASE: str = "rag_db"
    PG_POOL_SIZE: int = 5
    PG_MAX_OVERFLOW: int = 10

    # -- MinIO/S3 文件存储 ------------------------------------------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "allrag-files"
    MINIO_SECURE: bool = False

    # -- RAG parameters -----------------------------------------------
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.5
    MAX_HISTORY_TURNS: int = 5

    # -- BM25 + RRF ---------------------------------------------------
    BM25_TOP_K: int = 6
    RRF_K: int = 60
    RRF_WEIGHT_VECTOR: float = 0.7
    RRF_WEIGHT_BM25: float = 0.3

    # -- Semantic chunking --------------------------------------------
    SEMANTIC_CHUNK_PERCENTILE: int = 25
    SEMANTIC_CHUNK_MIN_SENTENCES: int = 2
    SEMANTIC_CHUNK_MAX_SENTENCES: int = 20
    CHUNKING_STRATEGY: str = "semantic"

    # -- Query expansion ----------------------------------------------
    USE_HYDE: bool = True
    HYDE_ENABLED_INTENTS: tuple[str, ...] = ("analytical", "exploratory")
    MULTI_QUERY_ENABLED: bool = True
    MULTI_QUERY_COUNT: int = 3

    # -- Reranking ----------------------------------------------------
    RERANK_STRATEGY: str = "cohere"
    COHERE_API_KEY: str = ""
    BGE_RERANKER_PATH: str = "BAAI/bge-reranker-base"
    RERANK_TOP_K: int = 15          # primary config default (advanced used 20)
    RERANK_GATE_THRESHOLD: float = 0.5
    RERANK_TIMEOUT_MS: int = 250

    # -- SiliconFlow cloud API ----------------------------------------
    SILICONFLOW_API_KEY: str = ""
    SILICONFLOW_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    SILICONFLOW_RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

    # -- DashScope (阿里云) -------------------------------------------
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_EMBEDDING_MODEL: str = "text-embedding-v3"
    DASHSCOPE_RERANKER_MODEL: str = "gte-rerank"

    # -- Cache --------------------------------------------------------
    USE_CACHE: bool = True
    CACHE_L1_MAX_SIZE: int = 1000
    CACHE_L1_TTL: int = 300
    USE_REDIS: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # -- Task Queue (Redis Stream) ------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    TASK_TTL_HOURS: int = 24

    # -- 文档格式支持 ------------------------------------------------
    SUPPORTED_FILE_EXTENSIONS: str = ".pdf,.docx,.html,.htm,.txt,.md,.png,.jpg,.jpeg,.bmp,.tiff,.tif,.xlsx,.csv,.pptx,.json,.mp3,.wav,.m4a"

    # -- LLM 增强（分块后执行）--------------------------------------
    ENABLE_AUTO_KEYWORDS: bool = False
    ENABLE_AUTO_QUESTIONS: bool = False
    ENABLE_METADATA_EXTRACTION: bool = False
    ENABLE_TOC_EXTRACTION: bool = False
    AUTO_KEYWORDS_TOPN: int = 5
    AUTO_QUESTIONS_TOPN: int = 3

    # -- Content Tagging -----------------------------------------------
    ENABLE_CONTENT_TAGGING: bool = False
    CONTENT_TAG_TOPN: int = 3
    CONTENT_TAG_KB_IDS: str = ""  # comma-separated tag KB ID list

    # -- RAPTOR -------------------------------------------------------
    ENABLE_RAPTOR: bool = False
    RAPTOR_MAX_CLUSTERS: int = 64
    RAPTOR_THRESHOLD: float = 0.1
    RAPTOR_CLUSTERING_METHOD: str = "gmm"
    RAPTOR_SMALL_LAYER_COLLAPSE: int = 8
    RAPTOR_MAX_ERRORS: int = 3
    RAPTOR_MAX_DEPTH: int = 3

    # -- GraphRAG ------------------------------------------------------
    GRAPHRAG_ENABLED: bool = False
    GRAPHRAG_METHOD: str = "general"  # general / light / ner
    GRAPHRAG_ENTITY_TYPES: str = "organization,person,geo,event,category"
    GRAPHRAG_MAX_GLEANINGS: int = 2
    GRAPHRAG_ENABLE_RESOLUTION: bool = True
    GRAPHRAG_ENABLE_COMMUNITY: bool = True
    GRAPHRAG_PAGERANK_ENABLED: bool = True

    # -- LLM 缓存 ----------------------------------------------------
    ENRICHMENT_CACHE_TTL: int = 86400

    # -- Worker -------------------------------------------------------
    WORKER_CONCURRENCY: int = 4
    WORKER_MAX_RETRIES: int = 3
    WORKER_RETRY_DELAYS: str = "5,15,30"  # comma-separated seconds

    CACHE_L2_TTL: int = 600
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.95

    # -- OCR ----------------------------------------------------------
    OCR_PROVIDER: str = "paddle"
    OCR_LANG: str = "ch"
    OCR_USE_GPU: bool = False

    # -- VLM ----------------------------------------------------------
    USE_VLM: bool = False
    VLM_MODEL: str = ""
    VLM_API_BASE: str = ""

    # -- Citation verification ----------------------------------------
    CITATION_VERIFY_ENABLED: bool = True
    CITATION_CONFIDENCE_THRESHOLD: float = 0.5

    # -- Retrieval refetch --------------------------------------------
    RETRIEVAL_REFETCH_ENABLED: bool = True
    RETRIEVAL_CONFIDENCE_THRESHOLD: float = 0.5

    # -- Self-RAG -----------------------------------------------------
    SELF_RAG_ENABLED: bool = True

    # -- Parent-Child chunking ----------------------------------------
    PC_CHILD_SENTENCES: int = 3
    PC_PARENT_GROUPS: int = 4
    PC_OVERLAP_SENTENCES: int = 1

    # -- Factory mode -------------------------------------------------
    USE_FACTORY_MODE: bool = False
    EMBEDDING_PROVIDER: str = "sentence-transformer"
    VECTOR_STORE_PROVIDER: str = "elasticsearch"
    LLM_PROVIDER: str = "openai-compatible"

    # -- Performance --------------------------------------------------
    BATCH_SIZE: int = 32
    MAX_WAIT_MS: int = 10
    PARALLEL_RETRIEVAL: bool = True

    # -- Evaluation ---------------------------------------------------
    EVAL_DATASET_PATH: str = "./data/eval_dataset.json"
    ENABLE_LLM_JUDGE: bool = True
    LLM_JUDGE_MODEL: str = "mimo-v2.5"

    # -- Observability ------------------------------------------------
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_TRACING: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # -- Knowledge Graph ----------------------------------------------
    USE_KNOWLEDGE_GRAPH: bool = False
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4jtest"
    GRAPH_MAX_CHUNKS: int = 20
    KG_EXTRACTOR_MODEL: str = "cheap"

    # -- Alert thresholds ---------------------------------------------
    ALERT_LATENCY_THRESHOLD_MS: int = 1000
    ALERT_ERROR_RATE_THRESHOLD: float = 0.05
    ALERT_QUALITY_THRESHOLD: float = 0.6

    # -- VLM Extractor（新版统一提取器，替代 OCR+VLM 分离管线）--
    # 为什么单独的 API Key：Qwen-VL-Max 使用 DashScope API，
    # 与现有 MIMO_API_KEY（SiliconFlow）是不同的服务商。
    USE_VLM_EXTRACTOR: bool = False
    VLM_EXTRACTOR_MODEL: str = "qwen-vl-max"
    VLM_EXTRACTOR_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    VLM_EXTRACTOR_API_KEY: str = ""
    VLM_EXTRACTOR_MAX_TOKENS: int = 4096
    VLM_EXTRACTOR_TIMEOUT: int = 60
    VLM_EXTRACTOR_MAX_IMAGE_SIZE: int = 1024

    # -- 图片存储 --
    IMAGE_STORE_ENABLED: bool = True
    IMAGE_STORE_DIR: str = "./data/images"

    # -- 查询时多模态 --
    # 为什么限制图片数：单次生成附带太多图片会超过 LLM 的 context 限制，
    # 且增加延迟和成本。3 张通常足够覆盖一次检索命中的图表。
    MULTIMODAL_GENERATION: bool = True
    MULTIMODAL_MAX_IMAGES: int = 3

    # -- Computed properties ------------------------------------------

    @property
    def worker_retry_delays(self) -> list[int]:
        return [int(x.strip()) for x in self.WORKER_RETRY_DELAYS.split(",")]

    @property
    def database_url(self) -> str:
        """Return PostgreSQL connection URL.

        Prefers the explicit ``DATABASE_URL`` env-var; falls back to
        assembling one from the individual ``PG_*`` values.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"
        )

    @property
    def supported_file_extensions(self) -> set[str]:
        return {ext.strip() for ext in self.SUPPORTED_FILE_EXTENSIONS.split(",")}

    @property
    def graphrag_entity_types(self) -> list[str]:
        return [t.strip() for t in self.GRAPHRAG_ENTITY_TYPES.split(",")]


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------
config = AppSettings()
