import pytest


def test_classifier_returns_valid_structure():
    """测试分类器返回完整的结构"""
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    result = classifier.classify("Python装饰器怎么用？")

    assert "intent_type" in result
    assert result["intent_type"] in ["factoid", "analytical", "procedural", "exploratory"]
    assert "confidence" in result
    assert 0 <= result["confidence"] <= 1
    assert "complexity" in result
    assert result["complexity"] in ["simple", "medium", "complex"]


def test_classifier_factoid():
    """测试事实型查询识别"""
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    assert classifier.classify("什么是装饰器")["intent_type"] == "factoid"
    assert classifier.classify("Python有哪些数据类型")["intent_type"] == "factoid"


def test_classifier_procedural():
    """测试步骤型查询识别"""
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    assert classifier.classify("如何实现装饰器")["intent_type"] == "procedural"
    assert classifier.classify("怎么配置Flask路由")["intent_type"] == "procedural"


def test_classifier_analytical():
    """测试分析型查询识别"""
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    assert classifier.classify("Flask和Django的区别")["intent_type"] == "analytical"
    assert classifier.classify("为什么Python有GIL")["intent_type"] == "analytical"


def test_classifier_exploratory():
    """测试探索型查询识别"""
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    assert classifier.classify("深入分析Python内存管理")["intent_type"] == "exploratory"
    assert classifier.classify("全面梳理Python异步编程")["intent_type"] == "exploratory"


def test_classifier_complexity():
    """测试复杂度分类"""
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    assert classifier.classify("装饰器")["complexity"] == "simple"
    assert classifier.classify("如何实现一个带参数的Python装饰器")["complexity"] == "medium"
    assert classifier.classify("请详细全面深入地对比React和Vue框架的优缺点，分析底层机制并给出完整的选择建议方案")["complexity"] == "complex"


def test_classifier_speed():
    """测试分类器速度（应 <1ms/次）"""
    import time
    from core.query_understanding.classifier import QueryClassifier

    classifier = QueryClassifier()
    t0 = time.time()
    for _ in range(1000):
        classifier.classify("Python装饰器怎么用？")
    elapsed_ms = (time.time() - t0) * 1000
    assert elapsed_ms < 100, f"1000 classifications took {elapsed_ms:.0f}ms, expected <100ms"
