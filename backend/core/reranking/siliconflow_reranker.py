"""SiliconFlow Reranker

通过硅基流动（SiliconFlow）云端 API 提供重排序服务，
调用 /v1/rerank 端点（非 OpenAI 格式，使用 requests）。

支持免费模型：
- BAAI/bge-reranker-v2-m3（多语言重排序）
"""

import logging

import requests

from .base import RerankerProvider

logger = logging.getLogger(__name__)


class SiliconFlowReranker(RerankerProvider):
    """SiliconFlow 云端重排序器

    特性：
    - 调用 SiliconFlow /v1/rerank API
    - 无需本地模型，零依赖（仅需 requests）
    - API 调用失败时 graceful 降级，返回原始排序
    """

    def __init__(self, api_key: str,
                 model: str = "BAAI/bge-reranker-v2-m3",
                 api_base: str = "https://api.siliconflow.cn/v1"):
        """
        Args:
            api_key: SiliconFlow API Key（首次启动时用；后续请求会从 config 重新读取以支持热更新）
            model: 模型名称（默认 BAAI/bge-reranker-v2-m3，免费）
            api_base: API 基础地址
        """
        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._initialization_failed = False
        # 延迟加载，避免 import 时的循环依赖
        self._config = None

    def _get_config(self):
        if self._config is None:
            from core.config import config  # noqa: WPS433
            self._config = config
        return self._config

    def _refresh_from_config(self):
        """每次请求前检查：如果 config 里的 key/model 变了，就用新值"""
        cfg = self._get_config()
        expected_key = cfg.SILICONFLOW_API_KEY or self._api_key
        expected_model = getattr(cfg, "SILICONFLOW_RERANKER_MODEL", self._model) or self._model
        # 允许首次请求时用 env / 默认值；之后若保存则会覆盖
        if expected_key:
            self._api_key = expected_key
        if expected_model:
            self._model = expected_model

    def is_available(self) -> bool:
        """检查 Reranker 是否可用（API Key 已配置）"""
        self._refresh_from_config()
        return bool(self._api_key) and not self._initialization_failed

    def rerank(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> list[dict]:
        """使用 SiliconFlow API 进行重排序

        Args:
            query: 用户查询
            documents: 文档列表
            top_k: 返回数量

        Returns:
            重排序后的文档列表（添加 rerank_score 字段）
        """
        self._refresh_from_config()
        if not self._api_key:
            logger.warning("SiliconFlow reranker: no API key, returning original order")
            return documents[:top_k]

        # 验证文档
        validated_docs = self._validate_documents(documents)

        if not validated_docs:
            return []

        # 提取文本用于重排序
        texts = [doc["text"] for doc in validated_docs]

        try:
            # 调用 SiliconFlow rerank API
            response = requests.post(
                f"{self._api_base}/rerank",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model,
                    "query": query,
                    "documents": texts,
                    "top_n": min(top_k, len(texts)),
                },
                timeout=30,
            )
            response.raise_for_status()
            result_data = response.json()

            # 构建结果：按 API 返回的 index 映射回原文档
            reranked = []
            for item in result_data.get("results", []):
                idx = item["index"]
                original_doc = validated_docs[idx].copy()
                original_doc["rerank_score"] = item["relevance_score"]
                reranked.append(original_doc)

            logger.debug(
                "SiliconFlow rerank completed: %d documents -> %d results",
                len(texts), len(reranked),
            )
            return reranked

        except Exception as e:
            logger.warning("SiliconFlow rerank failed: %s, returning original order", e)
            # API 调用失败，回退到原始排序
            return documents[:top_k]
