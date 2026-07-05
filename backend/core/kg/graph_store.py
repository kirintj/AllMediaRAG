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
