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
