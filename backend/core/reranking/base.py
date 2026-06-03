from abc import ABC, abstractmethod


class RerankerProvider(ABC):
    """重排序器抽象基类"""

    @abstractmethod
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        对文档进行重排序

        Args:
            query: 用户查询
            documents: [{"text": str, "metadata": dict, "score": float}, ...]
            top_k: 返回数量

        Returns:
            重排序后的文档列表，每个文档添加 "rerank_score" 字段
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        检查重排序器是否可用

        Returns:
            True if available, False otherwise
        """
        pass

    def _validate_documents(self, documents: list[dict]) -> list[dict]:
        """
        验证并规范化文档格式

        Args:
            documents: 原始文档列表

        Returns:
            验证后的文档列表，确保包含必要字段
        """
        validated = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            if "text" not in doc:
                continue

            # 确保必要字段存在
            validated_doc = {
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0.0),
            }
            validated.append(validated_doc)

        return validated
