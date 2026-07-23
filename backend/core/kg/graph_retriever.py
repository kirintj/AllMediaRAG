"""Graph retriever: resolve query entities → graph_candidates → chunk IDs."""

from __future__ import annotations

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

LAW_PATTERN = re.compile(
    r'(?:中华人民共和国)?[一-鿿]{2,20}(?:法|条例|规定|办法|决定|'
    r'意见|通知|细则|准则|通则|方案|标准)(?:（[^）]+）)?'
)


class GraphRetriever:
    """Orchestrates entity resolution and graph candidate expansion."""

    def __init__(self, graph_store: Any, llm: Any = None):
        self._graph_store = graph_store
        self._llm = llm
        self._alias_map: dict[str, str] = {}  # alias_text → canonical_name
        self._all_aliases: set[str] = set()

    def load_aliases(self) -> None:
        """Load all aliases from Neo4j at startup for in-memory lookup."""
        try:
            with self._graph_store._driver.session() as session:
                result = session.run(
                    "MATCH (a:Alias)-[:RESOLVES_TO]->(e:Entity) "
                    "RETURN a.text AS alias, e.name AS canonical"
                )
                for record in result:
                    alias = record["alias"]
                    canonical = record["canonical"]
                    self._alias_map[alias] = canonical
                    self._all_aliases.add(alias)
            logger.info("Loaded %d aliases for entity resolution", len(self._all_aliases))
        except Exception as e:
            logger.warning("Failed to load aliases: %s", e)

    def resolve_entities(self, query: str) -> list[str]:
        """Find canonical entity names in the query."""
        resolved = set()

        # Alias match (in-memory, no Neo4j call)
        for alias in self._all_aliases:
            if alias in query:
                resolved.add(self._alias_map[alias])

        # Regex match for law names
        for match in LAW_PATTERN.finditer(query):
            name = match.group()
            if name in self._alias_map:
                resolved.add(self._alias_map[name])
            else:
                resolved.add(name)

        return list(resolved)

    def search(self, query: str, max_chunks: int = 20) -> list[str]:
        """Full pipeline: resolve → expand → map → chunk IDs."""
        seed_entities = self.resolve_entities(query)
        if not seed_entities:
            return []
        return self._graph_store.graph_candidates(seed_entities, max_chunks=max_chunks)

    # ── Enhanced Retrieve ──────────────────────────────────────────

    def retrieve(self, query: str, top_k: int = 6) -> str | None:
        """增强检索：查询分析 + 实体检索 + N-hop + 社区报告

        Returns:
            格式化的图谱上下文文本，或 None
        """
        # 1. 查询分析
        entities, types = self._analyze_query(query)
        if not entities and not types:
            return None

        # 2. 实体检索
        matched_entities = self._search_entities(entities, types, top_k)
        if not matched_entities:
            return None

        # 3. N-hop 路径
        entity_ids = [e.get("id", "") for e in matched_entities if e.get("id")]
        paths = self._graph_store.get_n_hop_paths(entity_ids, max_hops=2)

        # 4. 关系检索
        relations = self._search_relations(entity_ids, top_k)

        # 5. 社区报告
        communities = self._graph_store.get_community_reports(entity_ids)

        # 6. 格式化
        return self._format_context(matched_entities, relations, paths, communities)

    def _analyze_query(self, query: str) -> tuple[list[str], list[str]]:
        """LLM 从问题提取实体名和类型"""
        try:
            from core.enrichment.prompt_loader import load_prompt
            from core.config import config
            prompt = load_prompt(
                "query_analyze.md",
                query=query,
                entity_types=", ".join(config.graphrag_entity_types),
            )
            result = self._llm.generate(prompt)
            import json
            cleaned = result.strip().strip("```json").strip("```")
            data = json.loads(cleaned)
            return data.get("entities", []), data.get("types", [])
        except Exception as e:
            logger.warning("Query analysis failed: %s", e)
            # Fallback: 直接用查询文本做实体名匹配
            return [query[:20]], []

    def _search_entities(self, entity_names: list[str],
                         entity_types: list[str], top_k: int) -> list[dict]:
        """Neo4j 实体检索"""
        try:
            conditions = []
            params: dict[str, Any] = {"limit": top_k}

            if entity_names:
                name_conditions = " OR ".join(
                    f"e.name CONTAINS $name_{i}"
                    for i in range(len(entity_names))
                )
                conditions.append(f"({name_conditions})")
                for i, name in enumerate(entity_names):
                    params[f"name_{i}"] = name

            if entity_types:
                conditions.append("e.type IN $types")
                params["types"] = entity_types

            where = " AND ".join(conditions) if conditions else "true"
            query = (
                f"MATCH (e:Entity) WHERE {where} "
                "RETURN e ORDER BY COALESCE(e.pagerank, 0.001) DESC "
                "LIMIT $limit"
            )

            with self._graph_store._driver.session() as session:
                result = session.run(query, **params)
                entities = []
                for record in result:
                    e = record["e"]
                    entities.append({
                        "id": e.get("id", ""),
                        "name": e.get("name", ""),
                        "type": e.get("type", ""),
                        "description": e.get("description", ""),
                        "pagerank": e.get("pagerank", 0.001),
                    })
                return entities
        except Exception as e:
            logger.warning("Entity search failed: %s", e)
            return []

    def _search_relations(self, entity_ids: list[str],
                          top_k: int) -> list[dict]:
        """关系检索"""
        try:
            with self._graph_store._driver.session() as session:
                result = session.run(
                    "MATCH (a:Entity)-[r:RELATES]->(b:Entity) "
                    "WHERE a.id IN $ids OR b.id IN $ids "
                    "RETURN a.name AS src, b.name AS tgt, "
                    "r.description AS desc, r.weight AS weight "
                    "ORDER BY COALESCE(r.weight, 1) DESC LIMIT $limit",
                    ids=entity_ids, limit=top_k,
                )
                return [
                    {
                        "source": r["src"],
                        "target": r["tgt"],
                        "description": r["desc"],
                        "weight": r.get("weight", 1),
                    }
                    for r in result
                ]
        except Exception as e:
            logger.warning("Relation search failed: %s", e)
            return []

    def _format_context(self, entities: list[dict],
                        relations: list[dict],
                        paths: list[dict],
                        communities: list[dict]) -> str | None:
        """将检索结果格式化为可读文本"""
        parts: list[str] = []
        if entities:
            parts.append("## 知识图谱 - 相关实体")
            for e in entities:
                pr = e.get("pagerank", 0)
                parts.append(
                    f"- **{e['name']}** ({e.get('type', '')}): "
                    f"{e.get('description', '')} [重要性: {pr:.3f}]"
                )
        if relations:
            parts.append("\n## 知识图谱 - 相关关系")
            for r in relations:
                parts.append(
                    f"- {r['source']} → {r['target']}: "
                    f"{r.get('description', '')} (权重: {r.get('weight', 1)})"
                )
        if paths:
            parts.append("\n## 知识图谱 - 关联路径")
            for p in paths[:5]:
                parts.append(f"- {p['path_text']}")
        if communities:
            parts.append("\n## 知识图谱 - 社区报告")
            for c in communities:
                parts.append(f"- {c['report']}")
        return "\n".join(parts) if parts else None
