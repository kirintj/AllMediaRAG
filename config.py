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
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-small-zh-v1.5")

    # Chroma 配置
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # 数据目录
    DATA_DIR: str = os.getenv("DATA_DIR", "./data/python-docs")

    # RAG 参数
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
    MAX_HISTORY_TURNS: int = 5


config = Config()
