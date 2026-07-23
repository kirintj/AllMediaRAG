"""Neo4j graph store for knowledge graph.

Provides ingest (write entities/relations/chunks), delete, and
two-phase graph_candidates (weighted entity expansion → chunk mapping).
"""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

# Relationship weight lookup (hardcoded, not stored per-edge)
RELATE_WEIGHTS: dict[str, float] = {
    "制定": 1.0, "上位法": 0.9, "隶属于": 0.9,
    "实施细则": 0.8, "修订": 0.8, "定义了": 0.7,
    "适用于": 0.6, "解释": 0.6, "细化": 0.6,
    "援引": 0.5, "废止": 0.4, "抵触": 0.3,
}


@dataclass
class ExtractedEntity:
    name: str
    type: str  # "Law" | "Organization"
    aliases: list[str] = field(default_factory=list)


@dataclass
class ExtractedRelation:
    subject: str
    predicate: str
    object: str


class Neo4jGraphStore:
    """Neo4j-backed knowledge graph store."""

    def __init__(self, uri: str, user: str, password: str):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._ensure_indexes()

    def close(self):
        self._driver.close()

    def _ensure_indexes(self):
        indexes = [
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
            "CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id)",
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX alias_text IF NOT EXISTS FOR (a:Alias) ON (a.text)",
            "CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id)",
            "CREATE INDEX chunk_source IF NOT EXISTS FOR (c:Chunk) ON (c.source)",
            "CREATE INDEX doc_source IF NOT EXISTS FOR (d:Document) ON (d.source)",
        ]
        with self._driver.session() as session:
            for stmt in indexes:
                session.run(stmt)

    # ── Ingest ─────────────────────────────────────────────────────

    def ingest(self, chunk_id: str, source: str,
               entities: list[ExtractedEntity],
               relations: list[ExtractedRelation]) -> None:
        """Write a chunk's extracted knowledge to Neo4j."""
        with self._driver.session() as session:
            # 1. Document node
            session.run(
                "MERGE (d:Document {source: $source}) "
                "ON CREATE SET d.id = $doc_id, d.chunk_count = 1 "
                "ON MATCH SET d.chunk_count = d.chunk_count + 1",
                source=source, doc_id=str(uuid.uuid4()),
            )
            # 2. Chunk node + HAS_CHUNK edge
            session.run(
                "MERGE (c:Chunk {id: $cid}) "
                "SET c.source = $source "
                "WITH c "
                "MATCH (d:Document {source: $source}) "
                "MERGE (d)-[:HAS_CHUNK]->(c)",
                cid=chunk_id, source=source,
            )
            # 3. Entities + aliases + MENTIONED_IN
            for entity in entities:
                eid = str(uuid.uuid4())
                session.run(
                    "MERGE (e:Entity {name: $name}) "
                    "ON CREATE SET e.id = $eid, e.type = $etype "
                    "WITH e "
                    "MATCH (c:Chunk {id: $cid}) "
                    "MERGE (e)-[:MENTIONED_IN]->(c)",
                    name=entity.name, eid=eid, etype=entity.type, cid=chunk_id,
                )
                for alias in [entity.name] + entity.aliases:
                    session.run(
                        "MERGE (a:Alias {text: $alias}) "
                        "WITH a "
                        "MATCH (e:Entity {name: $name}) "
                        "MERGE (a)-[:RESOLVES_TO]->(e)",
                        alias=alias, name=entity.name,
                    )
            # 4. Relations
            for rel in relations:
                weight = RELATE_WEIGHTS.get(rel.predicate, 0.5)
                session.run(
                    "MATCH (s:Entity {name: $subj}) "
                    "MATCH (o:Entity {name: $obj}) "
                    "MERGE (s)-[r:RELATES {predicate: $pred}]->(o) "
                    "SET r.weight = $weight, r.chunk_id = $cid",
                    subj=rel.subject, obj=rel.object,
                    pred=rel.predicate, weight=weight, cid=chunk_id,
                )

    # ── Delete ─────────────────────────────────────────────────────

    def delete_by_source(self, source: str) -> None:
        """Delete all graph data for one document."""
        with self._driver.session() as session:
            session.run(
                "MATCH (d:Document {source: $s}) DETACH DELETE d", s=source,
            )
            session.run(
                "MATCH (e:Entity) WHERE NOT (e)-[:MENTIONED_IN]->() DETACH DELETE e",
            )
            session.run(
                "MATCH (a:Alias) WHERE NOT (a)-[:RESOLVES_TO]->() DELETE a",
            )

    # ── Query: Two-Phase Candidate Expansion ──────────────────────

    def graph_candidates(self, seed_names: list[str],
                         max_chunks: int = 20,
                         min_weight: float = 0.3) -> list[str]:
        """Two-phase: expand entities → map to chunks. Returns chunk IDs."""
        if not seed_names:
            return []

        # Phase 1: Expand from seed entities through weighted RELATES edges
        expanded = self._expand_entities(seed_names, min_weight)

        # Phase 2: Map expanded entities to chunks
        return self._map_to_chunks(expanded, max_chunks)

    def _expand_entities(self, seed_names: list[str],
                         min_weight: float) -> dict[str, float]:
        """Phase 1: Weighted entity expansion."""
        cypher = """
        MATCH (seed:Entity)
        WHERE seed.name IN $seeds
        MATCH path = (seed)-[rels:RELATES*1..3]->(target:Entity)
        WITH seed, target, rels,
             REDUCE(w = 1.0, r IN rels | w * r.weight) AS cum_weight
        WHERE cum_weight >= $min_weight
        WITH target, MAX(cum_weight) AS best_weight
        RETURN target.name AS name, best_weight
        ORDER BY best_weight DESC
        """
        expanded = {name: 1.0 for name in seed_names}
        with self._driver.session() as session:
            result = session.run(cypher, seeds=seed_names, min_weight=min_weight)
            for record in result:
                name = record["name"]
                weight = record["best_weight"]
                if name not in expanded or weight > expanded[name]:
                    expanded[name] = weight
        return expanded

    def _map_to_chunks(self, entity_scores: dict[str, float],
                       max_chunks: int) -> list[str]:
        """Phase 2: Map entities to chunks, bridge-ranked."""
        cypher = """
        UNWIND $entities AS entity_info
        MATCH (e:Entity {name: entity_info.name})-[:MENTIONED_IN]->(c:Chunk)
        WITH c, COLLECT(DISTINCT e.name) AS entity_names, MAX(entity_info.score) AS max_score
        RETURN c.id AS chunk_id, SIZE(entity_names) AS entity_count
        ORDER BY entity_count DESC, max_score DESC
        LIMIT $limit
        """
        entities_param = [{"name": n, "score": s} for n, s in entity_scores.items()]
        with self._driver.session() as session:
            result = session.run(cypher, entities=entities_param, limit=max_chunks)
            return [record["chunk_id"] for record in result]

    # ── NetworkX / PageRank ────────────────────────────────────────

    def to_networkx(self) -> "nx.Graph":
        """导出为 NetworkX 图（用于 PageRank 和社区检测）"""
        import networkx as nx
        G = nx.Graph()
        with self._driver.session() as session:
            # 获取所有实体节点
            result = session.run(
                "MATCH (e:Entity) RETURN e.id AS id, e.name AS name, "
                "e.type AS type, e.description AS desc"
            )
            for record in result:
                G.add_node(
                    record["id"],
                    name=record["name"],
                    type=record["type"],
                    description=record["desc"],
                )
            # 获取所有关系
            result = session.run(
                "MATCH (a:Entity)-[r:RELATES]->(b:Entity) "
                "RETURN a.id AS src, b.id AS tgt, "
                "r.description AS desc, r.weight AS weight"
            )
            for record in result:
                if G.has_node(record["src"]) and G.has_node(record["tgt"]):
                    G.add_edge(
                        record["src"],
                        record["tgt"],
                        description=record["desc"],
                        weight=record.get("weight", 1),
                    )
        return G

    def compute_pagerank(self):
        """计算 PageRank 并写回 Neo4j"""
        import networkx as nx
        G = self.to_networkx()
        if len(G.nodes) == 0:
            return
        pr = nx.pagerank(G, alpha=0.85)
        with self._driver.session() as session:
            for node_id, rank in pr.items():
                session.run(
                    "MATCH (e:Entity {id: $id}) SET e.pagerank = $rank",
                    id=node_id, rank=rank,
                )
        logger.info("PageRank computed for %d nodes", len(pr))

    # ── Community ──────────────────────────────────────────────────

    def store_community(self, community_id: str, members: list[str],
                        report: str, weight: int):
        """存储社区"""
        with self._driver.session() as session:
            session.run(
                "MERGE (c:Community {id: $id}) "
                "SET c.members = $members, c.report = $report, c.weight = $weight",
                id=community_id, members=members, report=report, weight=weight,
            )
            # 关联社区成员
            for member_id in members:
                session.run(
                    "MATCH (e:Entity {id: $eid}), (c:Community {id: $cid}) "
                    "MERGE (e)-[:IN_COMMUNITY]->(c)",
                    eid=member_id, cid=community_id,
                )

    # ── N-hop Paths ────────────────────────────────────────────────

    def get_n_hop_paths(self, entity_ids: list[str],
                        max_hops: int = 2) -> list[dict]:
        """获取 N-hop 路径"""
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH path = (start)-[*1..""" + str(max_hops) + """]->(end)
                WHERE start.id IN $ids AND start <> end
                RETURN [n IN nodes(path) | n.name] AS node_names,
                       [r IN relationships(path) | r.description] AS rel_descs,
                       length(path) AS hops
                LIMIT 50
                """,
                ids=entity_ids,
            )
            paths = []
            for record in result:
                names = record["node_names"]
                descs = record["rel_descs"]
                path_text = names[0]
                for i, desc in enumerate(descs):
                    path_text += f" →({desc or 'related'})→ {names[i+1]}"
                paths.append({"path_text": path_text, "hops": record["hops"]})
            return paths

    # ── Community Reports ──────────────────────────────────────────

    def get_community_reports(self, entity_ids: list[str]) -> list[dict]:
        """获取包含指定实体的社区报告"""
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (e:Entity)-[:IN_COMMUNITY]->(c:Community)
                WHERE e.id IN $ids
                RETURN DISTINCT c.id AS id, c.report AS report, c.weight AS weight
                ORDER BY c.weight DESC LIMIT 5
                """,
                ids=entity_ids,
            )
            return [
                {"id": r["id"], "report": r["report"], "weight": r["weight"]}
                for r in result
            ]

    # ── Entity Merge ───────────────────────────────────────────────

    def merge_entity_nodes(self, keep_id: str, merge_id: str):
        """合并两个实体节点（消歧后）

        将 merge_id 的关系重定向到 keep_id，然后删除 merge 节点。
        使用纯 Cypher（无需 apoc）。
        """
        with self._driver.session() as session:
            # 获取 merge 节点的所有关系
            result = session.run(
                "MATCH (m:Entity {id: $merge_id})-[r:RELATES]-(other:Entity) "
                "RETURN other.id AS other_id, r.description AS desc, "
                "r.weight AS weight, startNode(r).id AS start_id",
                merge_id=merge_id,
            )
            records = list(result)
            for record in records:
                other_id = record["other_id"]
                if other_id == keep_id:
                    continue
                # 在 keep 节点和 other 之间创建关系
                session.run(
                    "MATCH (a:Entity {id: $a_id}), (b:Entity {id: $b_id}) "
                    "MERGE (a)-[r:RELATES]->(b) "
                    "ON CREATE SET r.description = $desc, r.weight = $weight "
                    "ON MATCH SET r.weight = r.weight + $weight",
                    a_id=keep_id, b_id=other_id,
                    desc=record["desc"], weight=record.get("weight", 1),
                )
            # 删除 merge 节点
            session.run(
                "MATCH (e:Entity {id: $id}) DETACH DELETE e", id=merge_id,
            )
