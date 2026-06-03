import pytest
from unittest.mock import Mock, MagicMock

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
