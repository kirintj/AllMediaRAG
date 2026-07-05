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
        assert any("数据安全法" in r for r in resolved)
        assert any("个人信息保护法" in r for r in resolved)

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
