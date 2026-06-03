import pytest
from unittest.mock import Mock

def test_classifier_returns_intent_type():
    """测试分类器返回意图类型"""
    from core.query_understanding.classifier import QueryClassifier

    mock_llm = Mock()
    mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.95, "complexity": "simple"}'

    classifier = QueryClassifier(llm_client=mock_llm)
    result = classifier.classify("Python装饰器怎么用？")

    assert "intent_type" in result
    assert result["intent_type"] in ["factoid", "analytical", "procedural", "exploratory"]
    assert "confidence" in result
    assert 0 <= result["confidence"] <= 1
    assert "complexity" in result
    assert result["complexity"] in ["simple", "medium", "complex"]

def test_classifier_caches_results():
    """测试分类器缓存结果"""
    from core.query_understanding.classifier import QueryClassifier

    mock_llm = Mock()
    mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.95, "complexity": "simple"}'

    classifier = QueryClassifier(llm_client=mock_llm)

    # 第一次调用
    result1 = classifier.classify("Python装饰器怎么用？")
    # 第二次调用相同查询
    result2 = classifier.classify("Python装饰器怎么用？")

    # LLM应该只被调用一次
    assert mock_llm.generate.call_count == 1
    assert result1 == result2


def test_classifier_handles_invalid_json():
    """测试处理非法JSON响应"""
    from core.query_understanding.classifier import QueryClassifier

    mock_llm = Mock()
    mock_llm.generate.return_value = "这不是JSON"

    classifier = QueryClassifier(llm_client=mock_llm)
    result = classifier.classify("测试查询")

    assert result["intent_type"] == "factoid"
    assert result["confidence"] == 0.5
    assert result["complexity"] == "medium"


def test_classifier_handles_none_response():
    """测试处理None响应"""
    from core.query_understanding.classifier import QueryClassifier

    mock_llm = Mock()
    mock_llm.generate.return_value = None

    classifier = QueryClassifier(llm_client=mock_llm)
    result = classifier.classify("测试查询")

    assert result["intent_type"] == "factoid"
    assert result["confidence"] == 0.5
    assert result["complexity"] == "medium"


def test_classifier_cache_eviction():
    """测试缓存淘汰机制"""
    from core.query_understanding.classifier import QueryClassifier

    mock_llm = Mock()
    mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

    classifier = QueryClassifier(llm_client=mock_llm, cache_size=2)

    classifier.classify("查询1")
    classifier.classify("查询2")
    classifier.classify("查询3")  # 应该淘汰查询1

    assert len(classifier.cache) == 2
    assert "查询1" not in classifier.cache
    assert "查询2" in classifier.cache
    assert "查询3" in classifier.cache
