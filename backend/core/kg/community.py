"""社区检测（Leiden）+ LLM 社区报告"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle

logger = logging.getLogger(__name__)


class CommunityDetector:
    def __init__(self, llm_bundle: LLMBundle):
        self._llm = llm_bundle

    def detect(self, graph) -> list[list[str]]:
        """Leiden 社区检测

        Args:
            graph: NetworkX graph

        Returns:
            list of communities, each is a list of node IDs
        """
        import networkx.algorithms.community as nx_comm
        try:
            communities = nx_comm.louvain_communities(graph, seed=42)
            return [list(c) for c in communities]
        except Exception as e:
            logger.warning("Community detection failed: %s", e)
            return []

    def generate_report(self, entities: list[dict], relations: list[dict]) -> str:
        """LLM 生成社区报告"""
        from core.enrichment.prompt_loader import load_prompt

        ent_summary = "\n".join(
            f"- {e.get('name', '')}: {e.get('description', '')[:100]}"
            for e in entities[:20]
        )
        rel_summary = "\n".join(
            f"- {r.get('source', '')} -> {r.get('target', '')}: {r.get('description', '')[:100]}"
            for r in relations[:20]
        )
        prompt = load_prompt("community_report.md", entities=ent_summary, relations=rel_summary)
        try:
            return self._llm.generate(prompt)
        except Exception as e:
            logger.warning("Community report generation failed: %s", e)
            return f"社区包含 {len(entities)} 个实体和 {len(relations)} 条关系"
