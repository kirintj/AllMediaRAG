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
    MIMO_API_KEY: str = ""
    MIMO_API_BASE: str = "https://api.siliconflow.cn/v1"
    MIMO_MODEL: str = "mimo-v2.5"

    # -- Embedding ----------------------------------------------------
    EMBEDDING_MODEL_PATH: str = "./models/bge-m3"

    # -- Chroma -------------------------------------------------------
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # -- Data directory -----------------------------------------------
    DATA_DIR: str = "./data/knowledge-base"

    # -- BM25 persistence ---------------------------------------------
    BM25_PERSIST_DIR: str = ""

    # -- PostgreSQL ---------------------------------------------------
    DATABASE_URL: str = ""
    PG_HOST: str = "localhost"
    PG_PORT: int = 5432
    PG_USER: str = "rag_user"
    PG_PASSWORD: str = "rag_password"
    PG_DATABASE: str = "rag_db"
    PG_POOL_SIZE: int = 5
    PG_MAX_OVERFLOW: int = 10

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

    # -- Cache --------------------------------------------------------
    USE_CACHE: bool = True
    CACHE_L1_MAX_SIZE: int = 1000
    CACHE_L1_TTL: int = 300
    USE_REDIS: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
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
    VECTOR_STORE_PROVIDER: str = "chroma"
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

    # -- Alert thresholds ---------------------------------------------
    ALERT_LATENCY_THRESHOLD_MS: int = 1000
    ALERT_ERROR_RATE_THRESHOLD: float = 0.05
    ALERT_QUALITY_THRESHOLD: float = 0.6

    # -- Computed properties ------------------------------------------

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


# ---------------------------------------------------------------------------
# Module-level singletons (backward-compatible import paths)
# ---------------------------------------------------------------------------
config = AppSettings()
advanced_config = config  # alias for code still importing advanced_config


def init_advanced_config() -> None:
    """Backward-compat no-op.

    The former implementation called ``load_dotenv()``; this is now handled
    automatically by ``pydantic_settings`` via ``env_file=".env"``.
    """
