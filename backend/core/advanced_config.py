import os
from dotenv import load_dotenv

load_dotenv()


class AdvancedRAGConfig:
    """高级RAG配置"""

    # 查询扩展配置
    USE_HYDE: bool = os.getenv("USE_HYDE", "true").lower() == "true"
    HYDE_ENABLED_INTENTS: list = ["analytical", "exploratory"]
    MULTI_QUERY_ENABLED: bool = os.getenv("MULTI_QUERY_ENABLED", "true").lower() == "true"
    MULTI_QUERY_COUNT: int = int(os.getenv("MULTI_QUERY_COUNT", "3"))

    # 重排序配置
    # Cohere API Key：从 https://cohere.com/ 申请
    RERANK_STRATEGY: str = os.getenv("RERANK_STRATEGY", "cohere")  # "cohere", "bge", "hybrid"
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    # BGE Reranker路径：本地模型路径或HuggingFace模型ID
    BGE_RERANKER_PATH: str = os.getenv("BGE_RERANKER_PATH", "BAAI/bge-reranker-base")
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "20"))
    RERANK_TIMEOUT_MS: int = int(os.getenv("RERANK_TIMEOUT_MS", "250"))

    # 缓存配置
    # 使用场景：单机部署可只用L1缓存；多实例部署或需要持久化时启用Redis
    USE_CACHE: bool = os.getenv("USE_CACHE", "true").lower() == "true"
    CACHE_L1_MAX_SIZE: int = int(os.getenv("CACHE_L1_MAX_SIZE", "1000"))
    CACHE_L1_TTL: int = int(os.getenv("CACHE_L1_TTL", "300"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    SEMANTIC_CACHE_ENABLED: bool = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
    SEMANTIC_CACHE_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))

    # 性能配置
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "32"))
    MAX_WAIT_MS: int = int(os.getenv("MAX_WAIT_MS", "10"))
    PARALLEL_RETRIEVAL: bool = os.getenv("PARALLEL_RETRIEVAL", "true").lower() == "true"

    # 评估配置
    EVAL_DATASET_PATH: str = os.getenv("EVAL_DATASET_PATH", "./data/eval_dataset.json")
    ENABLE_LLM_JUDGE: bool = os.getenv("ENABLE_LLM_JUDGE", "true").lower() == "true"
    LLM_JUDGE_MODEL: str = os.getenv("LLM_JUDGE_MODEL", "mimo-v2.5")

    # 监控配置
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # 告警配置
    ALERT_LATENCY_THRESHOLD_MS: int = int(os.getenv("ALERT_LATENCY_THRESHOLD_MS", "1000"))
    ALERT_ERROR_RATE_THRESHOLD: float = float(os.getenv("ALERT_ERROR_RATE_THRESHOLD", "0.05"))
    ALERT_QUALITY_THRESHOLD: float = float(os.getenv("ALERT_QUALITY_THRESHOLD", "0.6"))


advanced_config = AdvancedRAGConfig()
