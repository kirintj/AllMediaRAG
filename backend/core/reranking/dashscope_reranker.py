"""DashScope Reranker

通过阿里云 DashScope API 提供重排序服务，
调用 /api/v1/services/rerank/text-reranking/text-reranking 端点。

支持模型：
- gte-rerank
- qwen3-rerank
"""

from __future__ import annotations

import logging

import requests

from .base import RerankerProvider

logger = logging.getLogger(__name__)

DASHSCOPE_RERANK_URL = (
    "https://dashscope.aliyuncs.com/api/v1/services/rerank"
    "/text-reranking/text-reranking"
)


class DashScopeReranker(RerankerProvider):
    """阿里云 DashScope 云端重排序器

    特性：
    - 调用 DashScope text-reranking API
    - 无需本地模型，零依赖（仅需 requests）
    - API 调用失败时 graceful 降级，返回原始排序
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gte-rerank",
    ):
        self._api_key = api_key
        self._model = model
        self._initialization_failed = False
        self._config = None

    def _get_config(self):
        if self._config is None:
            from core.config import config  # noqa: WPS433
            self._config = config
        return self._config

    def _refresh_from_config(self):
        cfg = self._get_config()
        expected_key = getattr(cfg, "DASHSCOPE_API_KEY", "") or self._api_key
        expected_model = getattr(cfg, "DASHSCOPE_RERANKER_MODEL", self._model) or self._model
        if expected_key:
            self._api_key = expected_key
        if expected_model:
            self._model = expected_model

    def is_available(self) -> bool:
        self._refresh_from_config()
        return bool(self._api_key) and not self._initialization_failed

    def rerank(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> list[dict]:
        self._refresh_from_config()
        if not self._api_key:
            logger.warning("DashScope reranker: no API key, returning original order")
            return documents[:top_k]

        validated_docs = self._validate_documents(documents)
        if not validated_docs:
            return []

        texts = [doc["text"] for doc in validated_docs]

        try:
            response = requests.post(
                DASHSCOPE_RERANK_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "input": {
                        "query": query,
                        "documents": texts,
                    },
                    "parameters": {
                        "top_n": min(top_k, len(texts)),
                        "return_documents": False,
                    },
                },
                timeout=30,
            )
            response.raise_for_status()
            result_data = response.json()

            results = result_data.get("output", {}).get("results", [])
            reranked = []
            for item in results:
                idx = item["index"]
                original_doc = validated_docs[idx].copy()
                original_doc["rerank_score"] = item["relevance_score"]
                reranked.append(original_doc)

            logger.debug(
                "DashScope rerank completed: %d documents -> %d results",
                len(texts), len(reranked),
            )
            return reranked

        except Exception as e:
            logger.warning("DashScope rerank failed: %s, returning original order", e)
            return documents[:top_k]
