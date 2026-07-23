"""实体/关系合并 + 关系验证

与 RAGFlow 对齐：
- 同名实体合并（类型投票 + 描述拼接）
- 同对关系合并（权重叠加 + 描述拼接）
- 关系验证（负面模式过滤）
"""
from __future__ import annotations

import logging
from collections import Counter

logger = logging.getLogger(__name__)

NEGATIVE_PATTERNS = [
    "no clear relationship", "not directly linked", "no direct relationship",
    "unrelated", "no relationship", "无明确关系", "无直接关联", "没有关系",
    "没有关联", "不相关",
]


class GraphMerger:
    """实体/关系合并器"""

    def merge_entities(self, entities: list[dict], llm_bundle=None) -> list[dict]:
        """同名实体合并"""
        by_name: dict[str, dict] = {}
        for e in entities:
            key = e["name"].lower().strip()
            if not key:
                continue
            if key in by_name:
                self._merge_one_entity(by_name[key], e, llm_bundle)
            else:
                by_name[key] = dict(e)  # copy
        return list(by_name.values())

    def merge_relations(self, relations: list[dict]) -> list[dict]:
        """同对关系合并"""
        by_pair: dict[tuple, dict] = {}
        for r in relations:
            src = r.get("source", "").lower().strip()
            tgt = r.get("target", "").lower().strip()
            if not src or not tgt:
                continue
            key = tuple(sorted([src, tgt]))
            if key in by_pair:
                self._merge_one_relation(by_pair[key], r)
            else:
                by_pair[key] = dict(r)
        return list(by_pair.values())

    def validate_relations(self, relations: list[dict]) -> list[dict]:
        """关系验证：丢弃负面模式关系"""
        valid = []
        for r in relations:
            desc = r.get("description", "").lower()
            if any(p in desc for p in NEGATIVE_PATTERNS):
                logger.debug("Filtered negative relation: %s -> %s: %s",
                             r.get("source"), r.get("target"), desc[:50])
                continue
            valid.append(r)
        return valid

    def _merge_one_entity(self, target: dict, source: dict, llm_bundle=None):
        """合并一个实体到 target"""
        # 类型：多数投票（简化：保留 target 的类型）
        # 描述：拼接
        desc = source.get("description", "").strip()
        existing_desc = target.get("description", "")
        if desc and desc not in existing_desc:
            if existing_desc:
                target["description"] = f"{existing_desc}<SEP>{desc}"
            else:
                target["description"] = desc

        # 来源合并
        source_ids = target.get("source_ids", set())
        if isinstance(source_ids, str):
            source_ids = {source_ids}
        sid = source.get("source_id", "")
        if sid:
            source_ids.add(sid)
        target["source_ids"] = source_ids

        # 描述过长时摘要
        desc_parts = target["description"].split("<SEP>")
        if len(desc_parts) > 12 and llm_bundle:
            try:
                from core.enrichment.prompt_loader import load_prompt
                prompt = load_prompt(
                    "summarize_descriptions.md",
                    entity_name=target.get("name", ""),
                    entity_type=target.get("type", ""),
                    descriptions="\n".join(desc_parts[:20]),
                )
                target["description"] = llm_bundle.generate(prompt)
            except Exception as e:
                logger.warning("Description summarization failed: %s", e)

    def _merge_one_relation(self, target: dict, source: dict):
        """合并一个关系到 target"""
        target["weight"] = target.get("weight", 1) + source.get("weight", 1)

        desc = source.get("description", "").strip()
        existing_desc = target.get("description", "")
        if desc and desc not in existing_desc:
            target["description"] = f"{existing_desc}<SEP>{desc}" if existing_desc else desc

        # 关键词并集
        kw = set(target.get("keywords", []))
        kw.update(source.get("keywords", []))
        target["keywords"] = list(kw)
