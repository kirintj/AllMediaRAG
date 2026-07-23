"""LLM 调用缓存层

与 RAGFlow 对齐：Redis + sha256 key + 24h TTL。
重复文档处理时跳过已缓存的 LLM 调用。
"""
from __future__ import annotations

import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class LLMCache:
    """LLM 调用结果缓存"""

    def __init__(self, redis_client, ttl: int = 86400):
        self._redis = redis_client
        self._ttl = ttl

    def _make_key(self, llm_name: str, content: str, task_type: str, params: dict | None = None) -> str:
        raw = f"{llm_name}|{content}|{task_type}|{json.dumps(params or {}, sort_keys=True)}"
        return f"llm_cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    def get(self, llm_name: str, content: str, task_type: str, params: dict | None = None) -> str | None:
        """查询缓存，命中返回结果字符串，未命中返回 None"""
        if not self._redis:
            return None
        try:
            key = self._make_key(llm_name, content, task_type, params)
            val = self._redis.get(key)
            return val.decode() if val else None
        except Exception as e:
            logger.debug("LLM cache get failed: %s", e)
            return None

    def set(self, llm_name: str, content: str, task_type: str, value: str, params: dict | None = None):
        """写入缓存"""
        if not self._redis:
            return
        try:
            key = self._make_key(llm_name, content, task_type, params)
            self._redis.setex(key, self._ttl, value)
        except Exception as e:
            logger.debug("LLM cache set failed: %s", e)

    def clear(self):
        """清空所有 LLM 缓存"""
        if not self._redis:
            return
        try:
            for key in self._redis.scan_iter("llm_cache:*", count=100):
                self._redis.delete(key)
        except Exception as e:
            logger.debug("LLM cache clear failed: %s", e)
