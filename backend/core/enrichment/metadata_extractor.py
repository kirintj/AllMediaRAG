"""结构化元数据提取

与 RAGFlow 对齐：
- Prompt: metadata_prompt.md
- 支持用户自定义 JSON Schema
- Strict Evidence Only + Zero-Hallucination 规则
- 输出 JSON 合并到 chunk.metadata
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

DEFAULT_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "description": "主题"},
        "entities": {"type": "array", "items": {"type": "string"}, "description": "实体列表"},
        "summary": {"type": "string", "description": "一句话摘要"},
    },
}


class MetadataExtractor:
    def __init__(self, llm_bundle: LLMBundle, cache: LLMCache, schema: dict | None = None):
        self._llm = llm_bundle
        self._cache = cache
        self._schema = schema or DEFAULT_SCHEMA

    def extract(self, chunks: list[dict]) -> list[dict]:
        for chunk in chunks:
            self._extract_one(chunk)
        return chunks

    async def extract_async(self, chunks: list[dict]) -> list[dict]:
        tasks = [self._extract_one_async(chunk) for chunk in chunks]
        await asyncio.gather(*tasks, return_exceptions=True)
        return chunks

    def _extract_one(self, chunk: dict):
        text = chunk["text"][:1000]
        schema_str = json.dumps(self._schema, ensure_ascii=False)
        cached = self._cache.get("chat", text, "metadata", {"schema": schema_str})
        if cached:
            self._merge_metadata(chunk, cached)
            return

        prompt = load_prompt("metadata_prompt.md", schema=schema_str, content=text)
        try:
            result = self._llm.generate(prompt)
            self._cache.set("chat", text, "metadata", result, {"schema": schema_str})
            self._merge_metadata(chunk, result)
        except Exception as e:
            logger.warning("Metadata extraction failed: %s", e)

    async def _extract_one_async(self, chunk: dict):
        text = chunk["text"][:1000]
        schema_str = json.dumps(self._schema, ensure_ascii=False)
        cached = self._cache.get("chat", text, "metadata", {"schema": schema_str})
        if cached:
            self._merge_metadata(chunk, cached)
            return

        prompt = load_prompt("metadata_prompt.md", schema=schema_str, content=text)
        try:
            result = self._llm.generate(prompt)
            self._cache.set("chat", text, "metadata", result, {"schema": schema_str})
            self._merge_metadata(chunk, result)
        except Exception as e:
            logger.warning("Metadata extraction failed: %s", e)

    def _merge_metadata(self, chunk: dict, result: str):
        try:
            cleaned = result.strip().strip("```json").strip("```").strip()
            if cleaned == "{}":
                return
            meta = json.loads(cleaned)
            if isinstance(meta, dict):
                chunk["metadata"].update(meta)
        except json.JSONDecodeError:
            logger.debug("Metadata JSON parse failed, skipping")
