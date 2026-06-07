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

    # 查询扩展配置
    USE_HYDE: bool = os.getenv("USE_HYDE", "true").lower() in ("true", "1", "yes")
    MULTI_QUERY_ENABLED: bool = os.getenv("MULTI_QUERY_ENABLED", "true").lower() in ("true", "1", "yes")
    MULTI_QUERY_COUNT: int = int(os.getenv("MULTI_QUERY_COUNT", "3"))

    # 重排序配置
    RERANK_STRATEGY: str = os.getenv("RERANK_STRATEGY", "cohere")  # "cohere", "bge", "hybrid"
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    BGE_RERANKER_PATH: str = os.getenv("BGE_RERANKER_PATH", "BAAI/bge-reranker-base")
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "20"))

    # 缓存配置
    USE_CACHE: bool = os.getenv("USE_CACHE", "true").lower() in ("true", "1", "yes")
    CACHE_L1_MAX_SIZE: int = int(os.getenv("CACHE_L1_MAX_SIZE", "1000"))
    CACHE_L1_TTL: int = int(os.getenv("CACHE_L1_TTL", "300"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() in ("true", "1", "yes")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))


config = Config()
