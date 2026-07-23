"""Light Extractor — LightRAG 风格

- 更简洁的 prompt，更快
- 无 gleaning 轮次
"""
from __future__ import annotations

import re
import logging
from typing import TYPE_CHECKING

from .base import BaseExtractor

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle

logger = logging.getLogger(__name__)


class LightExtractor(BaseExtractor):
    def __init__(self, llm_bundle: LLMBundle, entity_types: list[str] = None):
        self._llm = llm_bundle
        self._entity_types = entity_types or ["organization", "person", "geo", "event"]

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
        prompt = load_prompt("light_extraction.md", entity_types=entity_types_str, content=text[:3000])

        try:
            result = self._llm.generate(prompt)
            return self._parse_result(result, metadata.get("chunk_id", ""))
        except Exception as e:
            logger.warning("Light extraction failed: %s", e)
            return [], []

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
            match_rel = re.match(r'\(relation\|(.+?)\|(.+?)\|(.+?)\)', line)
            if match_rel:
                relations.append({
                    "source": match_rel.group(1).strip(),
                    "target": match_rel.group(2).strip(),
                    "description": match_rel.group(3).strip(),
                    "weight": 1,
                    "keywords": [],
                })
        return entities, relations
