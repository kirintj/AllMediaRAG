"""General Extractor — Microsoft GraphRAG 风格

- LLM 提取实体 + 关系
- 支持 gleaning（最多 N 轮追加提取）
- 详细 prompt 带 few-shot 示例
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

from .base import BaseExtractor

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle

logger = logging.getLogger(__name__)


class GeneralExtractor(BaseExtractor):
    def __init__(self, llm_bundle: LLMBundle, entity_types: list[str] = None, max_gleanings: int = 2):
        self._llm = llm_bundle
        self._entity_types = entity_types or ["organization", "person", "geo", "event", "category"]
        self._max_gleanings = max_gleanings

    def extract(self, chunks: list[dict]) -> tuple[list[dict], list[dict]]:
        all_entities, all_relations = [], []
        for chunk in chunks:
            ents, rels = self._extract_one(chunk["text"], chunk.get("metadata", {}))
            all_entities.extend(ents)
            all_relations.extend(rels)
        return all_entities, all_relations

    def _extract_one(self, text: str, metadata: dict) -> tuple[list[dict], list[dict]]:
        from core.enrichment.prompt_loader import load_prompt

        entity_types_str = ", ".join(self._entity_types)
        prompt = load_prompt("general_extraction.md", entity_types=entity_types_str, content=text[:3000])

        entities, relations = [], []
        try:
            result = self._llm.generate(prompt)
            entities, relations = self._parse_result(result, metadata.get("chunk_id", ""))
        except Exception as e:
            logger.warning("General extraction failed: %s", e)
            return [], []

        # Gleaning rounds
        for i in range(self._max_gleanings):
            try:
                gleaning_prompt = load_prompt(
                    "gleaning_prompt.md",
                    content=text[:3000],
                    previous_results=result[:1000],
                )
                gleaning_result = self._llm.generate(gleaning_prompt)
                if "NO_NEW_ENTITIES" in gleaning_result:
                    break
                new_ents, new_rels = self._parse_result(gleaning_result, metadata.get("chunk_id", ""))
                entities.extend(new_ents)
                relations.extend(new_rels)
                result += "\n" + gleaning_result
            except Exception:
                break

        return entities, relations

    def _parse_result(self, text: str, source_id: str) -> tuple[list[dict], list[dict]]:
        entities, relations = [], []
        for line in text.split("\n"):
            line = line.strip()
            match_ent = re.match(r'\(entity\|(.+?)\|(.+?)\|(.+?)\)', line)
            if match_ent:
                entities.append({
                    "name": match_ent.group(1).strip(),
                    "type": match_ent.group(2).strip(),
                    "description": match_ent.group(3).strip(),
                    "source_id": source_id,
                })
                continue
            match_rel = re.match(r'\(relation\|(.+?)\|(.+?)\|(.+?)\|(\d+)\|(.+?)\)', line)
            if match_rel:
                keywords = [k.strip() for k in match_rel.group(5).split(";") if k.strip()]
                relations.append({
                    "source": match_rel.group(1).strip(),
                    "target": match_rel.group(2).strip(),
                    "description": match_rel.group(3).strip(),
                    "weight": int(match_rel.group(4)),
                    "keywords": keywords,
                })
        return entities, relations
