import math
import os
from dotenv import load_dotenv

# 在类定义前加载.env，确保类属性能读取到环境变量
load_dotenv()


def _int_env(key: str, default: int) -> int:
    """从环境变量读取整数值，解析失败时返回默认值。"""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _float_env(key: str, default: float) -> float:
    """从环境变量读取浮点值，解析失败时返回默认值。同时拒绝 nan/inf。"""
    val = os.getenv(key)
    if val is None:
        return default
    try:
        result = float(val)
    except ValueError:
        return default
    if not math.isfinite(result):
        return default
    return result


def _bool_env(key: str, default: bool) -> bool:
    """从环境变量读取布尔值，仅 'true'/'1'/'yes' 视为 True。"""
    val = os.getenv(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


def init_advanced_config() -> None:
    """显式初始化：加载 .env 文件。应在应用启动入口调用。"""
    load_dotenv()


class AdvancedRAGConfig:
    """高级RAG配置"""

    # 查询扩展配置
    USE_HYDE: bool = _bool_env("USE_HYDE", True)
    HYDE_ENABLED_INTENTS: tuple[str, ...] = ("analytical", "exploratory")
    MULTI_QUERY_ENABLED: bool = _bool_env("MULTI_QUERY_ENABLED", True)
    MULTI_QUERY_COUNT: int = _int_env("MULTI_QUERY_COUNT", 3)

    # 重排序配置
    # Cohere API Key：从 https://cohere.com/ 申请
    RERANK_STRATEGY: str = os.getenv("RERANK_STRATEGY", "cohere")  # "cohere", "bge", "hybrid"
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    # BGE Reranker路径：本地模型路径或HuggingFace模型ID
    BGE_RERANKER_PATH: str = os.getenv("BGE_RERANKER_PATH", "BAAI/bge-reranker-base")
    RERANK_TOP_K: int = _int_env("RERANK_TOP_K", 20)
    RERANK_TIMEOUT_MS: int = _int_env("RERANK_TIMEOUT_MS", 250)

    # 缓存配置
    # 使用场景：单机部署可只用L1缓存；多实例部署或需要持久化时启用Redis
    USE_CACHE: bool = _bool_env("USE_CACHE", True)
    CACHE_L1_MAX_SIZE: int = _int_env("CACHE_L1_MAX_SIZE", 1000)
    CACHE_L1_TTL: int = _int_env("CACHE_L1_TTL", 300)
    USE_REDIS: bool = _bool_env("USE_REDIS", False)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = _int_env("REDIS_PORT", 6379)
    SEMANTIC_CACHE_ENABLED: bool = _bool_env("SEMANTIC_CACHE_ENABLED", True)
    SEMANTIC_CACHE_THRESHOLD: float = _float_env("SEMANTIC_CACHE_THRESHOLD", 0.95)

    # 性能配置
    BATCH_SIZE: int = _int_env("BATCH_SIZE", 32)
    MAX_WAIT_MS: int = _int_env("MAX_WAIT_MS", 10)
    PARALLEL_RETRIEVAL: bool = _bool_env("PARALLEL_RETRIEVAL", True)

    # 评估配置
    EVAL_DATASET_PATH: str = os.getenv("EVAL_DATASET_PATH", "./data/eval_dataset.json")
    ENABLE_LLM_JUDGE: bool = _bool_env("ENABLE_LLM_JUDGE", True)
    LLM_JUDGE_MODEL: str = os.getenv("LLM_JUDGE_MODEL", "mimo-v2.5")

    # 监控配置
    ENABLE_METRICS: bool = _bool_env("ENABLE_METRICS", True)
    METRICS_PORT: int = _int_env("METRICS_PORT", 9090)
    ENABLE_TRACING: bool = _bool_env("ENABLE_TRACING", True)
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # 告警配置
    ALERT_LATENCY_THRESHOLD_MS: int = _int_env("ALERT_LATENCY_THRESHOLD_MS", 1000)
    ALERT_ERROR_RATE_THRESHOLD: float = _float_env("ALERT_ERROR_RATE_THRESHOLD", 0.05)
    ALERT_QUALITY_THRESHOLD: float = _float_env("ALERT_QUALITY_THRESHOLD", 0.6)


advanced_config = AdvancedRAGConfig()
