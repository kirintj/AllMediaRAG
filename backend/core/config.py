import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """配置管理类，从环境变量加载配置"""

    # MiMo API 配置
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", "")
    MIMO_API_BASE: str = os.getenv("MIMO_API_BASE", "https://api.siliconflow.cn/v1")
    MIMO_MODEL: str = os.getenv("MIMO_MODEL", "mimo-v2.5")

    # Embedding 模型配置
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-m3")

    # Chroma 配置
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # 数据目录
    DATA_DIR: str = os.getenv("DATA_DIR", "./data/knowledge-base")

    # BM25 持久化目录（解耦自 CHROMA_PERSIST_DIR，留空时回退到 CHROMA_PERSIST_DIR）
    BM25_PERSIST_DIR: str = os.getenv("BM25_PERSIST_DIR", "")

    # PostgreSQL 配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_USER: str = os.getenv("PG_USER", "rag_user")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD", "rag_password")
    PG_DATABASE: str = os.getenv("PG_DATABASE", "rag_db")
    PG_POOL_SIZE: int = int(os.getenv("PG_POOL_SIZE", "5"))
    PG_MAX_OVERFLOW: int = int(os.getenv("PG_MAX_OVERFLOW", "10"))

    # RAG 参数
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.5
    MAX_HISTORY_TURNS: int = 5

    # BM25 + RRF 参数
    BM25_TOP_K: int = 6        # 每路召回数量
    RRF_K: int = 60            # RRF 公式常数
    RRF_WEIGHT_VECTOR: float = 0.7  # 向量检索权重
    RRF_WEIGHT_BM25: float = 0.3    # BM25 检索权重

    # 语义切分参数
    SEMANTIC_CHUNK_PERCENTILE: int = 25    # 相似度阈值百分位
    SEMANTIC_CHUNK_MIN_SENTENCES: int = 2  # 每个 chunk 最少句子数
    SEMANTIC_CHUNK_MAX_SENTENCES: int = 20 # 每个 chunk 最多句子数
    CHUNKING_STRATEGY: str = os.getenv("CHUNKING_STRATEGY", "semantic")

    # 查询扩展配置
    USE_HYDE: bool = os.getenv("USE_HYDE", "true").lower() in ("true", "1", "yes")
    MULTI_QUERY_ENABLED: bool = os.getenv("MULTI_QUERY_ENABLED", "true").lower() in ("true", "1", "yes")
    MULTI_QUERY_COUNT: int = int(os.getenv("MULTI_QUERY_COUNT", "3"))

    # 重排序配置
    RERANK_STRATEGY: str = os.getenv("RERANK_STRATEGY", "cohere")  # "cohere", "bge", "hybrid"
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    BGE_RERANKER_PATH: str = os.getenv("BGE_RERANKER_PATH", "BAAI/bge-reranker-base")
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "40"))
    RERANK_GATE_THRESHOLD: float = float(os.getenv("RERANK_GATE_THRESHOLD", "0.3"))

    # 缓存配置
    USE_CACHE: bool = os.getenv("USE_CACHE", "true").lower() in ("true", "1", "yes")
    CACHE_L1_MAX_SIZE: int = int(os.getenv("CACHE_L1_MAX_SIZE", "1000"))
    CACHE_L1_TTL: int = int(os.getenv("CACHE_L1_TTL", "300"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() in ("true", "1", "yes")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    CACHE_L2_TTL: int = int(os.getenv("CACHE_L2_TTL", "600"))

    # OCR 配置
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "paddle")  # "paddle" | "tesseract" | "none"
    OCR_LANG: str = os.getenv("OCR_LANG", "ch")
    OCR_USE_GPU: bool = os.getenv("OCR_USE_GPU", "false").lower() in ("true", "1", "yes")

    # VLM 配置
    USE_VLM: bool = os.getenv("USE_VLM", "false").lower() in ("true", "1", "yes")
    VLM_MODEL: str = os.getenv("VLM_MODEL", "")
    VLM_API_BASE: str = os.getenv("VLM_API_BASE", "")

    # 引用核查配置
    CITATION_VERIFY_ENABLED: bool = os.getenv("CITATION_VERIFY_ENABLED", "true").lower() in ("true", "1", "yes")
    CITATION_CONFIDENCE_THRESHOLD: float = float(os.getenv("CITATION_CONFIDENCE_THRESHOLD", "0.5"))

    # 二次检索配置
    RETRIEVAL_REFETCH_ENABLED: bool = os.getenv("RETRIEVAL_REFETCH_ENABLED", "true").lower() in ("true", "1", "yes")
    RETRIEVAL_CONFIDENCE_THRESHOLD: float = float(os.getenv("RETRIEVAL_CONFIDENCE_THRESHOLD", "0.5"))

    # Self-RAG 配置
    SELF_RAG_ENABLED: bool = os.getenv("SELF_RAG_ENABLED", "true").lower() in ("true", "1", "yes")

    # Parent-Child 分块配置
    PC_CHILD_SENTENCES: int = int(os.getenv("PC_CHILD_SENTENCES", "3"))
    PC_PARENT_GROUPS: int = int(os.getenv("PC_PARENT_GROUPS", "4"))
    PC_OVERLAP_SENTENCES: int = int(os.getenv("PC_OVERLAP_SENTENCES", "1"))

    # 工厂模式配置
    USE_FACTORY_MODE: bool = os.getenv("USE_FACTORY_MODE", "false").lower() in ("true", "1", "yes")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "sentence-transformer")
    VECTOR_STORE_PROVIDER: str = os.getenv("VECTOR_STORE_PROVIDER", "chroma")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai-compatible")

    @property
    def database_url(self) -> str:
        """获取 PostgreSQL 连接 URL

        优先使用 DATABASE_URL 环境变量，否则从 PG_* 配置拼接。
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql://{self.PG_USER}:{self.PG_PASSWORD}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DATABASE}"
        )


config = Config()
