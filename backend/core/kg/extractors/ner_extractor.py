"""NER Extractor — spaCy 基础提取

- 无需 LLM 调用，速度快
- 实体由 spaCy NER 识别
- 关系通过共现（同一 chunk 内的实体对）
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import BaseExtractor

logger = logging.getLogger(__name__)

# spaCy NER 标签到通用类型的映射
NER_TYPE_MAP = {
    "PERSON": "person",
    "PER": "person",
    "ORG": "organization",
    "GPE": "geo",
    "LOC": "geo",
    "FAC": "geo",
    "EVENT": "event",
    "PRODUCT": "category",
    "WORK_OF_ART": "category",
    "LAW": "category",
    "LANGUAGE": "category",
}


class NERExtractor(BaseExtractor):
    def __init__(self, spacy_model: str = "zh_core_web_sm"):
        self._model_name = spacy_model
        self._nlp = None

    def _load_model(self):
        if self._nlp is None:
            try:
                import spacy
                self._nlp = spacy.load(self._model_name)
            except Exception as e:
                logger.error("Failed to load spaCy model %s: %s", self._model_name, e)
                raise

    def extract(self, chunks: list[dict]) -> tuple[list[dict], list[dict]]:
        self._load_model()
        all_entities, all_relations = [], []
        for chunk in chunks:
            ents, rels = self._extract_one(chunk["text"], chunk.get("metadata", {}))
            all_entities.extend(ents)
            all_relations.extend(rels)
        return all_entities, all_relations

    def _extract_one(self, text: str, metadata: dict) -> tuple[list[dict], list[dict]]:
        source_id = metadata.get("chunk_id", "")
        doc = self._nlp(text[:5000])

        # 提取实体
        entities = []
        seen = set()
        for ent in doc.ents:
            name = ent.text.strip()
            if len(name) < 2 or name in seen:
                continue
            seen.add(name)
            entity_type = NER_TYPE_MAP.get(ent.label_, "category")
            entities.append({
                "name": name,
                "type": entity_type,
                "description": f"{name}（{ent.label_}）",
                "source_id": source_id,
            })

        # 共现关系（同一 chunk 中的实体对）
        relations = []
        for i in range(len(entities)):
            for j in range(i + 1, len(entities)):
                relations.append({
                    "source": entities[i]["name"],
                    "target": entities[j]["name"],
                    "description": f"{entities[i]['name']}与{entities[j]['name']}在同一上下文中提及",
                    "weight": 1,
                    "keywords": [],
                })

        return entities, relations
