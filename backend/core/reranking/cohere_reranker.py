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
            api_key: Cohere API key（首次启动时用；后续请求会从 config 重新读取以支持热更新）
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self._client: Optional[cohere.Client] = None
        self._initialization_failed = False
        # 延迟加载，避免 import 时的循环依赖
        self._config = None

    def _get_config(self):
        if self._config is None:
            from core.config import config  # noqa: WPS433
            self._config = config
        return self._config

    def _ensure_current_client(self):
        """每次请求前检查：如果 config 里的 key 变了，就重建 client"""
        cfg = self._get_config()
        expected_key = cfg.COHERE_API_KEY or self.api_key
        if expected_key and (self._client is None or self.api_key != expected_key):
            try:
                self.api_key = expected_key
                self._client = cohere.Client(expected_key)
                self._initialization_failed = False
                logger.info("Cohere client refreshed")
            except Exception as e:
                logger.warning("Failed to initialize Cohere client: %s", e)
                self._initialization_failed = True

    @property
    def client(self) -> Optional[cohere.Client]:
        """延迟 + 热更新感知的客户端"""
        self._ensure_current_client()
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

            logger.debug("Cohere rerank completed: %d documents -> %d results", len(texts), len(reranked))
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
