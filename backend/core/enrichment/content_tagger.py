"""Content Tagger -- two-pass tag annotation aligned with RAGFlow.

Pass 1: BM25 fast match (no LLM)
Pass 2: LLM annotation (few-shot + tag set)
asyncio.gather for parallelism
Redis cache
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from typing import TYPE_CHECKING

from core.enrichment.prompt_loader import load_prompt

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle
    from core.enrichment.cache import LLMCache
    from core.tag_kb import TagKBManager

logger = logging.getLogger(__name__)


class ContentTagger:
    """Two-pass tag annotator."""

    def __init__(
        self,
        llm_bundle: LLMBundle,
        cache: LLMCache,
        tag_kb_manager: TagKBManager,
        topn: int = 3,
    ):
        self._llm = llm_bundle
        self._cache = cache
        self._tag_kb = tag_kb_manager
        self._topn = topn

    def tag(self, chunks: list[dict], tag_kb_ids: list[str]) -> list[dict]:
        """Sync entry point."""
        if not tag_kb_ids:
            return chunks

        # 1. Gather tag set from all tag KBs
        all_tags: dict[str, float] = {}
        for kb_id in tag_kb_ids:
            tags = self._tag_kb.get_all_tags(kb_id)
            all_tags.update(tags)

        if not all_tags:
            logger.warning("No tags found in tag KBs: %s", tag_kb_ids)
            return chunks

        tag_list = sorted(all_tags.keys())

        # 2. Pass 1: BM25 fast match
        examples: list[dict] = []
        to_tag: list[dict] = []
        for chunk in chunks:
            matched = self._bm25_match(chunk, tag_list)
            if matched:
                chunk["metadata"]["tag_feas"] = matched
                examples.append({
                    "content": chunk["text"][:500],
                    "tags_json": json.dumps(matched, ensure_ascii=False),
                })
            else:
                to_tag.append(chunk)

        logger.info(
            "Content tagging: %d BM25 matched, %d need LLM",
            len(examples),
            len(to_tag),
        )

        # 3. Pass 2: LLM annotation
        for chunk in to_tag:
            self._llm_tag_one(chunk, tag_list, examples)

        return chunks

    async def tag_async(self, chunks: list[dict], tag_kb_ids: list[str]) -> list[dict]:
        """Async entry point: parallel LLM tagging."""
        if not tag_kb_ids:
            return chunks

        all_tags: dict[str, float] = {}
        for kb_id in tag_kb_ids:
            tags = self._tag_kb.get_all_tags(kb_id)
            all_tags.update(tags)

        if not all_tags:
            return chunks

        tag_list = sorted(all_tags.keys())

        examples: list[dict] = []
        to_tag: list[dict] = []
        for chunk in chunks:
            matched = self._bm25_match(chunk, tag_list)
            if matched:
                chunk["metadata"]["tag_feas"] = matched
                examples.append({
                    "content": chunk["text"][:500],
                    "tags_json": json.dumps(matched, ensure_ascii=False),
                })
            else:
                to_tag.append(chunk)

        # Parallel LLM tagging
        tasks = [
            self._llm_tag_one_async(chunk, tag_list, examples)
            for chunk in to_tag
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        return chunks

    def _bm25_match(self, chunk: dict, tag_list: list[str]) -> dict:
        """Simplified BM25: keyword containment match."""
        text = chunk["text"].lower()
        matched: dict[str, int] = {}
        for tag in tag_list:
            if tag.lower() in text:
                matched[tag] = 8
        # Keep only topn
        if len(matched) > self._topn:
            sorted_tags = sorted(matched.items(), key=lambda x: x[1], reverse=True)
            matched = dict(sorted_tags[: self._topn])
        return matched

    def _llm_tag_one(
        self,
        chunk: dict,
        tag_list: list[str],
        examples: list[dict],
    ):
        """LLM-tag a single chunk."""
        text = chunk["text"][:1000]
        cache_key_tags = ",".join(tag_list[:50])
        cached = self._cache.get(
            "chat",
            text,
            "content_tagging",
            {"tags": cache_key_tags, "topn": self._topn},
        )
        if cached:
            chunk["metadata"]["tag_feas"] = self._parse_tags(cached)
            return

        # Randomly pick 2 few-shot examples
        selected_examples = random.sample(examples, min(2, len(examples)))
        if not selected_examples:
            selected_examples = [
                {"content": "sample text", "tags_json": '{"sample_tag": 5}'}
            ]

        all_tags_str = ", ".join(tag_list)
        prompt = load_prompt(
            "content_tagging_prompt.md",
            all_tags=all_tags_str,
            examples=selected_examples,
            topn=self._topn,
            content=text,
        )
        try:
            result = self._llm.generate(prompt)
            self._cache.set(
                "chat",
                text,
                "content_tagging",
                result,
                {"tags": cache_key_tags, "topn": self._topn},
            )
            chunk["metadata"]["tag_feas"] = self._parse_tags(result)
        except Exception as e:
            logger.warning("Content tagging LLM failed: %s", e)
            chunk["metadata"]["tag_feas"] = {}

    async def _llm_tag_one_async(
        self,
        chunk: dict,
        tag_list: list[str],
        examples: list[dict],
    ):
        """Async wrapper (delegates to sync for now)."""
        self._llm_tag_one(chunk, tag_list, examples)

    def _parse_tags(self, result: str) -> dict:
        """Parse LLM JSON tag response."""
        try:
            cleaned = result.strip().strip("```json").strip("```").strip()
            tags = json.loads(cleaned)
            if isinstance(tags, dict):
                return {k: int(v) for k, v in tags.items() if int(v) > 0}
        except (json.JSONDecodeError, ValueError):
            pass
        return {}
