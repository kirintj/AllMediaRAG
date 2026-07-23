"""ElasticsearchStore 单元测试。

使用 mock 避免依赖真实 ES 实例。
"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


# ---------------------------------------------------------------------------
# Mock ES client fixture
# ---------------------------------------------------------------------------

def _make_mock_client():
    """构建 mock Elasticsearch 客户端"""
    client = MagicMock()
    # indices.exists 默认返回 True（索引已存在）
    client.indices.exists.return_value.body = True
    client.cluster.health.return_value = {
        "status": "green",
        "cluster_name": "test-cluster",
        "number_of_nodes": 1,
    }
    return client


def _make_store(client=None):
    """构建 ElasticsearchStore 实例（绕过真实连接）"""
    from core.providers.elasticsearch_store import ElasticsearchStore

    with patch("core.providers.elasticsearch_store.Elasticsearch", return_value=client or _make_mock_client()):
        store = ElasticsearchStore(
            hosts="http://localhost:9200",
            index_prefix="test",
            tenant_id="unit",
            embedding_dim=128,
        )
    return store


# ---------------------------------------------------------------------------
# Tests: Connection info
# ---------------------------------------------------------------------------

class TestConnectionInfo:
    def test_db_type(self):
        store = _make_store()
        assert store.db_type() == "elasticsearch"

    def test_health_returns_cluster_info(self):
        store = _make_store()
        h = store.health()
        assert h["status"] == "green"
        assert h["cluster_name"] == "test-cluster"

    def test_health_handles_error(self):
        client = _make_mock_client()
        client.cluster.health.side_effect = Exception("connection refused")
        store = _make_store(client)
        h = store.health()
        assert h["status"] == "error"


# ---------------------------------------------------------------------------
# Tests: Index management
# ---------------------------------------------------------------------------

class TestIndexManagement:
    def test_index_name(self):
        store = _make_store()
        assert store._index_name == "test_unit"

    def test_index_exist(self):
        store = _make_store()
        assert store.index_exist("test_unit") is True

    def test_create_idx(self):
        client = _make_mock_client()
        store = _make_store(client)
        store.create_idx("new_idx", 256)
        client.indices.create.assert_called_once()
        call_kwargs = client.indices.create.call_args
        assert call_kwargs[1]["index"] == "new_idx"
        mapping = call_kwargs[1]["body"]
        assert mapping["mappings"]["properties"]["embedding"]["dims"] == 256

    def test_delete_idx(self):
        client = _make_mock_client()
        client.indices.exists.return_value.body = True
        store = _make_store(client)
        store.delete_idx("test_unit")
        client.indices.delete.assert_called_once_with(index="test_unit")


# ---------------------------------------------------------------------------
# Tests: Tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_tokenize_returns_string(self):
        store = _make_store()
        result = store._tokenize("你好世界")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Tests: Insert
# ---------------------------------------------------------------------------

class TestInsert:
    def test_insert_returns_empty_on_success(self):
        client = _make_mock_client()
        store = _make_store(client)
        # bulk is imported inside insert() from elasticsearch.helpers
        with patch("elasticsearch.helpers.bulk") as mock_bulk:
            mock_bulk.return_value = (2, [])
            errors = store.insert([
                {"id": "1", "text": "hello", "text_raw": "hello", "embedding": [0.1] * 128, "source": "a.txt"},
                {"id": "2", "text": "world", "text_raw": "world", "embedding": [0.2] * 128, "source": "a.txt"},
            ])
        assert errors == []

    def test_insert_empty_rows(self):
        store = _make_store()
        errors = store.insert([])
        assert errors == []


# ---------------------------------------------------------------------------
# Tests: Get
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_found(self):
        client = _make_mock_client()
        client.get.return_value = {
            "found": True,
            "_id": "doc1",
            "_source": {"text": "hello", "source": "a.txt"},
        }
        store = _make_store(client)
        doc = store.get("doc1")
        assert doc is not None
        assert doc["id"] == "doc1"
        assert doc["source"] == "a.txt"

    def test_get_not_found(self):
        client = _make_mock_client()
        client.get.return_value = {"found": False}
        store = _make_store(client)
        doc = store.get("missing")
        assert doc is None


# ---------------------------------------------------------------------------
# Tests: Delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_returns_count(self):
        client = _make_mock_client()
        client.delete_by_query.return_value = {"deleted": 3}
        store = _make_store(client)
        count = store.delete({"source": "a.txt"})
        assert count == 3


# ---------------------------------------------------------------------------
# Tests: Search
# ---------------------------------------------------------------------------

class TestSearch:
    def _mock_search_response(self, hits, total=1):
        return {
            "hits": {
                "total": {"value": total},
                "hits": hits,
            }
        }

    def test_search_returns_standard_format(self):
        client = _make_mock_client()
        client.search.return_value = self._mock_search_response([
            {
                "_id": "doc1",
                "_score": 0.95,
                "_source": {
                    "text": "tokenized text",
                    "text_raw": "original text",
                    "source": "a.txt",
                    "metadata": {"key": "val"},
                },
            }
        ], total=1)
        store = _make_store(client)
        result = store.search(
            select_fields=["id", "text_raw", "source", "metadata"],
            condition=None,
            match_expressions=[],
            limit=10,
        )
        assert result["total"] == 1
        assert len(result["documents"]) == 1
        assert result["documents"][0] == "original text"
        assert result["metadatas"][0]["source"] == "a.txt"

    def test_search_limit_zero_returns_count(self):
        client = _make_mock_client()
        client.count.return_value = {"count": 42}
        store = _make_store(client)
        result = store.search(
            select_fields=["id"],
            condition=None,
            match_expressions=[],
            limit=0,
        )
        assert result["total"] == 42
        assert result["documents"] == []


# ---------------------------------------------------------------------------
# Tests: Compatibility methods
# ---------------------------------------------------------------------------

class TestCompatMethods:
    def test_get_document_count(self):
        client = _make_mock_client()
        client.count.return_value = {"count": 10}
        store = _make_store(client)
        assert store.get_document_count() == 10

    def test_close_does_not_raise(self):
        store = _make_store()
        store.close()  # Should not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
