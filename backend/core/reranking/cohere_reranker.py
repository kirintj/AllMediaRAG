import logging
from typing import Optional

import cohere

from .base import RerankerProvider

logger = logging.getLogger(__name__)


class CohereReranker(RerankerProvider):
    """Cohere Reranker API 集成"""

    def __init__(self, api_key: str, model: str = "rerank-multilingual-v3.0"):
        """
        Args:
            api_key: Cohere API key
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self._client: Optional[cohere.Client] = None

    @property
    def client(self) -> Optional[cohere.Client]:
        """延迟初始化客户端"""
        if self._client is None and self.api_key:
            try:
                self._client = cohere.Client(self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize Cohere client: %s", e)
        return self._client

    def rerank(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> list[dict]:
        """
        使用Cohere API进行重排序

        Args:
            query: 用户查询
            documents: 文档列表
            top_k: 返回数量

        Returns:
            重排序后的文档列表
        """
        if not self.is_available():
            logger.warning(
                "Cohere reranker not available, returning original order"
            )
            return documents[:top_k]

        # 验证文档
        validated_docs = self._validate_documents(documents)

        if not validated_docs:
            return []

        # 提取文本用于重排序
        texts = [doc["text"] for doc in validated_docs]

        try:
            # 调用Cohere API
            results = self.client.rerank(
                query=query,
                documents=texts,
                top_n=min(top_k, len(texts)),
                model=self.model,
            )

            # 构建结果
            reranked = []
            for result in results.results:
                original_doc = validated_docs[result.index].copy()
                original_doc["rerank_score"] = result.relevance_score
                reranked.append(original_doc)

            return reranked

        except Exception as e:
            logger.warning(
                "Cohere rerank failed: %s, returning original order", e
            )
            # API调用失败，回退到原始排序
            return documents[:top_k]

    def is_available(self) -> bool:
        """检查Cohere是否可用"""
        return bool(self.api_key) and self.client is not None
