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


def test_manager_hybrid_strategy():
    """测试混合策略"""
    from core.reranking.manager import RerankManager

    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "hybrid"
    mock_config.COHERE_API_KEY = "test-key"
    mock_config.BGE_RERANKER_PATH = "test-path"
    mock_config.RERANK_TOP_K = 5

    with patch('core.reranking.manager.CohereReranker') as MockCohere, \
         patch('core.reranking.manager.BGEReranker') as MockBGE:

        MockCohere.return_value = Mock(is_available=Mock(return_value=True))
        MockBGE.return_value = Mock(is_available=Mock(return_value=True))

        manager = RerankManager(mock_config)
        assert manager.strategy == "hybrid"


def test_manager_bge_strategy():
    """测试BGE策略"""
    from core.reranking.manager import RerankManager

    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "bge"
    mock_config.COHERE_API_KEY = "test-key"
    mock_config.BGE_RERANKER_PATH = "test-path"
    mock_config.RERANK_TOP_K = 5

    with patch('core.reranking.manager.CohereReranker') as MockCohere, \
         patch('core.reranking.manager.BGEReranker') as MockBGE:

        mock_bge = Mock()
        mock_bge.is_available.return_value = True
        mock_bge.rerank.return_value = [
            {"text": "doc1", "rerank_score": 0.9},
            {"text": "doc2", "rerank_score": 0.8},
        ]
        MockCohere.return_value = Mock(is_available=Mock(return_value=True))
        MockBGE.return_value = mock_bge

        manager = RerankManager(mock_config)

        documents = [{"text": "doc1"}, {"text": "doc2"}]
        manager.rerank("query", documents)

        # 应该使用BGE
        mock_bge.rerank.assert_called_once()


def test_manager_empty_documents():
    """测试空文档列表"""
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
        result = manager.rerank("query", [])

        assert result == []


def test_manager_top_k_limit():
    """测试top_k限制"""
    from core.reranking.manager import RerankManager

    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "cohere"
    mock_config.COHERE_API_KEY = "test-key"
    mock_config.BGE_RERANKER_PATH = "test-path"
    mock_config.RERANK_TOP_K = 2

    with patch('core.reranking.manager.CohereReranker') as MockCohere, \
         patch('core.reranking.manager.BGEReranker') as MockBGE:

        all_docs = [
            {"text": "doc1", "rerank_score": 0.9},
            {"text": "doc2", "rerank_score": 0.8},
            {"text": "doc3", "rerank_score": 0.7},
        ]

        def fake_rerank(query, documents, top_k):
            return all_docs[:top_k]

        mock_reranker = Mock()
        mock_reranker.is_available.return_value = True
        mock_reranker.rerank.side_effect = fake_rerank
        MockCohere.return_value = mock_reranker
        MockBGE.return_value = Mock(is_available=Mock(return_value=False))

        manager = RerankManager(mock_config)
        documents = [{"text": "doc1"}, {"text": "doc2"}, {"text": "doc3"}]
        result = manager.rerank("query", documents, top_k=2)

        assert len(result) == 2
