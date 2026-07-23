"""目录提取（两阶段）

与 RAGFlow 对齐：
- Stage 1: 按 token 预算分批，提取标题
- Stage 2: 分配层级
- Prompt: toc_system_prompt.md + toc_user_prompt.md + toc_level_prompt.md
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

from core.enrichment.prompt_loader import load_prompt

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle
    from core.enrichment.cache import LLMCache

logger = logging.getLogger(__name__)


class TOCBuilder:
    def __init__(self, llm_bundle: LLMBundle, cache: LLMCache):
        self._llm = llm_bundle
        self._cache = cache

    def build(self, source: str, chunks: list[dict]) -> dict | None:
        """同步版本"""
        if len(chunks) < 2:
            return None
        batches = self._split_batches(chunks, max_chars=4000)
        all_titles = []
        for batch in batches:
            titles = self._extract_titles_batch(batch)
            all_titles.extend(titles)
        if not all_titles:
            return None
        return self._assign_levels(all_titles)

    async def build_async(self, source: str, chunks: list[dict]) -> dict | None:
        """异步版本：Stage 1 并发"""
        if len(chunks) < 2:
            return None
        batches = self._split_batches(chunks, max_chars=4000)
        results = await asyncio.gather(*[
            self._extract_titles_batch_async(batch) for batch in batches
        ], return_exceptions=True)
        all_titles = []
        for r in results:
            if isinstance(r, list):
                all_titles.extend(r)
        if not all_titles:
            return None
        return await self._assign_levels_async(all_titles)

    def _split_batches(self, chunks: list[dict], max_chars: int = 4000) -> list[list[dict]]:
        batches = []
        current = []
        current_len = 0
        for chunk in chunks:
            clen = len(chunk["text"])
            if current_len + clen > max_chars and current:
                batches.append(current)
                current = []
                current_len = 0
            current.append(chunk)
            current_len += clen
        if current:
            batches.append(current)
        return batches

    def _extract_titles_batch(self, batch: list[dict]) -> list[dict]:
        text = "\n\n".join(f"[chunk_{i}] {c['text'][:500]}" for i, c in enumerate(batch))
        cached = self._cache.get("chat", text[:2000], "toc_extract")
        if cached:
            try:
                return json.loads(cached.strip().strip("```json").strip("```"))
            except json.JSONDecodeError:
                pass

        prompt = load_prompt("toc_system_prompt.md")
        user_prompt = load_prompt("toc_user_prompt.md", text=text)
        full_prompt = f"{prompt}\n\n{user_prompt}"
        try:
            result = self._llm.generate(full_prompt)
            self._cache.set("chat", text[:2000], "toc_extract", result)
            cleaned = result.strip().strip("```json").strip("```")
            return json.loads(cleaned)
        except Exception as e:
            logger.warning("TOC extraction failed: %s", e)
            return []

    async def _extract_titles_batch_async(self, batch: list[dict]) -> list[dict]:
        return self._extract_titles_batch(batch)

    def _assign_levels(self, titles: list[dict]) -> dict:
        titles_str = json.dumps(titles, ensure_ascii=False)
        prompt = load_prompt("toc_level_prompt.md", titles=titles_str)
        try:
            result = self._llm.generate(prompt)
            cleaned = result.strip().strip("```json").strip("```")
            toc_items = json.loads(cleaned)
            return {"type": "toc", "items": toc_items}
        except Exception as e:
            logger.warning("TOC level assignment failed: %s", e)
            return {"type": "toc", "items": titles}

    async def _assign_levels_async(self, titles: list[dict]) -> dict:
        return self._assign_levels(titles)
