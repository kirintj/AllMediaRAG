import pytest
from abc import ABC

def test_reranker_provider_is_abstract():
    """测试RerankerProvider是抽象类"""
    from core.reranking.base import RerankerProvider

    with pytest.raises(TypeError):
        reranker = RerankerProvider()

def test_reranker_provider_has_required_methods():
    """测试RerankerProvider必须实现的方法"""
    from core.reranking.base import RerankerProvider

    # 检查抽象方法存在
    assert hasattr(RerankerProvider, 'rerank')
    assert hasattr(RerankerProvider, 'is_available')

def test_concrete_reranker_can_be_instantiated():
    """测试具体实现可以实例化"""
    from core.reranking.base import RerankerProvider

    class MockReranker(RerankerProvider):
        def rerank(self, query, documents, top_k=5):
            return documents[:top_k]

        def is_available(self):
            return True

    reranker = MockReranker()
    assert reranker.is_available() is True

    docs = [{"text": "doc1"}, {"text": "doc2"}]
    result = reranker.rerank("query", docs, top_k=1)
    assert len(result) == 1
