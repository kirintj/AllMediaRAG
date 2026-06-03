import pytest
from unittest.mock import Mock, patch


def test_cohere_reranker_rerank():
    """测试Cohere重排序"""
    from core.reranking.cohere_reranker import CohereReranker

    mock_cohere = Mock()
    mock_result = Mock()
    mock_result.index = 0
    mock_result.relevance_score = 0.95
    mock_cohere.rerank.return_value = Mock(results=[mock_result])

    with patch("cohere.Client", return_value=mock_cohere):
        reranker = CohereReranker(api_key="test-key")

        documents = [
            {"text": "文档1", "metadata": {"source": "test"}, "score": 0.8},
            {"text": "文档2", "metadata": {"source": "test"}, "score": 0.7},
        ]

        result = reranker.rerank("测试查询", documents, top_k=2)

        assert len(result) > 0
        assert "rerank_score" in result[0]


def test_cohere_reranker_is_available():
    """测试Cohere可用性检查"""
    from core.reranking.cohere_reranker import CohereReranker

    # 有API key时应该可用
    with patch("cohere.Client"):
        reranker = CohereReranker(api_key="test-key")
        assert reranker.is_available() is True

    # 无API key时应该不可用
    reranker = CohereReranker(api_key="")
    assert reranker.is_available() is False


def test_cohere_reranker_returns_original_on_failure():
    """测试API调用失败时返回原始排序"""
    from core.reranking.cohere_reranker import CohereReranker

    mock_cohere = Mock()
    mock_cohere.rerank.side_effect = Exception("API调用失败")

    with patch("cohere.Client", return_value=mock_cohere):
        reranker = CohereReranker(api_key="test-key")

        documents = [
            {"text": "文档1", "metadata": {}, "score": 0.8},
            {"text": "文档2", "metadata": {}, "score": 0.7},
        ]

        result = reranker.rerank("测试查询", documents, top_k=2)

        # 失败时返回原始文档
        assert len(result) == 2
