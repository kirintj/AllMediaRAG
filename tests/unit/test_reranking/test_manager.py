import pytest
from unittest.mock import Mock, patch


def test_manager_selects_cohere_strategy():
    """测试管理器选择Cohere策略"""
    from core.reranking.manager import RerankManager

    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "cohere"
    mock_config.COHERE_API_KEY = "test-key"
    mock_config.BGE_RERANKER_PATH = "test-path"

    with patch('core.reranking.manager.CohereReranker') as MockCohere, \
         patch('core.reranking.manager.BGEReranker') as MockBGE:

        MockCohere.return_value = Mock(is_available=Mock(return_value=True))
        MockBGE.return_value = Mock(is_available=Mock(return_value=True))

        manager = RerankManager(mock_config)
        assert manager.strategy == "cohere"


def test_manager_fallback_to_bge():
    """测试管理器回退到BGE"""
    from core.reranking.manager import RerankManager

    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "cohere"
    mock_config.COHERE_API_KEY = ""  # 无API key
    mock_config.BGE_RERANKER_PATH = "test-path"

    with patch('core.reranking.manager.CohereReranker') as MockCohere, \
         patch('core.reranking.manager.BGEReranker') as MockBGE:

        MockCohere.return_value = Mock(is_available=Mock(return_value=False))
        MockBGE.return_value = Mock(is_available=Mock(return_value=True))

        manager = RerankManager(mock_config)

        documents = [{"text": "doc1"}, {"text": "doc2"}]
        manager.rerank("query", documents)

        # 应该回退到BGE
        MockBGE.return_value.rerank.assert_called_once()


def test_manager_returns_original_when_no_reranker():
    """测试无可用重排序器时返回原始排序"""
    from core.reranking.manager import RerankManager

    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "cohere"
    mock_config.COHERE_API_KEY = ""
    mock_config.BGE_RERANKER_PATH = "test-path"
    mock_config.RERANK_TOP_K = 5

    with patch('core.reranking.manager.CohereReranker') as MockCohere, \
         patch('core.reranking.manager.BGEReranker') as MockBGE:

        MockCohere.return_value = Mock(is_available=Mock(return_value=False))
        MockBGE.return_value = Mock(is_available=Mock(return_value=False))

        manager = RerankManager(mock_config)

        documents = [{"text": "doc1"}, {"text": "doc2"}]
        result = manager.rerank("query", documents, top_k=5)

        # 应该返回原始文档
        assert len(result) == 2
