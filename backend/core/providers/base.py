from abc import ABC, abstractmethod
from typing import Any, Optional, Generator


class FileReader(ABC):
    """文档读取器抽象接口

    所有文件读取器必须实现此接口。
    """

    @abstractmethod
    def read(self, file_path: str) -> str:
        """读取文件内容，返回纯文本

        Args:
            file_path: 文件路径

        Returns:
            文件内容文本
        """
        pass

    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表

        Returns:
            扩展名列表，如 [".txt", ".md", ".pdf"]
        """
        pass

    def can_handle(self, file_path: str) -> bool:
        """判断是否能处理该文件

        Args:
            file_path: 文件路径

        Returns:
            是否支持该文件格式
        """
        import os
        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.supported_extensions()


class VectorStoreProvider(ABC):
    """向量存储抽象接口

    所有向量存储实现必须实现此接口。
    """

    @abstractmethod
    def add_documents(self, texts: list[str], embeddings: list, metadatas: list) -> None:
        """添加文档到向量库

        Args:
            texts: 文档文本列表
            embeddings: embedding 向量列表
            metadatas: 元数据列表
        """
        pass

    @abstractmethod
    def query(self, embedding: list[float], top_k: int) -> dict:
        """查询相似文档

        Args:
            embedding: 查询向量
            top_k: 返回数量

        Returns:
            {"documents": [...], "metadatas": [...], "distances": [...]}
        """
        pass

    @abstractmethod
    def delete_by_source(self, source: str) -> None:
        """按来源删除文档

        Args:
            source: 文档来源标识
        """
        pass

    @abstractmethod
    def get_all_sources(self) -> list[str]:
        """获取所有文档来源

        Returns:
            来源列表
        """
        pass

    @abstractmethod
    def get_document_count(self) -> int:
        """获取文档总数

        Returns:
            文档数量
        """
        pass

    @abstractmethod
    def delete_all(self) -> None:
        """清空所有文档"""
        pass

    @abstractmethod
    def get_all_documents(self) -> list[dict]:
        """获取所有文档

        Returns:
            [{"text": str, "metadata": dict}, ...]
        """
        pass

    @abstractmethod
    def get_source_details(self) -> list[dict]:
        """获取每个来源的 chunk 数量

        Returns:
            [{"source": str, "chunks": int}, ...]
        """
        pass


class EmbeddingProvider(ABC):
    """Embedding 模型抽象接口

    所有 Embedding 实现必须实现此接口。
    """

    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """批量编码文本

        Args:
            texts: 文本列表

        Returns:
            embedding 向量列表
        """
        pass

    @abstractmethod
    def encode_single(self, text: str) -> list[float]:
        """编码单条文本

        Args:
            text: 文本

        Returns:
            embedding 向量
        """
        pass


class LLMProvider(ABC):
    """LLM 抽象接口

    所有 LLM 实现必须实现此接口。
    """

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """生成回答

        Args:
            prompt: 输入提示

        Returns:
            生成的回答文本
        """
        pass

    @abstractmethod
    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        """流式生成回答

        Args:
            prompt: 输入提示

        Yields:
            生成的文本片段
        """
        pass
