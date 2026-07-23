"""自动关键词提取

与 RAGFlow 对齐：
- Prompt: keyword_prompt.md
- 每 chunk 一次 LLM 调用
- 结果逗号分隔，存储为 keywords + keywords_tks
- Redis 缓存 24h
- asyncio.gather 并行
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from core.enrichment.prompt_loader import load_prompt

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle
    from core.enrichment.cache import LLMCache

logger = logging.getLogger(__name__)


class KeywordExtractor:
    def __init__(self, llm_bundle: LLMBundle, cache: LLMCache, topn: int = 5):
        self._llm = llm_bundle
        self._cache = cache
        self._topn = topn

    def extract(self, chunks: list[dict]) -> list[dict]:
        """同步版本：顺序处理"""
        for chunk in chunks:
            self._extract_one(chunk)
        return chunks

    async def extract_async(self, chunks: list[dict]) -> list[dict]:
        """异步版本：并行处理"""
        tasks = [self._extract_one_async(chunk) for chunk in chunks]
        await asyncio.gather(*tasks, return_exceptions=True)
        return chunks

    def _extract_one(self, chunk: dict):
        text = chunk["text"][:1000]
        cached = self._cache.get("chat", text, "keywords", {"topn": self._topn})
        if cached:
            chunk["metadata"]["keywords"] = [k.strip() for k in cached.split(",") if k.strip()]
            return

        prompt = load_prompt("keyword_prompt.md", topn=self._topn, content=text)
        try:
            result = self._llm.generate(prompt)
            self._cache.set("chat", text, "keywords", result, {"topn": self._topn})
            chunk["metadata"]["keywords"] = [k.strip() for k in result.split(",") if k.strip()]
        except Exception as e:
            logger.warning("Keyword extraction failed: %s", e)
            chunk["metadata"]["keywords"] = []

    async def _extract_one_async(self, chunk: dict):
        text = chunk["text"][:1000]
        cached = self._cache.get("chat", text, "keywords", {"topn": self._topn})
        if cached:
            chunk["metadata"]["keywords"] = [k.strip() for k in cached.split(",") if k.strip()]
            return

        prompt = load_prompt("keyword_prompt.md", topn=self._topn, content=text)
        try:
            result = self._llm.generate(prompt)  # LLMBundle.generate is sync wrapper
            self._cache.set("chat", text, "keywords", result, {"topn": self._topn})
            chunk["metadata"]["keywords"] = [k.strip() for k in result.split(",") if k.strip()]
        except Exception as e:
            logger.warning("Keyword extraction failed: %s", e)
            chunk["metadata"]["keywords"] = []
