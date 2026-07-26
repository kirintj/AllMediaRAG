"""Embedding providers -- 向量嵌入模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 EmbeddingModel 注册表。
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIEmbedding:
    """OpenAI Embeddings API"""

    _FACTORY_NAME = "OpenAI"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def encode(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]

    def encode_queries(self, queries: list[str]) -> list[list[float]]:
        return self.encode(queries)

    @staticmethod
    def similarity(a: list[float], b: list[float]) -> float:
        import numpy as np

        a_np, b_np = np.array(a), np.array(b)
        return float(
            np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8)
        )


# ── Ollama (OpenAI-compatible at /v1) ─────────────────────────────────────────

class OllamaEmbedding:
    """Ollama 本地 Embedding，通过 OpenAI-compatible /v1 端点调用"""

    _FACTORY_NAME = "Ollama"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key or "ollama"
        self._model = model_name
        self._base_url = base_url or "http://localhost:11434/v1"

    def encode(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]

    def encode_queries(self, queries: list[str]) -> list[list[float]]:
        return self.encode(queries)

    @staticmethod
    def similarity(a: list[float], b: list[float]) -> float:
        import numpy as np

        a_np, b_np = np.array(a), np.array(b)
        return float(
            np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8)
        )


# ── HuggingFace (本地 sentence-transformers) ──────────────────────────────────

class HuggingFaceEmbedding:
    """通过 sentence-transformers 加载本地模型"""

    _FACTORY_NAME = "HuggingFace"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()

    def encode_queries(self, queries: list[str]) -> list[list[float]]:
        return self.encode(queries)

    @staticmethod
    def similarity(a: list[float], b: list[float]) -> float:
        import numpy as np

        a_np, b_np = np.array(a), np.array(b)
        return float(
            np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8)
        )


# ── SiliconFlow (OpenAI-compatible) ───────────────────────────────────────────

class SiliconFlowEmbedding:
    """SiliconFlow Embedding API，兼容 OpenAI 接口"""

    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://api.siliconflow.cn/v1"

    def encode(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]

    def encode_queries(self, queries: list[str]) -> list[list[float]]:
        return self.encode(queries)

    @staticmethod
    def similarity(a: list[float], b: list[float]) -> float:
        import numpy as np

        a_np, b_np = np.array(a), np.array(b)
        return float(
            np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8)
        )


# ── Tongyi-Qianwen / DashScope (OpenAI-compatible) ───────────────────────────

class TongyiQianwenEmbedding:
    """阿里通义千问 Embedding，通过 DashScope OpenAI-compatible 接口调用"""

    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def encode(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        all_embeddings: list[list[float]] = []
        batch_size = 20  # DashScope 限制单次最多 20 条
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            resp = client.embeddings.create(model=self._model, input=batch)
            all_embeddings.extend(item.embedding for item in resp.data)
        return all_embeddings

    def encode_queries(self, queries: list[str]) -> list[list[float]]:
        return self.encode(queries)

    @staticmethod
    def similarity(a: list[float], b: list[float]) -> float:
        import numpy as np

        a_np, b_np = np.array(a), np.array(b)
        return float(
            np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8)
        )
