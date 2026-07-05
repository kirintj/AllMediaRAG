"""Two-prompt LLM entity and relationship extraction for knowledge graph."""

from __future__ import annotations

import json
import logging
from typing import Any

from core.kg.graph_store import ExtractedEntity, ExtractedRelation

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"Law", "Organization"}
VALID_PREDICATES = {
    "制定", "修订", "适用于", "定义了", "上位法", "实施细则",
    "隶属于", "援引", "抵触", "解释", "细化", "废止",
}

ENTITY_PROMPT = """从以下法律文本中提取所有法律法规名称和机构名称。

## 文本
{chunk_text}

## 输出（严格 JSON 数组）
[
  {{"name": "中华人民共和国数据安全法", "type": "Law", "aliases": ["数据安全法", "数安法"]}},
  {{"name": "全国人大常委会", "type": "Organization", "aliases": []}}
]

规则：
- 只提取法律法规（type: Law）和机构（type: Organization）
- 法律名称保留"中华人民共和国"前缀
- aliases 填写常见简称
- 不要提取概念、术语、行为等
- 只输出 JSON，不要其他文字"""

RELATION_PROMPT = """根据以下文本和已提取的实体列表，提取实体之间的关系。

## 实体
{entities_json}

## 允许的关系类型
- 制定: Organization → Law（"全国人大常委会制定数据安全法"）
- 修订: Law → Law（新法修订旧法）
- 适用于: Law → 法律概念/领域（"数据安全法适用于数据处理活动"）
- 定义了: Law → 法律概念/术语（"个人信息保护法定义了敏感个人信息"）
- 上位法: Law → Law（上位法在前，下位法在后）
- 隶属于: Organization → Organization
- 援引、抵触、解释、细化、废止

## 文本
{chunk_text}

## 输出（严格 JSON 数组）
[
  {{"subject": "全国人大常委会", "predicate": "制定", "object": "中华人民共和国数据安全法"}}
]

注意：subject 和 object 必须是上面列出的实体名称，或文本中明确出现的名称。
只输出 JSON，不要其他文字."""


class KGExtractor:
    """Two-prompt LLM knowledge extraction."""

    def __init__(self, llm_client: Any):
        self._llm = llm_client

    async def extract_entities(self, chunk_text: str) -> list[ExtractedEntity]:
        """Stage 1: Extract Law and Organization entities."""
        try:
            truncated = chunk_text[:2000]
            prompt = ENTITY_PROMPT.format(chunk_text=truncated)
            raw = await self._llm.generate(prompt)
            raw = raw.strip().strip("```json").strip("```").strip()
            items = json.loads(raw)
            return [
                ExtractedEntity(
                    name=item["name"].strip(),
                    type=item["type"],
                    aliases=[a.strip() for a in item.get("aliases", [])],
                )
                for item in items
                if item.get("type") in VALID_ENTITY_TYPES
                and item.get("name")
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Entity extraction failed: %s", e)
            return []

    async def extract_relations(
        self, chunk_text: str, entities: list[ExtractedEntity]
    ) -> list[ExtractedRelation]:
        """Stage 2: Extract relationships between known entities."""
        try:
            entities_json = json.dumps(
                [{"name": e.name, "type": e.type} for e in entities],
                ensure_ascii=False,
            )
            truncated = chunk_text[:2000]
            prompt = RELATION_PROMPT.format(
                entities_json=entities_json, chunk_text=truncated,
            )
            raw = await self._llm.generate(prompt)
            raw = raw.strip().strip("```json").strip("```").strip()
            items = json.loads(raw)
            return [
                ExtractedRelation(
                    subject=item["subject"].strip(),
                    predicate=item["predicate"],
                    object=item["object"].strip(),
                )
                for item in items
                if item.get("predicate") in VALID_PREDICATES
                and item.get("subject")
                and item.get("object")
            ]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Relation extraction failed: %s", e)
            return []
