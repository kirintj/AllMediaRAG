import pytest


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


def test_validate_documents_normal():
    """测试正常文档通过验证"""
    from core.reranking.base import RerankerProvider

    class MockReranker(RerankerProvider):
        def rerank(self, query, documents, top_k=5):
            return documents[:top_k]

        def is_available(self):
            return True

    reranker = MockReranker()
    docs = [
        {"text": "doc1", "metadata": {"source": "test"}, "score": 0.9},
        {"text": "doc2", "metadata": {}, "score": 0.8}
    ]

    result = reranker._validate_documents(docs)
    assert len(result) == 2
    assert result[0]["text"] == "doc1"


def test_validate_documents_filters_non_dict():
    """测试非dict条目被过滤"""
    from core.reranking.base import RerankerProvider

    class MockReranker(RerankerProvider):
        def rerank(self, query, documents, top_k=5):
            return documents[:top_k]

        def is_available(self):
            return True

    reranker = MockReranker()
    docs = [
        {"text": "doc1"},
        "not a dict",  # 应该被过滤
        {"text": "doc2"}
    ]

    result = reranker._validate_documents(docs)
    assert len(result) == 2


def test_validate_documents_filters_missing_text():
    """测试缺少text的条目被过滤"""
    from core.reranking.base import RerankerProvider

    class MockReranker(RerankerProvider):
        def rerank(self, query, documents, top_k=5):
            return documents[:top_k]

        def is_available(self):
            return True

    reranker = MockReranker()
    docs = [
        {"text": "doc1"},
        {"metadata": {}},  # 缺少text，应该被过滤
        {"score": 0.5}     # 缺少text，应该被过滤
    ]

    result = reranker._validate_documents(docs)
    assert len(result) == 1


def test_validate_documents_adds_default_values():
    """测试缺失字段使用默认值"""
    from core.reranking.base import RerankerProvider

    class MockReranker(RerankerProvider):
        def rerank(self, query, documents, top_k=5):
            return documents[:top_k]

        def is_available(self):
            return True

    reranker = MockReranker()
    docs = [{"text": "doc1"}]  # 缺少metadata和score

    result = reranker._validate_documents(docs)
    assert result[0]["metadata"] == {}
    assert result[0]["score"] == 0.0
