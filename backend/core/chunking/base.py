from abc import ABC, abstractmethod
from typing import TypedDict


class ChunkData(TypedDict):
    """单个切片的数据结构"""
    content: str
    metadata: dict


class ChunkingStrategy(ABC):
    """切分策略抽象基类

    所有切分策略必须实现此接口。
    """

    @abstractmethod
    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        """将文本切分为多个 chunk

        Args:
            text: 待切分的文本
            metadata: 可选的元数据，会合并到每个 chunk 的 metadata 中

        Returns:
            ChunkData 列表
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称标识"""
        ...
