"""QueryClassifier 测试（纯规则分类器版本）"""
import pytest

from core.query_understanding.classifier import QueryClassifier


class TestQueryClassifier:
    """QueryClassifier 测试套件"""

    def test_classify_factoid_query(self):
        """测试事实型查询分类"""
        classifier = QueryClassifier()
        result = classifier.classify("什么是 RAG？")

        assert result["intent_type"] == "factoid"
        assert result["confidence"] >= 0.6
        assert result["complexity"] in ("simple", "medium", "complex")

    def test_classify_analytical_query(self):
        """测试分析型查询分类"""
        classifier = QueryClassifier()
        result = classifier.classify("比较Python和Java的优缺点")

        assert result["intent_type"] == "analytical"
        assert result["confidence"] >= 0.6
        assert result["complexity"] in ("simple", "medium", "complex")

    def test_classify_procedural_query(self):
        """测试步骤型查询分类"""
        classifier = QueryClassifier()
        result = classifier.classify("如何配置 PostgreSQL?")

        assert result["intent_type"] == "procedural"

    def test_classify_exploratory_query(self):
        """测试探索型查询分类"""
        classifier = QueryClassifier()
        result = classifier.classify("全面介绍 RAG 系统的各个组件")

        assert result["intent_type"] == "exploratory"

    def test_classify_short_factoid(self):
        """测试短查询默认为事实型"""
        classifier = QueryClassifier()
        result = classifier.classify("RAG")

        assert result["intent_type"] == "factoid"
        assert result["confidence"] == 0.7

    def test_classify_question_mark(self):
        """测试带问号的查询默认为事实型"""
        classifier = QueryClassifier()
        result = classifier.classify("这个系统支持哪些文件格式？")

        assert result["intent_type"] == "factoid"
        assert result["confidence"] == 0.65

    def test_classify_complexity_simple(self):
        """测试简单复杂度"""
        classifier = QueryClassifier()
        result = classifier.classify("什么是 RAG")

        assert result["complexity"] == "simple"

    def test_classify_complexity_medium(self):
        """测试中等复杂度"""
        classifier = QueryClassifier()
        result = classifier.classify("这个系统是如何工作的，有哪些组件？")

        assert result["complexity"] == "medium"

    def test_clear_cache(self):
        """测试清空缓存（保留接口兼容，不应报错）"""
        classifier = QueryClassifier()
        classifier.clear_cache()  # 不应抛出异常

    def test_classify_returns_dict_structure(self):
        """测试返回字典结构完整"""
        classifier = QueryClassifier()
        result = classifier.classify("测试查询")

        assert "intent_type" in result
        assert "confidence" in result
        assert "complexity" in result
        assert isinstance(result["confidence"], float)
        assert result["intent_type"] in ("factoid", "analytical", "procedural", "exploratory")
        assert result["complexity"] in ("simple", "medium", "complex")
