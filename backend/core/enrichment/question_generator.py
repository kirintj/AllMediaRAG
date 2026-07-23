"""自动问题生成

与 RAGFlow 对齐：
- Prompt: question_prompt.md
- 结果每行一个问题，存储为 questions + questions_tks
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


class QuestionGenerator:
    def __init__(self, llm_bundle: LLMBundle, cache: LLMCache, topn: int = 3):
        self._llm = llm_bundle
        self._cache = cache
        self._topn = topn

    def generate(self, chunks: list[dict]) -> list[dict]:
        for chunk in chunks:
            self._generate_one(chunk)
        return chunks

    async def generate_async(self, chunks: list[dict]) -> list[dict]:
        tasks = [self._generate_one_async(chunk) for chunk in chunks]
        await asyncio.gather(*tasks, return_exceptions=True)
        return chunks

    def _generate_one(self, chunk: dict):
        text = chunk["text"][:1000]
        cached = self._cache.get("chat", text, "questions", {"topn": self._topn})
        if cached:
            chunk["metadata"]["questions"] = [q.strip() for q in cached.split("\n") if q.strip()]
            return

        prompt = load_prompt("question_prompt.md", topn=self._topn, content=text)
        try:
            result = self._llm.generate(prompt)
            self._cache.set("chat", text, "questions", result, {"topn": self._topn})
            chunk["metadata"]["questions"] = [q.strip() for q in result.split("\n") if q.strip()]
        except Exception as e:
            logger.warning("Question generation failed: %s", e)
            chunk["metadata"]["questions"] = []

    async def _generate_one_async(self, chunk: dict):
        text = chunk["text"][:1000]
        cached = self._cache.get("chat", text, "questions", {"topn": self._topn})
        if cached:
            chunk["metadata"]["questions"] = [q.strip() for q in cached.split("\n") if q.strip()]
            return

        prompt = load_prompt("question_prompt.md", topn=self._topn, content=text)
        try:
            result = self._llm.generate(prompt)
            self._cache.set("chat", text, "questions", result, {"topn": self._topn})
            chunk["metadata"]["questions"] = [q.strip() for q in result.split("\n") if q.strip()]
        except Exception as e:
            logger.warning("Question generation failed: %s", e)
            chunk["metadata"]["questions"] = []
