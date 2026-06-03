import pytest
from unittest.mock import Mock, patch


def test_bge_reranker_rerank():
    """测试BGE重排序"""
    from core.reranking.bge_reranker import BGEReranker

    mock_model = Mock()
    mock_model.predict.return_value = [0.95, 0.85]

    with patch("sentence_transformers.CrossEncoder", return_value=mock_model):
        reranker = BGEReranker(model_path="test-model")

        documents = [
            {"text": "文档1", "metadata": {"source": "test"}, "score": 0.8},
            {"text": "文档2", "metadata": {"source": "test"}, "score": 0.7},
        ]

        result = reranker.rerank("测试查询", documents, top_k=2)

        assert len(result) == 2
        assert "rerank_score" in result[0]
        assert result[0]["rerank_score"] == 0.95
        assert result[1]["rerank_score"] == 0.85


def test_bge_reranker_is_available():
    """测试BGE可用性检查"""
    from core.reranking.bge_reranker import BGEReranker

    # 模型加载成功时应该可用
    with patch("sentence_transformers.CrossEncoder") as MockEncoder:
        MockEncoder.return_value = Mock()
        reranker = BGEReranker(model_path="test-model")
        assert reranker.is_available() is True

    # 模型加载失败时应该不可用
    with patch("sentence_transformers.CrossEncoder", side_effect=Exception("加载失败")):
        reranker = BGEReranker(model_path="invalid-model")
        assert reranker.is_available() is False


def test_bge_reranker_returns_original_on_failure():
    """测试模型调用失败时返回原始排序"""
    from core.reranking.bge_reranker import BGEReranker

    mock_model = Mock()
    mock_model.predict.side_effect = Exception("推理失败")

    with patch("sentence_transformers.CrossEncoder", return_value=mock_model):
        reranker = BGEReranker(model_path="test-model")

        documents = [
            {"text": "文档1", "metadata": {}, "score": 0.8},
            {"text": "文档2", "metadata": {}, "score": 0.7},
        ]

        result = reranker.rerank("测试查询", documents, top_k=2)

        # 失败时返回原始文档
        assert len(result) == 2
        assert result[0]["text"] == "文档1"
