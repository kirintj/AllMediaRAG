"""End-to-end KG test: ingest -> query -> verify candidates.

Requires: Neo4j running on bolt://localhost:7687
Run: RUN_KG_INTEGRATION=1 python -m pytest tests/integration/test_kg_e2e.py -v
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
    from core.kg.graph_store import Neo4jGraphStore
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

    # Query: "全国人大常委会" should expand to both laws -> find both chunks
    candidates = graph_store.graph_candidates(["全国人大常委会"], max_chunks=10)
    assert "c1" in candidates
    assert "c2" in candidates
