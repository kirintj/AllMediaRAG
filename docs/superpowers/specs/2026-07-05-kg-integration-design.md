# Knowledge Graph Integration Design

> **Date**: 2026-07-05
> **Status**: Draft v4 (Simplified)
> **Scope**: Neo4j-based knowledge graph for cross-regulation candidate expansion

## 1. Purpose

Graph is a **candidate generator**, not a retriever. It finds chunks that vector/BM25 miss by traversing entity relationships. Ranking is unified through CrossEncoder reranking (already in the existing pipeline).

Core flow:
```
Vector  → 50 chunks
BM25    → 50 chunks
Graph   → 20 chunks (candidate expansion)
          ↓
        Union + Dedup
          ↓
        CrossEncoder Rerank (existing reranker)
          ↓
        Top-K
```

## 2. Scope: What We Build and What We Skip

| Build (v1) | Skip (v1) | Why Skip |
|------------|-----------|----------|
| Neo4j as primary graph store | PG mirror / dual-write | 5K chunks, reimport in seconds |
| Entity extraction: Law + Organization only | Concept extraction | Too hard, low marginal value for v1 |
| Regex + seed alias for entity resolution | Trigram fuzzy / prefix / context verify | Regex + alias covers 90% of queries |
| Two LLM calls: entity extract → relation extract | Single mega-prompt | Split prompts are more stable |
| Graph as candidate generator → union → CrossEncoder rerank | Graph participating in RRF with weights | CrossEncoder is the right place to rank |
| Simple delete+rebuild on reimport | Incremental sync / watermarks / retry | 5K chunk reimport is ~10 seconds |
| Basic API for stats + rebuild | Gray release / traffic percent / feature flags | Overkill for this scale |
| A/B evaluation with golden set | Production monitoring / alerting | Pilot phase doesn't need it |

## 3. Architecture

```
Ingestion:
  Document
    → Chunk (existing)
    → Embedding (existing)
    → LLM Call 1: Entity Extraction (Law, Organization)
    → LLM Call 2: Relationship Extraction
    → Write to Neo4j (Entity nodes + RELATES edges, linked to Chunk nodes)
    → Build vector/BM25 index (existing, unchanged)

Query:
  User query
    → Vector search  → 50 candidate chunks
    → BM25 search    → 50 candidate chunks
    → Graph search   → 20 candidate chunks
    → Union + Dedup by chunk_id
    → CrossEncoder Rerank (existing reranker) → Top-K
    → LLM Generation (existing, unchanged)
```

**Key principle**: Graph never ranks. It only finds candidates. The existing CrossEncoder reranker handles all ranking.

## 4. Neo4j Graph Model

### 4.1 Design Principles

1. **Separate concerns**: Document structure (Document → Chunk), Knowledge (Entity → Entity), and Surface form (Alias → Entity) are independent node types with explicit edges.
2. **Decouple expansion from mapping**: Entity expansion (traverse RELATES) and Chunk mapping (traverse MENTIONED_IN) are two distinct phases in the query pipeline, not a single Cypher path.
3. **Edges carry semantics**: RELATES edges have `weight` reflecting relationship strength, enabling weighted traversal instead of uniform hop counting.

### 4.2 Node Types

```cypher
// Document: one per source file
(:Document {
    id: String,           // matches documents.id in PG
    source: String,       // filename
    chunk_count: Integer
})

// Chunk: one per text chunk, belongs to a Document
(:Chunk {
    id: String,           // matches document_chunks.id in PG
    source: String,       // filename (denormalized for fast delete)
    section: String       // heading
})

// Entity: Law or Organization (v1)
(:Entity {
    id: String,           // UUID
    name: String,         // canonical name: "中华人民共和国数据安全法"
    type: String          // "Law" | "Organization"
})

// Alias: surface forms that refer to an Entity
(:Alias {
    text: String          // "数安法", "数据安全法", "PIPL"
})
```

### 4.3 Edge Types

```cypher
// Document structure
(:Document)-[:HAS_CHUNK {index: Integer}]->(:Chunk)

// Entity surface form
(:Alias)-[:RESOLVES_TO]->(:Entity)

// Entity mention in text
(:Entity)-[:MENTIONED_IN]->(:Chunk)

// Entity relationships (the knowledge graph core)
(:Entity)-[:RELATES {
    predicate: String,    // 制定|修订|适用于|定义了|上位法|隶属于
    weight: Float,        // semantic strength, see weight table below
    chunk_id: String      // provenance: which chunk this was extracted from
}]->(:Entity)
```

### 4.4 Relationship Weight Schema

Not all relationships are equally strong for traversal. A `上位法` link is structurally important; a `适用于` link is topical. Weights control how far traversal "spreads" from a seed entity:

| Predicate | Weight | Rationale |
|-----------|--------|-----------|
| 制定 | 1.0 | Strong structural link (Org creates Law) |
| 上位法 | 0.9 | Strong hierarchical link |
| 隶属于 | 0.9 | Strong structural link |
| 实施细则 | 0.8 | Direct derivative |
| 修订 | 0.8 | Direct modification |
| 定义了 | 0.7 | Moderate: Law defines a concept area |
| 适用于 | 0.6 | Weaker: topical applicability |
| 援引 | 0.5 | Weak: citation reference |
| 废止 | 0.4 | Deprecated link, low traversal value |
| 解释 | 0.6 | Moderate |
| 细化 | 0.6 | Moderate |
| 抵触 | 0.3 | Negative relationship, traverse cautiously |

These weights are hardcoded constants in `graph_store.py`, not stored per-edge. Only the `predicate` is stored; weight is looked up at query time. This allows tuning weights without reimporting data.

### 4.5 Graph Topology Example

```
(:Document {source: "数据安全法.txt"})
  -[:HAS_CHUNK]-> (:Chunk {id: "c1", section: "第一章 总则"})
  -[:HAS_CHUNK]-> (:Chunk {id: "c2", section: "第三章 数据安全制度"})

(:Alias {text: "数安法"})  -[:RESOLVES_TO]->  (:Entity {name: "中华人民共和国数据安全法", type: "Law"})
(:Alias {text: "数据安全法"}) -[:RESOLVES_TO]-> (:Entity {name: "中华人民共和国数据安全法", type: "Law"})

(:Entity {name: "中华人民共和国数据安全法"})
  -[:MENTIONED_IN]-> (:Chunk {id: "c1"})
  -[:MENTIONED_IN]-> (:Chunk {id: "c2"})

(:Entity {name: "全国人大常委会"})
  -[:RELATES {predicate: "制定", weight: 1.0, chunk_id: "c1"}]
  ->(:Entity {name: "中华人民共和国数据安全法"})
```

### 4.6 Why This Model Is Better

| Aspect | v4 (Chunk nodes, flat Entity) | v4.1 (Document + Alias + weighted edges) |
|--------|-------------------------------|------------------------------------------|
| Entity expansion | Blind hop count | Weighted traversal: strong links spread further |
| Chunk mapping | Same as expansion (mixed) | Separate phase: expansion finds entities, mapping finds chunks |
| Alias handling | Array on Entity node | Dedicated `(:Alias)` node with `RESOLVES_TO` edge; supports multiple surface forms per entity; Cypher `MATCH (a:Alias {text: $q})-[:RESOLVES_TO]->(e)` is cleaner |
| Document delete | Delete Chunks by source | `MATCH (d:Document {source: $s}) DETACH DELETE d` cascades to chunks |
| Provenance | `chunk_id` string on RELATES | Same, but now can also traverse `(Entity)-[:MENTIONED_IN]->(Chunk)<-[:HAS_CHUNK]-(Document)` for full provenance chain |
| Future extension | Add new node types awkwardly | Natural: add `(:Concept)` node type with its own edges later |

### 4.7 Indexes

```cypher
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id);
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX alias_text IF NOT EXISTS FOR (a:Alias) ON (a.text);
CREATE INDEX chunk_id IF NOT EXISTS FOR (c:Chunk) ON (c.id);
CREATE INDEX chunk_source IF NOT EXISTS FOR (c:Chunk) ON (c.source);
CREATE INDEX doc_source IF NOT EXISTS FOR (d:Document) ON (d.source);
```

## 5. Entity Extraction (Two-Stage LLM)

### Stage 1: Entity Extraction Prompt

Only extracts Law and Organization. No Concept. Simple and stable.

```
从以下法律文本中提取所有法律法规名称和机构名称。

## 文本
{chunk_text}

## 输出（严格 JSON 数组）
[
  {"name": "中华人民共和国数据安全法", "type": "Law", "aliases": ["数据安全法", "数安法"]},
  {"name": "全国人大常委会", "type": "Organization", "aliases": []}
]

规则：
- 只提取法律法规（type: Law）和机构（type: Organization）
- 法律名称保留"中华人民共和国"前缀
- aliases 填写常见简称
- 不要提取概念、术语、行为等
```

### Stage 2: Relationship Extraction Prompt

Given entities from Stage 1, extract relationships.

```
根据以下文本和已提取的实体列表，提取实体之间的关系。

## 实体
{entities_json}

## 允许的关系类型
- 制定: Organization → Law（"全国人大常委会制定数据安全法"）
- 修订: Law → Law（新法修订旧法）
- 适用于: Law → 法律概念/领域（"数据安全法适用于数据处理活动"）
- 定义了: Law → 法律概念/术语（"个人信息保护法定义了敏感个人信息"）
- 上位法: Law → Law（上位法在前，下位法在后）
- 隶属于: Organization → Organization

## 文本
{chunk_text}

## 输出（严格 JSON 数组）
[
  {"subject": "全国人大常委会", "predicate": "制定", "object": "中华人民共和国数据安全法"},
  {"subject": "中华人民共和国数据安全法", "predicate": "定义了", "object": "重要数据"}
]

注意：
- subject 和 object 必须是上面列出的实体名称，或文本中明确出现的概念
- relation 方向严格按上述定义
```

**Why two prompts**: Single prompt trying to do entity + relation + alias + canonicalization + validation is unstable. Two focused prompts with clear inputs/outputs are cheaper (each prompt is shorter) and easier to debug.

## 6. Entity Resolution in Query

Uses `(:Alias)` nodes in Neo4j for name resolution. No in-memory map, no trigram, no prefix.

```python
def resolve_entities(query: str) -> list[str]:
    """Find canonical entity names mentioned in the query."""
    resolved = set()

    # Step 1: Regex extraction (catches full law names like "中华人民共和国数据安全法")
    for match in LAW_PATTERN.finditer(query):
        resolved.add(match.group())

    # Step 2: Alias lookup in Neo4j (catches "数安法", "个保法", etc.)
    # Check every 2-4 char substring of the query against Alias nodes
    with driver.session() as session:
        for length in range(4, min(len(query), 16)):
            for i in range(len(query) - length + 1):
                candidate = query[i:i+length]
                result = session.run(
                    "MATCH (a:Alias {text: $t})-[:RESOLVES_TO]->(e:Entity) "
                    "RETURN e.name AS name LIMIT 1",
                    t=candidate
                )
                record = result.single()
                if record:
                    resolved.add(record["name"])

    return list(resolved)
```

**Optimization**: At startup, load all aliases into a `set` for O(1) lookup, then check `if alias in query` (no Neo4j call per query). Only hit Neo4j for the initial load:

```python
# At startup
self._all_aliases = set(session.run(
    "MATCH (a:Alias) RETURN collect(a.text) AS texts"
).single()["texts"])

# At query time (no Neo4j call)
for alias in self._all_aliases:
    if alias in query:
        canonical = self._alias_to_canonical[alias]
        resolved.add(canonical)
```

This handles:
- "数安法" → "中华人民共和国数据安全法" (Alias match)
- "个人信息保护法" → "中华人民共和国个人信息保护法" (Alias match or regex)
- "合同法" → "中华人民共和国合同法" (regex match)

For edge cases ("个保" not in aliases), vector/BM25 still retrieves relevant chunks. Graph simply contributes nothing — which is fine.

## 7. Graph Retrieval: Two-Phase Candidate Expansion

Graph retrieval is split into two decoupled phases. This separation matters because each phase has different optimization strategies and failure modes.

```
Phase 1: Entity Expansion
  Seed entities → traverse RELATES edges → discover related entities
  (weighted by edge type, bounded by cumulative weight decay)

Phase 2: Chunk Mapping
  All discovered entities → traverse MENTIONED_IN → collect candidate chunks
  (deduplicated, with provenance info)
```

### 7.1 Phase 1: Entity Expansion

Starting from seed entities (resolved from query), traverse `RELATES` edges to find related entities. Unlike uniform hop counting, traversal is **weighted**: strong relationships (制定, weight=1.0) spread further than weak ones (适用于, weight=0.6).

```python
# Edge weights (same as Section 4.4, used at query time)
RELATE_WEIGHTS = {
    "制定": 1.0, "上位法": 0.9, "隶属于": 0.9,
    "实施细则": 0.8, "修订": 0.8, "定义了": 0.7,
    "适用于": 0.6, "解释": 0.6, "细化": 0.6,
    "援引": 0.5, "废止": 0.4, "抵触": 0.3,
}

def expand_entities(seed_names: list[str], min_weight: float = 0.3) -> dict[str, float]:
    """
    Phase 1: Expand from seed entities through RELATES edges.
    Returns {entity_name: relevance_score} for all discovered entities.

    Traversal is weight-bounded: cumulative weight < min_weight → stop.
    Seed entities have score 1.0. Each hop multiplies by edge weight.
    """
    cypher = """
    MATCH (seed:Entity)
    WHERE seed.name IN $seeds

    // Variable-length traversal with weight tracking
    MATCH path = (seed)-[rels:RELATES*1..3]->(target:Entity)

    // Compute cumulative weight: multiply edge weights along path
    WITH seed, target, rels,
         REDUCE(w = 1.0, r IN rels | w * toFloat(r.weight)) AS cum_weight
    WHERE cum_weight >= $min_weight

    // Keep the highest cumulative weight for each target
    WITH target, MAX(cum_weight) AS best_weight
    RETURN target.name AS name, best_weight
    ORDER BY best_weight DESC
    """

    with driver.session() as session:
        result = session.run(cypher, seeds=seed_names, min_weight=min_weight)
        # Seed entities always included with weight 1.0
        expanded = {name: 1.0 for name in seed_names}
        for record in result:
            name = record["name"]
            weight = record["best_weight"]
            if name not in expanded or weight > expanded[name]:
                expanded[name] = weight
        return expanded
```

**Why weighted expansion matters**: For query "数据安全法和个人信息保护法的异同", the seed entities are the two laws. Traversal finds:
- `全国人大常委会` (via 制定, weight 1.0) → high relevance
- `数据安全法实施条例` (via 实施细则, weight 0.8) → moderate relevance
- Some law that merely `适用于` a similar area (weight 0.6) → lower relevance

Without weights, all three would be treated equally. With weights, the expansion naturally prioritizes structurally close entities.

### 7.2 Phase 2: Chunk Mapping

Given the expanded entity set (with scores), collect all chunks that mention any of these entities.

```python
def map_to_chunks(entity_scores: dict[str, float], max_chunks: int = 20) -> list[dict]:
    """
    Phase 2: Map entities to their chunks.
    Returns chunk dicts sorted by number of distinct seed entities that connect to them.
    Chunks touching multiple seed entities rank higher (bridge chunks).
    """
    cypher = """
    UNWIND $entities AS entity_info
    MATCH (e:Entity {name: entity_info.name})-[:MENTIONED_IN]->(c:Chunk)
    WITH c, COLLECT(DISTINCT e.name) AS entity_names, MAX(entity_info.score) AS max_entity_score
    RETURN c.id AS chunk_id, c.source AS source, c.section AS section,
           entity_names, max_entity_score,
           SIZE(entity_names) AS entity_count
    ORDER BY entity_count DESC, max_entity_score DESC
    LIMIT $limit
    """

    entities_param = [{"name": n, "score": s} for n, s in entity_scores.items()]

    with driver.session() as session:
        result = session.run(cypher, entities=entities_param, limit=max_chunks)
        return [
            {
                "chunk_id": record["chunk_id"],
                "source": record["source"],
                "section": record["section"],
                "matched_entities": record["entity_names"],
                "entity_count": record["entity_count"],
            }
            for record in result
        ]
```

**Key insight**: Chunks that connect multiple seed entities (bridge chunks) rank higher. For "数据安全法 vs 个保法" queries, chunks that mention both laws are the most valuable — they're exactly where cross-regulation comparison lives.

### 7.3 Complete Graph Retrieval Pipeline

```python
def graph_candidates(query: str, max_chunks: int = 20) -> list[str]:
    """Full graph retrieval: resolve → expand → map → return chunk IDs."""
    # Resolve query entities
    seed_entities = resolve_entities(query)
    if not seed_entities:
        return []

    # Phase 1: Expand through weighted RELATES edges
    expanded = expand_entities(seed_entities, min_weight=0.3)

    # Phase 2: Map to chunks via MENTIONED_IN
    chunks = map_to_chunks(expanded, max_chunks=max_chunks)

    return [c["chunk_id"] for c in chunks]
```

### 7.4 Integration with Existing Pipeline

Graph candidates bypass RRF entirely. They're appended to the candidate pool before the existing CrossEncoder reranker:

```python
def _do_retrieve(self, search_queries, query, vector_weight, bm25_weight, retrieve_top_k):
    # Existing: parallel vector + BM25
    vec_f = executor.submit(vector_search)
    bm25_f = executor.submit(bm25_search)

    # New: graph candidate expansion (parallel)
    graph_f = None
    if self.infra.graph_store:
        graph_f = executor.submit(graph_candidates_sync, query)

    # Collect
    vec_results = vec_f.result()
    bm25_results = bm25_f.result()
    graph_chunk_ids = graph_f.result() if graph_f else []

    # Existing RRF fusion for vector + BM25 (unchanged)
    fused = self.reciprocal_rank_fusion(
        [vec_results, bm25_results],
        [vector_weight, bm25_weight],
        k=self.rrf_k
    )

    # Add graph candidates not already in pool
    existing_ids = {doc["id"] for doc in fused}
    for chunk_id in graph_chunk_ids:
        if f"vec_{chunk_id}" not in existing_ids and f"bm25_{chunk_id}" not in existing_ids:
            chunk = self._get_chunk_by_id(chunk_id)
            if chunk:
                fused.append({
                    "id": f"graph_{chunk_id}",
                    "text": chunk["text"],
                    "metadata": {**chunk["metadata"], "retrieval_source": "knowledge_graph"},
                })

    # Existing: CrossEncoder reranks the full pool (vector + BM25 + graph)
    reranked = self.infra.rerank_manager.rerank(query, fused, self.rerank_top_k)
    return reranked[:self.top_k]
```

### Why Graph as Candidate Generator, Not RRF Participant

RRF assumes each route returns independently ranked results with comparable quality. But:
- Graph results have no meaningful "score" — they're found by traversal, not similarity
- Putting a fake score into RRF distorts the fusion
- CrossEncoder is specifically designed to rank a heterogeneous candidate pool

The existing `rerank_manager.rerank(query, candidates, top_k)` already works on a list of `{"text": ..., "metadata": ...}` dicts. Graph candidates just need to be formatted the same way.

## 8. Integration with Existing Pipeline

### 8.1 Ingestion (modify `ingestion_service.py`)

After existing vector/BM25 writes:

```python
if self._graph_store and self._kg_extractor:
    for chunk in chunks:
        chunk_id = chunk["metadata"]["chunk_id"]
        source = chunk["metadata"]["source"]
        entities = self._kg_extractor.extract_entities(chunk["text"])
        relations = self._kg_extractor.extract_relations(chunk["text"], entities)
        self._graph_store.ingest(chunk_id, source, entities, relations)
```

`graph_store.ingest()` writes:
1. `MERGE (:Document {source: ...})` — idempotent document node
2. `MERGE (:Chunk {id: chunk_id})` + `MERGE (doc)-[:HAS_CHUNK]->(chunk)`
3. For each entity: `MERGE (:Entity {name: ...})` + `MERGE (:Alias {text: alias})-[:RESOLVES_TO]->(entity)` for each alias
4. `MERGE (entity)-[:MENTIONED_IN]->(chunk)`
5. For each relation: `MERGE (subject)-[:RELATES {predicate: ...}]->(object)` with weight from lookup table

### 8.2 Deletion

```python
def delete_by_source(source: str):
    """Delete all graph data for one document."""
    with driver.session() as session:
        # Delete document → cascades to chunks → cascades MENTIONED_IN edges
        session.run("MATCH (d:Document {source: $s}) DETACH DELETE s", s=source)
        # Clean orphan entities (no remaining MENTIONED_IN)
        session.run("""
            MATCH (e:Entity)
            WHERE NOT (e)-[:MENTIONED_IN]->()
            DETACH DELETE e
        """)
        # Clean orphan aliases (no RESOLVES_TO target)
        session.run("""
            MATCH (a:Alias)
            WHERE NOT (a)-[:RESOLVES_TO]->()
            DELETE a
        """)
```

### 8.3 Retrieval (modify `retrieval_pipeline.py`)

Replace the three-route RRF approach with candidate-union + rerank:

```python
def _do_retrieve(self, search_queries, query, vector_weight, bm25_weight,
                 retrieve_top_k) -> dict:
    # Existing: parallel vector + BM25
    vec_f = executor.submit(vector_search)
    bm25_f = executor.submit(bm25_search)

    # New: graph candidate expansion (parallel)
    graph_f = None
    if self.infra.graph_store:
        graph_f = executor.submit(graph_candidates_sync, query)

    # Collect candidates
    vec_results = vec_f.result()
    bm25_results = bm25_f.result()
    graph_chunk_ids = graph_f.result() if graph_f else []

    # Existing RRF fusion for vector + BM25 (unchanged)
    fused = self.reciprocal_rank_fusion(
        [vec_results, bm25_results],
        [vector_weight, bm25_weight],
        k=self.rrf_k
    )

    # New: add graph candidates that aren't already in fused results
    existing_ids = {doc["id"] for doc in fused}
    for chunk_id in graph_chunk_ids:
        if f"vec_{chunk_id}" not in existing_ids and f"bm25_{chunk_id}" not in existing_ids:
            chunk = self._get_chunk_by_id(chunk_id)
            if chunk:
                fused.append({
                    "id": f"graph_{chunk_id}",
                    "text": chunk["text"],
                    "metadata": {**chunk["metadata"], "retrieval_source": "knowledge_graph"},
                })

    # Existing: rerank the full candidate pool (now includes graph candidates)
    reranked = self.infra.rerank_manager.rerank(query, fused, self.rerank_top_k)
    return reranked[:self.top_k]
```

**Graph candidates bypass RRF entirely.** They're appended to the candidate pool before reranking. The CrossEncoder sees all candidates (vector + BM25 + graph) and ranks them by relevance. This is simpler and more correct than trying to give graph results a fake RRF score.

### 8.4 Config (.env)

```env
USE_KNOWLEDGE_GRAPH=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
GRAPH_MAX_CHUNKS=20          # Max candidate chunks from graph
KG_EXTRACTOR_MODEL=cheap     # cheap model for extraction
```

No graph weights. No traffic percent. No feature flags. `USE_KNOWLEDGE_GRAPH=false` turns it off.

## 9. docker-compose.yml

```yaml
services:
  neo4j:
    image: neo4j:5-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

## 10. Evaluation

### 10.1 Test Query Set (20 queries)

| # | Type | Query |
|---|------|-------|
| 1 | Cross-law | 数据安全法和个人信息保护法在数据出境方面的规定有什么异同？ |
| 2 | Cross-law | 民法典合同编和合同法在违约责任方面有什么变化？ |
| 3 | Multi-hop | 制定数据安全法的机构还制定了哪些法律？ |
| 4 | Multi-hop | 公司法和证券法之间有什么关联？ |
| 5 | Alias | 数安法对重要数据的定义是什么？ |
| ... | ... | ... |

### 10.2 Metrics

| Metric | Measurement | How |
|--------|------------|-----|
| Recall@10 | Correct chunk in top-10? | Manual labeling on 20 queries |
| MRR | Mean reciprocal rank | Automatic |
| Graph contribution rate | % of queries where graph added ≥1 new chunk to top-10 | Automatic |
| Extraction precision | 50 random entity extractions, correct? | Manual |
| Extraction recall | 20 known entities, all found? | Manual |

### 10.3 A/B Comparison

```python
# Baseline: existing 2-route (vector + BM25 + CrossEncoder rerank)
# Treatment: 3-candidate (vector + BM25 + graph candidates + CrossEncoder rerank)
# Compare Recall@10 and MRR on the 20-query set
```

## 11. Cost

Pilot (5 laws, ~250 chunks, 2 LLM calls per chunk):
- Entity extraction: ~500 tokens/chunk × 250 = ~125K tokens
- Relation extraction: ~400 tokens/chunk × 250 = ~100K tokens
- Total: ~225K tokens × ¥0.5/1M = **¥0.11**

## 12. What This Deliberately Skips (and When to Add)

| Skipped Feature | When to Add |
|----------------|-------------|
| Concept entities | After v1 evaluation shows Law+Org alone is insufficient. Add with human-in-the-loop review. |
| Alias fuzzy matching | When user testing shows regex+alias misses common queries. Add prefix match first. |
| Incremental Neo4j sync | When knowledge base exceeds ~50K chunks and full reimport takes >30 seconds. |
| Graph weights in RRF | When CrossEncoder alone can't distinguish graph-sourced candidates. Add only if data supports it. |
| Monitoring / alerting | When going beyond pilot to production users. |
| Gray release / feature flags | When having >10 concurrent users who'd be affected by graph quality issues. |

## 13. File Summary

### New files (4)

| File | Lines | Purpose |
|------|-------|---------|
| `backend/core/kg/__init__.py` | ~5 | Package |
| `backend/core/kg/graph_store.py` | ~150 | Neo4j CRUD + ingest + delete + two-phase graph_candidates |
| `backend/core/kg/extractor.py` | ~100 | Two-prompt extraction (entities, then relations) |
| `backend/core/kg/graph_retriever.py` | ~50 | Query → resolve entities → expand → map → chunk IDs |

### Modified files (5)

| File | Lines Changed | What |
|------|--------------|------|
| `backend/core/config.py` | ~10 | Add KG config fields |
| `backend/core/services/__init__.py` | ~15 | Add graph_store + kg_extractor to InfraBundle |
| `backend/core/services/ingestion_service.py` | ~15 | Add extraction + Neo4j write after existing writes |
| `backend/core/services/retrieval_pipeline.py` | ~20 | Add graph candidates to candidate pool before rerank |
| `docker-compose.yml` | ~10 | Add neo4j service |

### Frontend (optional, after core works)

| File | Purpose |
|------|---------|
| `frontend/src/api/kg.js` | API wrapper |
| `frontend/src/features/kg/KGManagement.vue` | Stats + entity list (simple) |

### Total

**~350 lines backend + docker-compose + optional frontend.** 3-5 working days.
