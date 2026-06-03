import pytest
from unittest.mock import Mock
from core.query_understanding.hyde_generator import HyDEGenerator


@pytest.fixture
def mock_llm():
    return Mock()


def test_hyde_generates_hypothetical_document(mock_llm):
    """测试HyDE生成假设性文档"""
    mock_llm.generate.return_value = "Python装饰器是一种语法糖，用于修改函数或类的行为..."

    generator = HyDEGenerator(llm_client=mock_llm)
    result = generator.generate_hypothetical_document("Python装饰器怎么用？")

    assert isinstance(result, str)
    assert len(result) > 0
    mock_llm.generate.assert_called_once()


def test_hyde_returns_none_for_factoid(mock_llm):
    """测试事实型查询不使用HyDE"""
    generator = HyDEGenerator(llm_client=mock_llm)

    # 事实型查询不应该生成HyDE
    result = generator.generate_hypothetical_document(
        "Python的创始人是谁？",
        intent_type="factoid"
    )

    assert result is None
    mock_llm.generate.assert_not_called()


def test_hyde_generates_for_analytical(mock_llm):
    """测试分析型查询生成HyDE"""
    mock_llm.generate.return_value = "假设性文档内容..."

    generator = HyDEGenerator(llm_client=mock_llm)
    result = generator.generate_hypothetical_document(
        "比较Python和Java的优缺点",
        intent_type="analytical"
    )

    assert result is not None
    assert len(result) > 0
    mock_llm.generate.assert_called_once()


def test_hyde_handles_llm_exception(mock_llm):
    """测试LLM抛出异常时返回None"""
    mock_llm.generate.side_effect = RuntimeError("API调用失败")

    generator = HyDEGenerator(llm_client=mock_llm)
    result = generator.generate_hypothetical_document("测试查询")

    assert result is None


def test_hyde_handles_empty_response(mock_llm):
    """测试LLM返回空字符串"""
    mock_llm.generate.return_value = ""

    generator = HyDEGenerator(llm_client=mock_llm)
    result = generator.generate_hypothetical_document("测试查询")

    assert result is None


def test_hyde_handles_none_response(mock_llm):
    """测试LLM返回None"""
    mock_llm.generate.return_value = None

    generator = HyDEGenerator(llm_client=mock_llm)
    result = generator.generate_hypothetical_document("测试查询")

    assert result is None
