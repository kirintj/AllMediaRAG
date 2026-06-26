"""DocumentRegion 数据模型的单元测试。

覆盖场景：
- 各合法区域类型的构造（text / figure / table / equation / header）
- 非法类型的校验报错
- 非 figure 类型自动清空 image_base64

为什么每个测试只断言一个关注点：
单一职责的测试在失败时能精确指向问题所在，避免"一个测试覆盖太多
导致第一个断言失败就掩盖了后续断言的问题"。
"""

import pytest

from core.models.document_region import DocumentRegion


# ── 基本类型构造 ──────────────────────────────────────────────


def test_create_text_region():
    """纯文本区域：bbox 可以为 None，image_base64 保持空字符串。"""
    region = DocumentRegion(
        type="text",
        content="这是一段文字",
        bbox=None,
        confidence=0.95,
        image_base64="",
    )
    assert region.type == "text"
    assert region.content == "这是一段文字"
    assert region.bbox is None
    assert region.confidence == 0.95
    assert region.image_base64 == ""


def test_create_figure_region_with_image():
    """图片区域：唯一允许携带 image_base64 的类型。"""
    region = DocumentRegion(
        type="figure",
        content="流程图展示了用户认证过程",
        bbox=(10, 20, 300, 400),
        confidence=0.88,
        image_base64="iVBORw0KGgo=",
    )
    assert region.type == "figure"
    assert region.image_base64 == "iVBORw0KGgo="
    assert region.bbox == (10, 20, 300, 400)


def test_create_table_region():
    """表格区域：content 存 Markdown 格式的表格文本。"""
    md_table = "| 指标 | Q1 | Q2 |\n|------|----|----|\n| 收入 | 100| 120|"
    region = DocumentRegion(
        type="table",
        content=md_table,
        bbox=(0, 0, 500, 200),
        confidence=0.92,
        image_base64="",
    )
    assert region.type == "table"
    assert "| 指标 |" in region.content


def test_create_equation_region():
    """公式区域：LaTeX 格式内容，image_base64 应被清空。"""
    region = DocumentRegion(
        type="equation",
        content="E = mc^2",
        bbox=None,
        confidence=0.95,
        image_base64="should_be_cleared",
    )
    assert region.type == "equation"
    assert region.content == "E = mc^2"
    assert region.image_base64 == ""


def test_create_header_region():
    """标题区域：作为 section 名称，image_base64 应被清空。"""
    region = DocumentRegion(
        type="header",
        content="第一章 系统概述",
        bbox=None,
        confidence=0.99,
        image_base64="should_be_cleared",
    )
    assert region.type == "header"
    assert region.content == "第一章 系统概述"
    assert region.image_base64 == ""


# ── 校验逻辑 ──────────────────────────────────────────────────


def test_region_type_validation():
    """非法类型必须在构造时抛出 ValueError，错误信息包含中文提示。"""
    with pytest.raises(ValueError, match="不支持的区域类型"):
        DocumentRegion(
            type="invalid_type",
            content="test",
            bbox=None,
            confidence=0.5,
            image_base64="",
        )


def test_non_figure_clears_image_base64():
    """非 figure 类型即使传入 image_base64，也会被 __post_init__ 清空。

    为什么单独测这个：上游 VLM 可能误填图片数据给文本区域，
    清空逻辑是防御性编程的关键路径，必须有测试覆盖。
    """
    region = DocumentRegion(
        type="text",
        content="一段文字",
        bbox=None,
        confidence=0.9,
        image_base64="should_be_cleared",
    )
    assert region.image_base64 == ""


def test_figure_preserves_image_base64():
    """figure 类型的 image_base64 必须原样保留，不能被清空。"""
    region = DocumentRegion(
        type="figure",
        content="示意图",
        bbox=(0, 0, 100, 100),
        confidence=0.85,
        image_base64="iVBORw0KGgo=",
    )
    assert region.image_base64 == "iVBORw0KGgo="
