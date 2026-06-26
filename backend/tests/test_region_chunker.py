"""RegionChunker 按区域类型 Chunk 的单元测试。

覆盖场景：
- text 区域：委托给 text_chunking_strategy 进行文本切分
- table 区域：不切分，返回单个 chunk，保留表格原内容
- figure 区域：保存图片到 image_store，设置 has_image 元数据
- header 区域：更新 current_section，影响后续 chunk 的 section 标注
- equation 区域：不切分，返回单个 chunk，region_type="equation"

为什么用 MagicMock 替换 text_chunking_strategy：
RegionChunker 的职责是按区域类型路由和组装 chunk，而非实现切分算法；
mock 掉策略可以将两者解耦，单独验证 RegionChunker 的路由逻辑。
"""

import pytest
from unittest.mock import MagicMock

from core.models.document_region import DocumentRegion
from core.chunking.region_chunker import RegionChunker


@pytest.fixture
def chunker():
    """构造带 mock 策略的 RegionChunker。"""
    mock_strategy = MagicMock()
    mock_strategy.split.return_value = [
        {"content": "切分后的文本", "metadata": {"section": ""}}
    ]
    return RegionChunker(text_chunking_strategy=mock_strategy)


@pytest.fixture
def mock_image_store():
    """构造 mock ImageStore，save 返回固定路径。"""
    store = MagicMock()
    store.save.return_value = "images/abc123.png"
    return store


# ── text 区域测试 ──────────────────────────────────────────────────


def test_text_region_delegates_to_strategy(chunker):
    """text 区域必须委托给 text_chunking_strategy.split 进行切分，
    返回的 chunk 数量应 >= 1。

    为什么验证 >= 1 而非固定数量：不同策略对同一文本的切分粒度可能不同，
    RegionChunker 只需确保至少产出一个 chunk，不应耦合具体切分策略的行为。
    """
    region = DocumentRegion(
        type="text",
        content="这是一段正文内容，用于测试文本切分。",
        bbox=None,
        confidence=0.95,
    )
    chunks = chunker.chunk([region], source="测试文档.pdf")

    # 验证策略被调用
    chunker._text_chunking_strategy.split.assert_called_once()

    # 验证至少产出一个 chunk
    assert len(chunks) >= 1

    # 验证 chunk 格式：包含 text 和 metadata
    assert "text" in chunks[0]
    assert "metadata" in chunks[0]


# ── table 区域测试 ──────────────────────────────────────────────────


def test_table_region_not_split(chunker):
    """table 区域不切分，返回恰好 1 个 chunk，
    region_type 必须为 "table"，内容必须原样保留。

    为什么 table 不切分：表格是有结构的数据单元，拆分后会破坏行列
    对应关系，导致语义丢失；整表作为一个 chunk 保留了完整性。
    """
    table_content = "| 模块 | 状态 |\n|------|------|\n| A | 正常 |"
    region = DocumentRegion(
        type="table",
        content=table_content,
        bbox=(0, 0, 500, 300),
        confidence=0.92,
    )
    chunks = chunker.chunk([region], source="测试文档.pdf")

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["region_type"] == "table"
    assert table_content in chunks[0]["text"]

    # table 区域不应调用 text_chunking_strategy
    chunker._text_chunking_strategy.split.assert_not_called()


# ── figure 区域测试 ──────────────────────────────────────────────────


def test_figure_region_with_image_store(chunker, mock_image_store):
    """figure 区域在有 image_store 时，必须调用 image_store.save()，
    metadata 中必须包含 has_image=True 和 image_path。

    为什么需要 image_path：向量检索命中后，前端需要 image_path
    定位图片文件来展示给用户，这是多模态 RAG 的核心价值。
    """
    region = DocumentRegion(
        type="figure",
        content="架构图展示了三个微服务之间的调用关系",
        bbox=(10, 200, 500, 600),
        confidence=0.88,
        image_base64="iVBORw0KGgo=",
    )
    chunks = chunker.chunk(
        [region], source="测试文档.pdf", image_store=mock_image_store
    )

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["region_type"] == "figure"
    assert chunks[0]["metadata"]["has_image"] is True
    assert chunks[0]["metadata"]["image_path"] == "images/abc123.png"

    # 验证 image_store.save 被正确调用
    mock_image_store.save.assert_called_once_with("iVBORw0KGgo=", source="测试文档.pdf")


def test_figure_region_without_image_store(chunker):
    """figure 区域在没有 image_store 时，metadata 中不应出现 has_image。

    为什么允许无 image_store：某些场景（如纯文本检索模式或测试环境）
    不需要存储图片，RegionChunker 应优雅降级而非抛出异常。
    """
    region = DocumentRegion(
        type="figure",
        content="一张示意图",
        bbox=(10, 200, 500, 600),
        confidence=0.85,
        image_base64="iVBORw0KGgo=",
    )
    chunks = chunker.chunk([region], source="测试文档.pdf", image_store=None)

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["region_type"] == "figure"
    assert "has_image" not in chunks[0]["metadata"]
    assert "image_path" not in chunks[0]["metadata"]


# ── header 区域测试 ──────────────────────────────────────────────────


def test_header_updates_section(chunker):
    """header 区域必须更新 current_section，
    使其后的 text 区域 chunk 带上正确的 section 标注。

    为什么 section 跟踪很重要：section 让检索结果可以展示
    "出自哪个章节"，用户能快速判断结果的相关性和上下文。

    为什么 header 本身不产出 chunk：header 的内容已通过 section
    传递给后续 chunk，单独产出一个仅含标题的 chunk 会稀释
    检索结果的信息密度。
    """
    regions = [
        DocumentRegion(
            type="header",
            content="第三章 数据库设计",
            bbox=None,
            confidence=0.99,
        ),
        DocumentRegion(
            type="text",
            content="数据库采用 PostgreSQL，主表设计如下。",
            bbox=None,
            confidence=0.95,
        ),
    ]
    chunks = chunker.chunk(regions, source="技术文档.pdf")

    # header 不产出 chunk，只有 text 产出 1 个 chunk
    assert len(chunks) == 1

    # text 区域的 chunk 应包含 header 设置的 section
    assert "第三章 数据库设计" in chunks[0]["text"]
    assert chunks[0]["metadata"]["section"] == "第三章 数据库设计"


# ── equation 区域测试 ────────────────────────────────────────────────


def test_equation_region(chunker):
    """equation 区域不切分，返回恰好 1 个 chunk，
    region_type 必须为 "equation"，内容原样保留。

    为什么 equation 不切分：数学公式是一个完整的语义单元，
    拆分后公式不再完整，检索和展示都会失去意义。
    """
    equation_content = "E = mc^2"
    region = DocumentRegion(
        type="equation",
        content=equation_content,
        bbox=None,
        confidence=0.97,
    )
    chunks = chunker.chunk([region], source="物理讲义.pdf")

    assert len(chunks) == 1
    assert chunks[0]["metadata"]["region_type"] == "equation"
    assert equation_content in chunks[0]["text"]

    # equation 区域不应调用 text_chunking_strategy
    chunker._text_chunking_strategy.split.assert_not_called()
