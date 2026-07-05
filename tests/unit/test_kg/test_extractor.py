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
