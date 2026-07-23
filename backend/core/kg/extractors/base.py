"""提取器基类"""
from __future__ import annotations
from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """GraphRAG 提取器统一接口"""

    @abstractmethod
    def extract(self, chunks: list[dict]) -> tuple[list[dict], list[dict]]:
        """从 chunks 中提取实体和关系

        Args:
            chunks: [{"text": str, "metadata": dict}, ...]

        Returns:
            (entities, relations) where:
            entities: [{"name": str, "type": str, "description": str, "source_id": str}]
            relations: [{"source": str, "target": str, "description": str, "weight": int, "keywords": list[str]}]
        """
        ...
