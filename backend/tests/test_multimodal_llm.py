from core.llm_client import LLMClient


def test_build_content_no_images():
    """无图片时返回纯文本，确保向后兼容"""
    client = LLMClient("key", "https://test.com", "model")
    result = client._build_content("hello", None)
    assert result == "hello"
    assert isinstance(result, str)


def test_build_content_with_images():
    """有图片时返回多模态 content 数组"""
    client = LLMClient("key", "https://test.com", "model")
    result = client._build_content("describe this", ["base64data1", "base64data2"])
    assert isinstance(result, list)
    assert result[0] == {"type": "text", "text": "describe this"}
    assert result[1]["type"] == "image_url"
    assert "base64data1" in result[1]["image_url"]["url"]
    assert len(result) == 3


def test_build_content_empty_images_list():
    """空图片列表等同于无图片，保持向后兼容"""
    client = LLMClient("key", "https://test.com", "model")
    result = client._build_content("hello", [])
    assert result == "hello"
