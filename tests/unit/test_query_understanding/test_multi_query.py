import pytest
from unittest.mock import Mock

from core.query_understanding.multi_query import MultiQueryGenerator


@pytest.fixture
def mock_llm():
    return Mock()


def test_multi_query_generates_variants(mock_llm):
    """测试多查询生成"""
    mock_llm.generate.return_value = "1. Python装饰器的使用方法\n2. 如何在Python中使用装饰器\n3. Python装饰器教程"

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("Python装饰器怎么用？", num_queries=3)

    assert isinstance(queries, list)
    assert len(queries) == 4
    assert queries[0] == "Python装饰器怎么用？"
    assert queries[1] == "Python装饰器的使用方法"
    assert queries[2] == "如何在Python中使用装饰器"
    assert queries[3] == "Python装饰器教程"


def test_multi_query_includes_original(mock_llm):
    """测试返回结果包含原始查询"""
    mock_llm.generate.return_value = "1. 变体1\n2. 变体2"

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("原始查询", num_queries=2)

    assert queries[0] == "原始查询"
    assert len(queries) == 3


def test_multi_query_handles_empty_response(mock_llm):
    """测试处理空响应"""
    mock_llm.generate.return_value = ""

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("测试查询", num_queries=3)

    assert len(queries) == 1
    assert queries[0] == "测试查询"


def test_multi_query_handles_llm_exception(mock_llm):
    """测试LLM抛出异常"""
    mock_llm.generate.side_effect = RuntimeError("API调用失败")

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("测试查询", num_queries=3)

    assert len(queries) == 1
    assert queries[0] == "测试查询"


def test_multi_query_handles_none_response(mock_llm):
    """测试LLM返回None"""
    mock_llm.generate.return_value = None

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("测试查询", num_queries=3)

    assert len(queries) == 1
    assert queries[0] == "测试查询"
