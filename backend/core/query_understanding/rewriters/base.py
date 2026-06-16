from abc import ABC, abstractmethod


class QueryRewriter(ABC):
    """查询改写器抽象基类"""

    @abstractmethod
    def rewrite_sync(self, query: str, context: dict = None) -> list[str]:
        """同步改写查询，返回改写后的查询列表（不含原始查询）"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """改写器名称标识"""
        pass
