"""QueryClassifier 测试"""
import pytest
from unittest.mock import Mock

from core.query_understanding.classifier import QueryClassifier


class TestQueryClassifier:
    """QueryClassifier 测试套件"""

    def test_classify_factoid_query(self):
        """测试事实型查询分类"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("北京的天气如何？")

        assert result["intent_type"] == "factoid"
        assert result["confidence"] == 0.9
        assert result["complexity"] == "simple"
        mock_llm.generate.assert_called_once()

    def test_classify_analytical_query(self):
        """测试分析型查询分类"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "analytical", "confidence": 0.85, "complexity": "complex"}'

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("比较Python和Java的优缺点")

        assert result["intent_type"] == "analytical"
        assert result["confidence"] == 0.85
        assert result["complexity"] == "complex"

    def test_classify_with_caching(self):
        """测试缓存功能"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm, cache_size=10)

        # 第一次调用
        result1 = classifier.classify("测试查询")
        assert mock_llm.generate.call_count == 1

        # 第二次调用相同查询，应使用缓存
        result2 = classifier.classify("测试查询")
        assert mock_llm.generate.call_count == 1  # LLM只被调用一次
        assert result1 == result2

    def test_classify_cache_eviction(self):
        """测试缓存淘汰"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm, cache_size=2)

        classifier.classify("查询1")
        classifier.classify("查询2")
        classifier.classify("查询3")  # 应该淘汰查询1

        assert "查询1" not in classifier.cache
        assert "查询2" in classifier.cache
        assert "查询3" in classifier.cache

    def test_classify_invalid_json(self):
        """测试无效JSON响应"""
        mock_llm = Mock()
        mock_llm.generate.return_value = "这不是JSON"

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("测试查询")

        assert result["intent_type"] == "factoid"
        assert result["confidence"] == 0.5
        assert result["complexity"] == "medium"

    def test_classify_missing_fields(self):
        """测试缺少字段的JSON"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid"}'

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("测试查询")

        assert result["intent_type"] == "factoid"
        assert result["confidence"] == 0.5
        assert result["complexity"] == "medium"

    def test_classify_invalid_intent_type(self):
        """测试无效的意图类型"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "invalid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("测试查询")

        assert result["intent_type"] == "factoid"  # 默认值

    def test_classify_confidence_bounds(self):
        """测试置信度边界"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 1.5, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("测试查询")

        assert result["confidence"] == 1.0  # 被限制在1.0

    def test_clear_cache(self):
        """测试清空缓存"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm, cache_size=10)
        classifier.classify("测试查询")

        assert len(classifier.cache) == 1

        classifier.clear_cache()
        assert len(classifier.cache) == 0

    def test_classifier_cache_disabled(self):
        """测试缓存禁用（cache_size=0）"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm, cache_size=0)

        classifier.classify("查询1")
        classifier.classify("查询1")  # 相同查询，应该再次调用LLM

        assert mock_llm.generate.call_count == 2  # LLM被调用两次
        assert len(classifier.cache) == 0  # 缓存为空

    def test_classifier_lru_ordering(self):
        """测试LRU淘汰顺序"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.9, "complexity": "simple"}'

        classifier = QueryClassifier(llm_client=mock_llm, cache_size=2)

        classifier.classify("查询1")
        classifier.classify("查询2")
        classifier.classify("查询1")  # 访问查询1，更新其LRU顺序
        classifier.classify("查询3")  # 应该淘汰查询2（最久未访问）

        assert "查询1" in classifier.cache  # 查询1被保留
        assert "查询2" not in classifier.cache  # 查询2被淘汰
        assert "查询3" in classifier.cache  # 查询3被添加

    def test_classifier_handles_non_dict_json(self):
        """测试处理非dict的JSON响应"""
        mock_llm = Mock()
        mock_llm.generate.return_value = "null"  # JSON null

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("测试查询")

        assert result["intent_type"] == "factoid"  # 默认值
        assert result["confidence"] == 0.5  # 默认值

    def test_classifier_handles_list_json(self):
        """测试处理列表JSON响应"""
        mock_llm = Mock()
        mock_llm.generate.return_value = '[1, 2, 3]'  # JSON数组

        classifier = QueryClassifier(llm_client=mock_llm)
        result = classifier.classify("测试查询")

        assert result["intent_type"] == "factoid"  # 默认值
