import pytest
from unittest.mock import Mock

def test_multi_query_generates_variants():
    """测试多查询生成"""
    from core.query_understanding.multi_query import MultiQueryGenerator

    mock_llm = Mock()
    mock_llm.generate.return_value = "1. Python装饰器的使用方法\n2. 如何在Python中使用装饰器\n3. Python装饰器教程"

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("Python装饰器怎么用？", num_queries=3)

    assert isinstance(queries, list)
    assert len(queries) == 4  # 原始查询 + 3个变体
    assert queries[0] == "Python装饰器怎么用？"  # 第一个是原始查询
    assert all(isinstance(q, str) for q in queries)

def test_multi_query_includes_original():
    """测试返回结果包含原始查询"""
    from core.query_understanding.multi_query import MultiQueryGenerator

    mock_llm = Mock()
    mock_llm.generate.return_value = "1. 变体1\n2. 变体2"

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("原始查询", num_queries=2)

    assert queries[0] == "原始查询"
    assert len(queries) == 3

def test_multi_query_handles_empty_response():
    """测试处理空响应"""
    from core.query_understanding.multi_query import MultiQueryGenerator

    mock_llm = Mock()
    mock_llm.generate.return_value = ""

    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("测试查询", num_queries=3)

    assert len(queries) == 1  # 只有原始查询
    assert queries[0] == "测试查询"
