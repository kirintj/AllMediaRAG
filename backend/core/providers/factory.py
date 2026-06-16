import logging
from typing import Optional, Type

from .base import FileReader, VectorStoreProvider, EmbeddingProvider, LLMProvider
from ..chunking.base import ChunkingStrategy

logger = logging.getLogger(__name__)


class ProviderFactory:
    """可插拔模块工厂

    通过注册表管理各种 Provider 的创建。
    支持：
    - 注册自定义 Provider
    - 按名称创建 Provider 实例
    - 自动回退到默认实现
    """

    # 注册表
    _file_readers: dict[str, Type[FileReader]] = {}
    _vector_stores: dict[str, Type[VectorStoreProvider]] = {}
    _embedding_providers: dict[str, Type[EmbeddingProvider]] = {}
    _llm_providers: dict[str, Type[LLMProvider]] = {}
    _chunking_strategies: dict[str, Type[ChunkingStrategy]] = {}

    @classmethod
    def register_file_reader(cls, name: str, reader_class: Type[FileReader]):
        """注册文件读取器

        Args:
            name: 名称标识
            reader_class: 读取器类
        """
        cls._file_readers[name] = reader_class
        logger.debug("Registered file reader: %s", name)

    @classmethod
    def register_vector_store(cls, name: str, store_class: Type[VectorStoreProvider]):
        """注册向量存储

        Args:
            name: 名称标识
            store_class: 存储类
        """
        cls._vector_stores[name] = store_class
        logger.debug("Registered vector store: %s", name)

    @classmethod
    def register_embedding_provider(cls, name: str, provider_class: Type[EmbeddingProvider]):
        """注册 Embedding 提供者

        Args:
            name: 名称标识
            provider_class: 提供者类
        """
        cls._embedding_providers[name] = provider_class
        logger.debug("Registered embedding provider: %s", name)

    @classmethod
    def register_llm_provider(cls, name: str, provider_class: Type[LLMProvider]):
        """注册 LLM 提供者

        Args:
            name: 名称标识
            provider_class: 提供者类
        """
        cls._llm_providers[name] = provider_class
        logger.debug("Registered LLM provider: %s", name)

    @classmethod
    def create_file_reader(cls, name: str, **kwargs) -> FileReader:
        """创建文件读取器实例

        Args:
            name: 注册名称
            **kwargs: 传递给构造函数的参数

        Returns:
            FileReader 实例

        Raises:
            ValueError: 未知的 Provider 名称
        """
        reader_class = cls._file_readers.get(name)
        if not reader_class:
            available = list(cls._file_readers.keys())
            raise ValueError(f"Unknown file reader: {name}. Available: {available}")
        return reader_class(**kwargs)

    @classmethod
    def create_vector_store(cls, name: str, **kwargs) -> VectorStoreProvider:
        """创建向量存储实例

        Args:
            name: 注册名称
            **kwargs: 传递给构造函数的参数

        Returns:
            VectorStoreProvider 实例
        """
        store_class = cls._vector_stores.get(name)
        if not store_class:
            available = list(cls._vector_stores.keys())
            raise ValueError(f"Unknown vector store: {name}. Available: {available}")
        return store_class(**kwargs)

    @classmethod
    def create_embedding_provider(cls, name: str, **kwargs) -> EmbeddingProvider:
        """创建 Embedding 提供者实例

        Args:
            name: 注册名称
            **kwargs: 传递给构造函数的参数

        Returns:
            EmbeddingProvider 实例
        """
        provider_class = cls._embedding_providers.get(name)
        if not provider_class:
            available = list(cls._embedding_providers.keys())
            raise ValueError(f"Unknown embedding provider: {name}. Available: {available}")
        return provider_class(**kwargs)

    @classmethod
    def create_llm_provider(cls, name: str, **kwargs) -> LLMProvider:
        """创建 LLM 提供者实例

        Args:
            name: 注册名称
            **kwargs: 传递给构造函数的参数

        Returns:
            LLMProvider 实例
        """
        provider_class = cls._llm_providers.get(name)
        if not provider_class:
            available = list(cls._llm_providers.keys())
            raise ValueError(f"Unknown LLM provider: {name}. Available: {available}")
        return provider_class(**kwargs)

    @classmethod
    def register_chunking_strategy(cls, name: str, strategy_class: Type[ChunkingStrategy]):
        """注册切分策略

        Args:
            name: 名称标识
            strategy_class: 切分策略类
        """
        cls._chunking_strategies[name] = strategy_class
        logger.debug("Registered chunking strategy: %s", name)

    @classmethod
    def create_chunking_strategy(cls, name: str, **kwargs) -> ChunkingStrategy:
        """创建切分策略实例

        Args:
            name: 注册名称
            **kwargs: 传递给构造函数的参数

        Returns:
            ChunkingStrategy 实例

        Raises:
            ValueError: 未知的策略名称
        """
        strategy_class = cls._chunking_strategies.get(name)
        if not strategy_class:
            available = list(cls._chunking_strategies.keys())
            raise ValueError(
                f"Unknown chunking strategy: {name}. Available: {available}"
            )
        return strategy_class(**kwargs)

    @classmethod
    def get_available_providers(cls) -> dict:
        """获取所有可用的 Provider 列表

        Returns:
            {
                "file_readers": [str],
                "vector_stores": [str],
                "embedding_providers": [str],
                "llm_providers": [str]
            }
        """
        return {
            "file_readers": list(cls._file_readers.keys()),
            "vector_stores": list(cls._vector_stores.keys()),
            "embedding_providers": list(cls._embedding_providers.keys()),
            "llm_providers": list(cls._llm_providers.keys()),
            "chunking_strategies": list(cls._chunking_strategies.keys()),
        }
