"""SiliconFlow Embedding 适配器

通过硅基流动（SiliconFlow）云端 API 提供 Embedding 服务，
使用 openai SDK 调用 OpenAI 兼容的 /v1/embeddings 端点。

支持免费模型：
- BAAI/bge-m3（多语言，8192 token）
- BAAI/bge-large-zh-v1.5（中文，512 token）
"""

import logging
from typing import Optional

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class SiliconFlowEmbeddingAdapter(EmbeddingProvider):
    """SiliconFlow 云端 Embedding 适配器

    特性：
    - 延迟初始化客户端（首次 encode 时才创建）
    - 兼容 OpenAI SDK，可无缝替换本地 SentenceTransformer
    - API 调用失败时抛出异常，由上层捕获处理
    """

    def __init__(self, api_key: str, model: str = "BAAI/bge-m3",
                 api_base: str = "https://api.siliconflow.cn/v1"):
        """
        Args:
            api_key: SiliconFlow API Key
            model: 模型名称（默认 BAAI/bge-m3，免费）
            api_base: API 基础地址
        """
        self._api_key = api_key
        self._model = model
        self._api_base = api_base
        self._client = None
        self._initialization_failed = False

    def _ensure_client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None and not self._initialization_failed:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self._api_key,
                    base_url=self._api_base,
                )
                logger.info("SiliconFlow embedding client initialized: %s @ %s",
                            self._model, self._api_base)
            except Exception as e:
                logger.warning("Failed to initialize SiliconFlow embedding client: %s", e)
                self._initialization_failed = True

    def encode(self, texts: list[str], show_progress: bool = False) -> list[list[float]]:
        """批量编码文本为向量

        Args:
            texts: 文本列表
            show_progress: 未使用，保持接口兼容

        Returns:
            向量列表（与输入等长、等序）

        Raises:
            RuntimeError: 客户端初始化失败时
        """
        if not texts:
            return []

        self._ensure_client()

        if self._client is None:
            raise RuntimeError(
                "SiliconFlow embedding client not available. "
                "Check SILICONFLOW_API_KEY environment variable."
            )

        try:
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )

            # 按 index 排序确保与输入顺序一致
            sorted_data = sorted(response.data, key=lambda x: x.index)
            embeddings = [item.embedding for item in sorted_data]

            logger.debug("SiliconFlow embedding: %d texts -> %d vectors (dim=%d)",
                         len(texts), len(embeddings), len(embeddings[0]) if embeddings else 0)
            return embeddings

        except Exception as e:
            logger.error("SiliconFlow embedding API call failed: %s", e)
            raise

    def encode_single(self, text: str) -> list[float]:
        """编码单条文本为向量

        Args:
            text: 单条文本

        Returns:
            向量
        """
        results = self.encode([text])
        return results[0]
