"""Rerank providers -- 重排序模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 RerankModel 注册表。
"""
from __future__ import annotations

import logging
from operator import itemgetter

logger = logging.getLogger(__name__)


# ── Cohere ────────────────────────────────────────────────────────────────────

class CohereRerank:
    """Cohere Rerank API"""

    _FACTORY_NAME = "Cohere"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        import cohere

        client = cohere.Client(self._api_key)
        resp = client.rerank(
            model=self._model,
            query=query,
            documents=documents,
            top_n=top_k,
        )
        results = []
        for item in resp.results:
            results.append({
                "index": item.index,
                "text": documents[item.index],
                "score": item.relevance_score,
            })
        return sorted(results, key=itemgetter("score"), reverse=True)


# ── BGE (本地 CrossEncoder) ──────────────────────────────────────────────────

class BGERerank:
    """BGE Reranker，通过 sentence_transformers.CrossEncoder 本地推理"""

    _FACTORY_NAME = "BGE"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        from sentence_transformers import CrossEncoder

        self._model = CrossEncoder(model_name)

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        pairs = [[query, doc] for doc in documents]
        scores = self._model.predict(pairs)
        scored = [
            {"index": i, "text": doc, "score": float(score)}
            for i, (doc, score) in enumerate(zip(documents, scores))
        ]
        scored.sort(key=itemgetter("score"), reverse=True)
        return scored[:top_k]


# ── SiliconFlow ───────────────────────────────────────────────────────────────

class SiliconFlowRerank:
    """SiliconFlow Rerank API"""

    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://api.siliconflow.cn/v1"

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        import requests

        url = f"{self._base_url}/rerank"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "query": query,
            "documents": documents,
            "top_n": top_k,
            "return_documents": False,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            idx = item.get("index", 0)
            results.append({
                "index": idx,
                "text": documents[idx],
                "score": item.get("relevance_score", 0.0),
            })
        return sorted(results, key=itemgetter("score"), reverse=True)


# ── Jina ──────────────────────────────────────────────────────────────────────

class JinaRerank:
    """Jina Rerank API (OpenAI-compatible rerank endpoint)"""

    _FACTORY_NAME = "Jina"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://api.jina.ai/v1"

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        import requests

        url = f"{self._base_url}/rerank"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "query": query,
            "documents": documents,
            "top_n": top_k,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            idx = item.get("index", 0)
            results.append({
                "index": idx,
                "text": documents[idx],
                "score": item.get("relevance_score", 0.0),
            })
        return sorted(results, key=itemgetter("score"), reverse=True)


# ── Tongyi-Qianwen / DashScope ───────────────────────────────────────────────

class TongyiQianwenRerank:
    """阿里通义千问 Rerank API (DashScope)"""

    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://dashscope.aliyuncs.com/api/v1"

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        import requests

        url = f"{self._base_url}/services/rerank/text-reranking/text-reranking"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": {
                "query": query,
                "documents": documents,
            },
            "parameters": {
                "top_n": top_k,
                "return_documents": False,
            },
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("output", {}).get("results", []):
            idx = item.get("index", 0)
            results.append({
                "index": idx,
                "text": documents[idx],
                "score": item.get("relevance_score", 0.0),
            })
        return sorted(results, key=itemgetter("score"), reverse=True)
