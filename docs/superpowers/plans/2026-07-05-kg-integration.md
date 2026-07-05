# Knowledge Graph Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight Neo4j knowledge graph that expands retrieval candidates for cross-regulation queries, integrated as a candidate generator alongside existing vector+BM25 search.

**Architecture:** Entity/relationship extraction via two LLM calls during ingestion → Neo4j graph store with Document/Chunk/Entity/Alias nodes → Two-phase graph retrieval (weighted entity expansion → bridge-ranked chunk mapping) → candidates appended to pool before existing CrossEncoder reranker.

**Tech Stack:** Neo4j Community 5.x (sync Python driver `neo4j`), existing LLM client (SiliconFlow MiMo), existing reranking pipeline (CrossEncoder).

**Spec:** `docs/superpowers/specs/2026-07-05-kg-integration-design.md`

---

## File Structure

### New files

| File | Responsibility |
|------|---------------|
| `backend/core/kg/__init__.py` | Package init |
| `backend/core/kg/graph_store.py` | Neo4j connection, CRUD, ingest, delete, graph_candidates (expand + map) |
| `backend/core/kg/extractor.py` | Two-prompt LLM extraction: entities → relations |
| `backend/core/kg/graph_retriever.py` | Query entity resolution + orchestrates graph_candidates |
| `tests/unit/test_kg/__init__.py` | Test package |
| `tests/unit/test_kg/test_graph_store.py` | GraphStore unit tests |
| `tests/unit/test_kg/test_extractor.py` | Extractor unit tests |
| `tests/unit/test_kg/test_graph_retriever.py` | GraphRetriever unit tests |

### Modified files

| File | What changes |
|------|-------------|
| `backend/core/config.py:144` | Add KG config fields after Observability section |
| `backend/core/services/__init__.py:79` | Add `graph_store` and `kg_extractor` fields to InfraBundle |
| `backend/core/services/__init__.py` (create_infra) | Init graph_store + kg_extractor when `USE_KNOWLEDGE_GRAPH=true` |
| `backend/core/services/ingestion_service.py:71` | After BM25 write, call KG extraction + ingest |
| `backend/core/services/ingestion_service.py:92` | In delete_by_source, call graph_store.delete_by_source |
| `backend/core/services/retrieval_pipeline.py:247` | Add graph_candidates parallel future alongside vec/bm25 |
| `docker-compose.yml` | Add neo4j service |

---

### Task 1: Neo4j Docker + Config + Dependencies

**Files:**
- Modify: `docker-compose.yml`
- Modify: `backend/core/config.py:144`
- Modify: `requirements.txt` or `pyproject.toml`

- [ ] **Step 1: Add neo4j service to docker-compose.yml**

Read the existing `docker-compose.yml`, then append:

```yaml
  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-neo4jtest}
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
```

Add `neo4j_data:` to the top-level `volumes:` section.

- [ ] **Step 2: Add KG config fields to AppSettings**

Read `backend/core/config.py`. After line 144 (`LOG_LEVEL: str = "INFO"`), add:

```python
    # -- Knowledge Graph ----------------------------------------------
    USE_KNOWLEDGE_GRAPH: bool = False
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4jtest"
    GRAPH_MAX_CHUNKS: int = 20
    KG_EXTRACTOR_MODEL: str = "cheap"
```

- [ ] **Step 3: Add neo4j Python driver dependency**

Run: `pip install neo4j`

Verify: `python -c "from neo4j import GraphDatabase; print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml backend/core/config.py
git commit -m "feat(kg): add Neo4j docker service and KG config fields"
```

---

### Task 2: GraphStore — Neo4j CRUD and Ingest

**Files:**
- Create: `backend/core/kg/__init__.py`
- Create: `backend/core/kg/graph_store.py`
- Create: `tests/unit/test_kg/__init__.py`
- Create: `tests/unit/test_kg/test_graph_store.py`

- [ ] **Step 1: Write test for GraphStore ingest and query**

Create `tests/unit/test_kg/__init__.py` (empty).

Create `tests/unit/test_kg/test_graph_store.py`:

```python
"""Tests for Neo4jGraphStore — mock the Neo4j driver, test Cypher logic."""

import pytest
from unittest.mock import MagicMock, patch, call


class TestGraphStoreIngest:
    """Test ingest() writes correct Cypher statements."""

    def test_ingest_creates_document_and_chunk_nodes(self):
        from core.kg.graph_store import Neo4jGraphStore, ExtractedEntity, ExtractedRelation

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        store = Neo4jGraphStore.__new__(Neo4jGraphStore)
        store._driver = mock_driver

        entities = [
            ExtractedEntity(name="全国人大常委会", type="Organization", aliases=["常委会"]),
            ExtractedEntity(name="中华人民共和国数据安全法", type="Law", aliases=["数据安全法"]),
        ]
        relations = [
            ExtractedRelation(subject="全国人大常委会", predicate="制定", object="中华人民共和国数据安全法"),
        ]

        store.ingest("chunk-001", "数据安全法.txt", entities, relations)

        # Should have called session.run multiple times
        assert mock_session.run.call_count >= 5  # doc, chunk, 2 entities, 2 alias sets, 2 mentions, 1 relation

    def test_ingest_empty_entities_does_nothing(self):
        from core.kg.graph_store import Neo4jGraphStore

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        store = Neo4jGraphStore.__new__(Neo4jGraphStore)
        store._driver = mock_driver

        store.ingest("chunk-001", "test.txt", [], [])

        # Only doc + chunk MERGE calls, no entity/relation calls
        assert mock_session.run.call_count == 2


class TestGraphStoreDelete:
    """Test delete_by_source cleans up correctly."""

    def test_delete_by_source_runs_cypher(self):
        from core.kg.graph_store import Neo4jGraphStore

        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        store = Neo4jGraphStore.__new__(Neo4jGraphStore)
        store._driver = mock_driver

        store.delete_by_source("数据安全法.txt")

        # Should run 3 Cypher statements: delete doc, clean orphans, clean aliases
        assert mock_session.run.call_count == 3


class TestGraphStoreQueryCandidates:
    """Test graph_candidates returns chunk IDs from two-phase expansion."""

    def test_graph_candidates_returns_empty_for_no_entities(self):
        from core.kg.graph_store import Neo4jGraphStore

        mock_driver = MagicMock()
        store = Neo4jGraphStore.__new__(Neo4jGraphStore)
        store._driver = mock_driver

        result = store.graph_candidates([], max_chunks=20)
        assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_kg/test_graph_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.kg'`

- [ ] **Step 3: Implement GraphStore**

Create `backend/core/kg/__init__.py`:

```python
```

Create `backend/core/kg/graph_store.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_kg/test_graph_store.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/kg/ tests/unit/test_kg/
git commit -m "feat(kg): add Neo4jGraphStore with ingest, delete, and two-phase graph_candidates"
```

---

### Task 3: Entity Extractor (Two-Prompt LLM)

**Files:**
- Create: `backend/core/kg/extractor.py`
- Create: `tests/unit/test_kg/test_extractor.py`

- [ ] **Step 1: Write tests for entity extractor**

Create `tests/unit/test_kg/test_extractor.py`:

```python
"""Tests for KGExtractor — mock LLM, test prompt construction and output parsing."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestExtractEntities:
    """Test entity extraction from LLM output."""

    @pytest.mark.asyncio
    async def test_extract_entities_parses_valid_json(self):
        from core.kg.extractor import KGExtractor

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps([
            {"name": "中华人民共和国数据安全法", "type": "Law", "aliases": ["数据安全法", "数安法"]},
            {"name": "全国人大常委会", "type": "Organization", "aliases": ["常委会"]},
        ]))

        extractor = KGExtractor(mock_llm)
        entities = await extractor.extract_entities("some text about 数据安全法")

        assert len(entities) == 2
        assert entities[0].name == "中华人民共和国数据安全法"
        assert entities[0].type == "Law"
        assert "数安法" in entities[0].aliases

    @pytest.mark.asyncio
    async def test_extract_entities_filters_invalid_types(self):
        from core.kg.extractor import KGExtractor

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps([
            {"name": "数据安全法", "type": "Law", "aliases": []},
            {"name": "数据出境", "type": "Concept", "aliases": []},  # should be filtered
        ]))

        extractor = KGExtractor(mock_llm)
        entities = await extractor.extract_entities("text")

        assert len(entities) == 1
        assert entities[0].type == "Law"

    @pytest.mark.asyncio
    async def test_extract_entities_handles_malformed_json(self):
        from core.kg.extractor import KGExtractor

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value="not valid json {{{")

        extractor = KGExtractor(mock_llm)
        entities = await extractor.extract_entities("text")

        assert entities == []


class TestExtractRelations:
    """Test relation extraction from LLM output."""

    @pytest.mark.asyncio
    async def test_extract_relations_parses_valid_json(self):
        from core.kg.extractor import KGExtractor, ExtractedEntity

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps([
            {"subject": "全国人大常委会", "predicate": "制定", "object": "中华人民共和国数据安全法"},
        ]))

        extractor = KGExtractor(mock_llm)
        entities = [
            ExtractedEntity(name="全国人大常委会", type="Organization", aliases=[]),
            ExtractedEntity(name="中华人民共和国数据安全法", type="Law", aliases=[]),
        ]
        relations = await extractor.extract_relations("text", entities)

        assert len(relations) == 1
        assert relations[0].predicate == "制定"

    @pytest.mark.asyncio
    async def test_extract_relations_filters_invalid_predicates(self):
        from core.kg.extractor import KGExtractor, ExtractedEntity

        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(return_value=json.dumps([
            {"subject": "A", "predicate": "制定", "object": "B"},
            {"subject": "C", "predicate": "自定义关系", "object": "D"},  # invalid
        ]))

        extractor = KGExtractor(mock_llm)
        relations = await extractor.extract_relations("text", [])

        assert len(relations) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_kg/test_extractor.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement KGExtractor**

Create `backend/core/kg/extractor.py`:

```python
"""Two-prompt LLM entity and relationship extraction for knowledge graph."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

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

    async def extract_relations(self, chunk_text: str,
                                entities: list[ExtractedEntity]) -> list[ExtractedRelation]:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_kg/test_extractor.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/kg/extractor.py tests/unit/test_kg/test_extractor.py
git commit -m "feat(kg): add two-prompt entity and relation extractor"
```

---

### Task 4: GraphRetriever — Query Entity Resolution + Orchestration

**Files:**
- Create: `backend/core/kg/graph_retriever.py`
- Create: `tests/unit/test_kg/test_graph_retriever.py`

- [ ] **Step 1: Write tests for GraphRetriever**

Create `tests/unit/test_kg/test_graph_retriever.py`:

```python
"""Tests for GraphRetriever — mock GraphStore, test entity resolution + candidate retrieval."""

import re
import pytest
from unittest.mock import MagicMock


# Reuse the same regex from the implementation
LAW_PATTERN = re.compile(
    r'(?:中华人民共和国)?[一-鿿]{2,20}(?:法|条例|规定|办法|决定|'
    r'意见|通知|细则|准则|通则|方案|标准)(?:（[^）]+）)?'
)


class TestResolveEntities:
    """Test entity resolution from query text."""

    def test_resolves_law_names_by_regex(self):
        from core.kg.graph_retriever import GraphRetriever

        mock_store = MagicMock()
        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._graph_store = mock_store
        retriever._alias_map = {}
        retriever._all_aliases = set()

        resolved = retriever.resolve_entities("数据安全法对个人信息保护法有什么影响？")
        # Regex should match "数据安全法" and "个人信息保护法"
        assert "中华人民共和国数据安全法" not in resolved  # regex won't add prefix
        # But the raw match should be there
        assert any("数据安全法" in r for r in resolved)

    def test_resolves_aliases(self):
        from core.kg.graph_retriever import GraphRetriever

        mock_store = MagicMock()
        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._graph_store = mock_store
        retriever._alias_map = {"数安法": "中华人民共和国数据安全法"}
        retriever._all_aliases = {"数安法"}

        resolved = retriever.resolve_entities("数安法对重要数据的定义")
        assert "中华人民共和国数据安全法" in resolved

    def test_returns_empty_for_no_entities(self):
        from core.kg.graph_retriever import GraphRetriever

        mock_store = MagicMock()
        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._graph_store = mock_store
        retriever._alias_map = {}
        retriever._all_aliases = set()

        resolved = retriever.resolve_entities("你好")
        assert resolved == []


class TestGraphCandidates:
    """Test the full candidate pipeline."""

    def test_returns_empty_for_no_resolved_entities(self):
        from core.kg.graph_retriever import GraphRetriever

        mock_store = MagicMock()
        mock_store.graph_candidates.return_value = []
        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._graph_store = mock_store
        retriever._alias_map = {}
        retriever._all_aliases = set()

        result = retriever.search("你好，今天天气怎么样？")
        assert result == []

    def test_search_calls_graph_candidates(self):
        from core.kg.graph_retriever import GraphRetriever

        mock_store = MagicMock()
        mock_store.graph_candidates.return_value = ["chunk-1", "chunk-2"]
        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._graph_store = mock_store
        retriever._alias_map = {"数安法": "中华人民共和国数据安全法"}
        retriever._all_aliases = {"数安法"}

        result = retriever.search("数安法的重要数据定义", max_chunks=10)
        assert result == ["chunk-1", "chunk-2"]
        mock_store.graph_candidates.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_kg/test_graph_retriever.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement GraphRetriever**

Create `backend/core/kg/graph_retriever.py`:

```python
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

    def __init__(self, graph_store: Any):
        self._graph_store = graph_store
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
            # Check if this matches a known canonical name
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit/test_kg/test_graph_retriever.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/kg/graph_retriever.py tests/unit/test_kg/test_graph_retriever.py
git commit -m "feat(kg): add GraphRetriever with entity resolution and candidate search"
```

---

### Task 5: InfraBundle Wiring + Ingestion Integration

**Files:**
- Modify: `backend/core/services/__init__.py:58-79` (InfraBundle dataclass)
- Modify: `backend/core/services/__init__.py` (create_infra function)
- Modify: `backend/core/services/ingestion_service.py:71` (after BM25 write)
- Modify: `backend/core/services/ingestion_service.py:92` (in delete_by_source)

- [ ] **Step 1: Add KG fields to InfraBundle**

Read `backend/core/services/__init__.py`. In the `InfraBundle` dataclass (after line 79 `bm25_ready: bool = False`), add:

```python
    graph_store: Any = None
    graph_retriever: Any = None
    kg_extractor: Any = None
```

- [ ] **Step 2: Add KG initialization to create_infra**

Read `backend/core/services/__init__.py` to find the `create_infra` function. At the end, before the `return InfraBundle(...)` call, add:

```python
    # ── Knowledge Graph ─────────────────────────────────────
    graph_store = None
    graph_retriever = None
    kg_extractor = None

    if config.USE_KNOWLEDGE_GRAPH:
        graph_store = _try_init(
            "Neo4j graph store",
            lambda: Neo4jGraphStore(config.NEO4J_URI, config.NEO4J_USER, config.NEO4J_PASSWORD),
        )
        if graph_store:
            from core.kg.extractor import KGExtractor
            from core.kg.graph_retriever import GraphRetriever
            kg_extractor = KGExtractor(llm_client)
            graph_retriever = GraphRetriever(graph_store)
            graph_retriever.load_aliases()
```

Add the import at the top of the file:
```python
from core.kg.graph_store import Neo4jGraphStore
```

Add the three new fields to the `return InfraBundle(...)` call:
```python
    graph_store=graph_store,
    graph_retriever=graph_retriever,
    kg_extractor=kg_extractor,
```

- [ ] **Step 3: Add KG extraction to ingestion_service.ingest_document**

Read `backend/core/services/ingestion_service.py`. After line 71 (`self._bm25_retriever.add_documents(bm25_docs)`), add:

```python
        # KG extraction + ingest (after vector/BM25 writes)
        graph_store = getattr(self._infra, "graph_store", None)
        kg_extractor = getattr(self._infra, "kg_extractor", None)
        if graph_store and kg_extractor:
            import asyncio
            for chunk, meta in zip(chunks, metadatas):
                try:
                    chunk_id = meta.get("chunk_id", str(uuid.uuid4()))
                    meta["chunk_id"] = chunk_id
                    entities = asyncio.run(kg_extractor.extract_entities(chunk["text"]))
                    relations = asyncio.run(kg_extractor.extract_relations(chunk["text"], entities))
                    graph_store.ingest(chunk_id, source, entities, relations)
                except Exception as e:
                    logger.warning("KG extraction failed for chunk in %s: %s", source, e)
```

- [ ] **Step 4: Add graph cleanup to delete_by_source**

Read `backend/core/services/ingestion_service.py`. In `delete_by_source`, after line 92 (`self._cache_manager.invalidate_by_source(source)`), add:

```python
        # 4. 清理图谱数据
        graph_store = getattr(self._infra, "graph_store", None)
        if graph_store:
            try:
                graph_store.delete_by_source(source)
            except Exception as e:
                logger.warning("Graph cleanup failed for %s: %s", source, e)
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/services/__init__.py backend/core/services/ingestion_service.py
git commit -m "feat(kg): wire KG into InfraBundle, ingestion, and deletion"
```

---

### Task 6: Retrieval Pipeline Integration

**Files:**
- Modify: `backend/core/services/retrieval_pipeline.py:247-262` (in _do_retrieve)

- [ ] **Step 1: Add graph candidates to _do_retrieve**

Read `backend/core/services/retrieval_pipeline.py`. In `_do_retrieve`, after line 248 (`bm25_f = executor.submit(bm25_search)`), add:

```python
        # Graph candidate expansion (parallel with vector/BM25)
        graph_retriever = getattr(self.infra, "graph_retriever", None)
        graph_f = None
        if graph_retriever:
            def graph_search():
                try:
                    return graph_retriever.search(query, max_chunks=self.top_k * 4)
                except Exception as e:
                    logger.warning("Graph retrieval failed: %s", e)
                    return []
            graph_f = executor.submit(graph_search)
```

Then after line 250 (`all_bm25_results = bm25_f.result()`), add:

```python
        graph_chunk_ids = graph_f.result() if graph_f else []
```

Then after the RRF fusion block (after line 262 `k=self.rrf_k`), add the graph candidate injection:

```python
        # Inject graph candidates (bypass RRF, go straight to candidate pool)
        if graph_chunk_ids:
            existing_ids = {doc["id"] for doc in fused}
            for cid in graph_chunk_ids:
                vec_id = f"vec_{hashlib.sha256(cid.encode('utf-8')).hexdigest()[:16]}"
                if vec_id not in existing_ids and cid not in existing_ids:
                    # Look up chunk text from the infra's DB or vector store
                    try:
                        # Try to get chunk text from the vector store's metadata
                        chunk_docs = self.infra.vector_store.get_all_documents()
                        for d in chunk_docs:
                            if d.get("metadata", {}).get("chunk_id") == cid:
                                fused.append({
                                    "id": f"graph_{cid}",
                                    "text": d["text"],
                                    "metadata": {**d["metadata"], "retrieval_source": "knowledge_graph"},
                                })
                                break
                    except Exception:
                        pass  # Skip if chunk not found
```

- [ ] **Step 2: Update debug log to include graph count**

Update the existing logger.debug on line 253 to include graph results:

```python
        logger.debug("Retrieval: %.0fms (queries=%d, vec=%d, bm25=%d, graph=%d)",
                      (t_search - t0) * 1000, len(search_queries),
                      len(all_vector_results), len(all_bm25_results),
                      len(graph_chunk_ids))
```

- [ ] **Step 3: Commit**

```bash
git add backend/core/services/retrieval_pipeline.py
git commit -m "feat(kg): integrate graph candidates into retrieval pipeline"
```

---

### Task 7: End-to-End Smoke Test

**Files:**
- Create: `tests/integration/test_kg_e2e.py`

- [ ] **Step 1: Write integration test (requires running Neo4j)**

Create `tests/integration/test_kg_e2e.py`:

```python
"""End-to-end KG test: ingest → query → verify candidates.

Requires: Neo4j running on bolt://localhost:7687
Run: NEO4J_URI=bolt://localhost:7687 python -m pytest tests/integration/test_kg_e2e.py -v
"""

import os
import pytest

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_KG_INTEGRATION"),
    reason="Set RUN_KG_INTEGRATION=1 to run Neo4j integration tests",
)


@pytest.fixture
def graph_store():
    from core.kg.graph_store import Neo4jGraphStore, ExtractedEntity, ExtractedRelation
    store = Neo4jGraphStore(NEO4J_URI, "neo4j", os.getenv("NEO4J_PASSWORD", "neo4jtest"))
    # Clean up before test
    with store._driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    yield store
    # Clean up after test
    with store._driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    store.close()


def test_ingest_and_query_candidates(graph_store):
    from core.kg.graph_store import ExtractedEntity, ExtractedRelation

    # Ingest two chunks from different documents mentioning related entities
    graph_store.ingest(
        "c1", "数据安全法.txt",
        entities=[
            ExtractedEntity(name="全国人大常委会", type="Organization", aliases=["常委会"]),
            ExtractedEntity(name="中华人民共和国数据安全法", type="Law", aliases=["数据安全法", "数安法"]),
        ],
        relations=[
            ExtractedRelation(subject="全国人大常委会", predicate="制定", object="中华人民共和国数据安全法"),
        ],
    )
    graph_store.ingest(
        "c2", "个人信息保护法.txt",
        entities=[
            ExtractedEntity(name="全国人大常委会", type="Organization", aliases=[]),
            ExtractedEntity(name="中华人民共和国个人信息保护法", type="Law", aliases=["个保法"]),
        ],
        relations=[
            ExtractedRelation(subject="全国人大常委会", predicate="制定", object="中华人民共和国个人信息保护法"),
        ],
    )

    # Query: "全国人大常委会" should expand to both laws → find both chunks
    candidates = graph_store.graph_candidates(["全国人大常委会"], max_chunks=10)
    assert "c1" in candidates
    assert "c2" in candidates

    # Query: "数安法" → resolve to 数据安全法 → find c1
    # (This tests entity resolution, done in GraphRetriever)
```

- [ ] **Step 2: Run integration test (if Neo4j is available)**

Run: `RUN_KG_INTEGRATION=1 python -m pytest tests/integration/test_kg_e2e.py -v`
Expected: PASS (or SKIP if Neo4j not running)

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_kg_e2e.py
git commit -m "test(kg): add end-to-end integration test for graph ingest and query"
```

---

### Task 8: Evaluation — Golden Test Set + A/B Comparison

**Files:**
- Create: `tests/fixtures/kg_golden_set.json`
- Create: `tests/integration/test_kg_eval.py`

- [ ] **Step 1: Create golden test set**

Create `tests/fixtures/kg_golden_set.json`:

```json
[
  {
    "id": 1,
    "type": "cross_law",
    "query": "数据安全法和个人信息保护法在数据出境方面的规定有什么异同？",
    "expected_entities": ["中华人民共和国数据安全法", "中华人民共和国个人信息保护法"],
    "expected_graph_contribution": true,
    "relevant_sources": ["中华人民共和国数据安全法.txt", "中华人民共和国个人信息保护法.txt"]
  },
  {
    "id": 2,
    "type": "multi_hop",
    "query": "制定数据安全法的机构还制定了哪些法律？",
    "expected_entities": ["全国人大常委会"],
    "expected_graph_contribution": true,
    "relevant_sources": ["中华人民共和国数据安全法.txt"]
  },
  {
    "id": 3,
    "type": "alias",
    "query": "数安法对重要数据的定义是什么？",
    "expected_entities": ["中华人民共和国数据安全法"],
    "expected_graph_contribution": true,
    "relevant_sources": ["中华人民共和国数据安全法.txt"]
  },
  {
    "id": 4,
    "type": "negative",
    "query": "你好",
    "expected_entities": [],
    "expected_graph_contribution": false,
    "relevant_sources": []
  },
  {
    "id": 5,
    "type": "negative",
    "query": "今天天气怎么样？",
    "expected_entities": [],
    "expected_graph_contribution": false,
    "relevant_sources": []
  }
]
```

- [ ] **Step 2: Write evaluation test**

Create `tests/integration/test_kg_eval.py`:

```python
"""KG evaluation: measure graph contribution rate and entity resolution accuracy.

Run: python -m pytest tests/integration/test_kg_eval.py -v
"""

import json
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load_golden_set():
    with open(FIXTURES / "kg_golden_set.json") as f:
        return json.load(f)


class TestEntityResolution:
    """Test entity resolution accuracy against golden set."""

    def test_resolve_cross_law_query(self):
        from core.kg.graph_retriever import GraphRetriever

        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._alias_map = {
            "数据安全法": "中华人民共和国数据安全法",
            "个保法": "中华人民共和国个人信息保护法",
        }
        retriever._all_aliases = {"数据安全法", "个保法"}

        golden = load_golden_set()
        for case in golden:
            resolved = retriever.resolve_entities(case["query"])
            for expected_entity in case["expected_entities"]:
                # Check that expected entity (or its short form) appears in resolved
                found = any(
                    expected_entity in r or r in expected_entity
                    for r in resolved
                )
                if case["expected_graph_contribution"]:
                    assert found or not case["expected_entities"], \
                        f"Case {case['id']}: expected entity '{expected_entity}' not found in {resolved}"
```

- [ ] **Step 3: Run evaluation**

Run: `python -m pytest tests/integration/test_kg_eval.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/kg_golden_set.json tests/integration/test_kg_eval.py
git commit -m "test(kg): add golden test set and entity resolution evaluation"
```
