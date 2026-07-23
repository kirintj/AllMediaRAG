"""实体消歧：编辑距离 + LLM 批量确认"""
from __future__ import annotations

import logging
from itertools import combinations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle

logger = logging.getLogger(__name__)


class EntityResolver:
    def __init__(self, llm_bundle: LLMBundle):
        self._llm = llm_bundle

    def find_candidates(self, new_entities: list[dict], existing_entities: list[dict]) -> list[tuple[dict, dict]]:
        """生成候选对（编辑距离过滤）"""
        candidates = []
        # 按类型分组
        new_by_type = self._group_by_type(new_entities)
        existing_by_type = self._group_by_type(existing_entities)

        for etype in set(list(new_by_type.keys()) + list(existing_by_type.keys())):
            new_ents = new_by_type.get(etype, [])
            old_ents = existing_by_type.get(etype, [])
            for ne in new_ents:
                for oe in old_ents:
                    if self._is_candidate(ne["name"], oe["name"]):
                        candidates.append((ne, oe))
        return candidates

    def confirm_batch(self, candidates: list[tuple[dict, dict]]) -> list[tuple[dict, dict]]:
        """LLM 批量确认"""
        if not candidates:
            return []

        confirmed = []
        for i in range(0, len(candidates), 100):
            batch = candidates[i:i+100]
            result = self._llm_confirm(batch)
            confirmed.extend(result)
        return confirmed

    def _llm_confirm(self, batch: list[tuple[dict, dict]]) -> list[tuple[dict, dict]]:
        """LLM 确认一批候选对"""
        from core.enrichment.prompt_loader import load_prompt

        pairs = [(a["name"], b["name"]) for a, b in batch]
        prompt = load_prompt("entity_resolution.md", pairs=pairs)
        try:
            result = self._llm.generate(prompt)
            import json
            cleaned = result.strip().strip("```json").strip("```")
            judgments = json.loads(cleaned)
            confirmed = []
            for j in judgments:
                if j.get("same"):
                    idx = next((i for i, p in enumerate(pairs)
                                if p[0] == j["name1"] and p[1] == j["name2"]), -1)
                    if idx >= 0:
                        confirmed.append(batch[idx])
            return confirmed
        except Exception as e:
            logger.warning("Entity resolution LLM failed: %s", e)
            return []

    def _is_candidate(self, name1: str, name2: str) -> bool:
        if name1 == name2:
            return False
        set1, set2 = set(name1), set(name2)
        overlap = len(set1 & set2) / max(len(set1 | set2), 1)
        if any('一' <= c <= '鿿' for c in name1 + name2):
            return overlap >= 0.8
        return self._edit_distance(name1, name2) <= 2

    @staticmethod
    def _edit_distance(s1: str, s2: str) -> int:
        m, n = len(s1), len(s2)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                if s1[i-1] == s2[j-1]:
                    dp[j] = prev
                else:
                    dp[j] = 1 + min(prev, dp[j], dp[j-1])
                prev = temp
        return dp[n]

    @staticmethod
    def _group_by_type(entities: list[dict]) -> dict[str, list[dict]]:
        groups = {}
        for e in entities:
            t = e.get("type", "unknown")
            groups.setdefault(t, []).append(e)
        return groups
