"""VLMExtractor 统一提取器的单元测试。

覆盖场景：
- VLM 响应解析（正常 JSON、markdown 包裹、纯文本回退）
- 空区域处理（有摘要/无摘要）
- VLM 使用判断逻辑（扫描页 vs 文字页）

为什么用 mock 而非真实 OpenAI 调用：
单元测试应独立于外部服务，mock 掉 _client 可以：
1. 避免测试依赖网络和 API key；
2. 让测试运行时间从秒级降到毫秒级；
3. 可以精确控制返回值来覆盖边界情况。
"""

import json
import pytest
from unittest.mock import MagicMock

from core.ocr.vlm_extractor import VLMExtractor, TEXT_THRESHOLD_FOR_VLM


# ── 测试用常量 ──────────────────────────────────────────────────

# 为什么用 json.dumps + ensure_ascii=False：直接生成含中文的 JSON 字符串，
# 避免手写 JSON 时遗漏引号或逗号导致测试 fixture 本身有语法错误。
VALID_VLM_RESPONSE = json.dumps(
    {
        "regions": [
            {"type": "header", "content": "第一章 系统概述", "confidence": 0.99},
            {
                "type": "text",
                "content": "本系统采用微服务架构",
                "confidence": 0.95,
            },
            {
                "type": "table",
                "content": "| 模块 | 状态 |\n|------|------|\n| A | 正常 |",
                "confidence": 0.92,
            },
            {
                "type": "figure",
                "content": "架构图展示了三个微服务之间的调用关系",
                "bbox": [10, 200, 500, 600],
                "confidence": 0.88,
            },
        ],
        "page_summary": "系统架构概述页面",
    },
    ensure_ascii=False,
)


@pytest.fixture
def extractor():
    """构造带 mock client 的 VLMExtractor。

    为什么用 MagicMock 替换 _client：
    __init__ 不会真正创建 OpenAI 客户端，
    直接替换 _client 属性可以绕过网络初始化，
    同时保留其他方法（如 _call_vlm）的正常调用路径。
    """
    ext = VLMExtractor(
        api_key="test", api_base="https://test.com/v1", model="test"
    )
    ext._client = MagicMock()
    return ext


# ── 解析测试 ────────────────────────────────────────────────────


def test_parse_valid_response(extractor):
    """正常的 JSON 响应：4 个区域全部正确解析，figure 带 bbox。

    为什么单独检查 figure 的 bbox：
    bbox 是 list→tuple 转换的关键路径，直接决定下游
    _crop_image 能否正确裁剪图片区域。
    """
    regions = extractor._parse_response(VALID_VLM_RESPONSE)

    assert len(regions) == 4

    # 标题区域
    assert regions[0].type == "header"
    assert regions[0].content == "第一章 系统概述"
    assert regions[0].confidence == 0.99
    assert regions[0].bbox is None

    # 文本区域
    assert regions[1].type == "text"
    assert regions[1].content == "本系统采用微服务架构"

    # 表格区域
    assert regions[2].type == "table"
    assert "| 模块 |" in regions[2].content

    # 图片区域：唯一需要检查 bbox 的类型
    assert regions[3].type == "figure"
    assert regions[3].content == "架构图展示了三个微服务之间的调用关系"
    assert regions[3].bbox == (10, 200, 500, 600)
    assert regions[3].confidence == 0.88


def test_parse_invalid_json_fallback(extractor):
    """VLM 返回纯文本而非 JSON 时，回退为单个 text 区域。

    为什么需要这个回退：VLM 有时会输出自然语言描述而非结构化 JSON，
    直接丢弃这些内容会导致信息完全丢失；
    包装成 text 区域至少保留了文本，后续 chunking 仍可处理。
    """
    raw = "这是一段纯文本内容，不是 JSON 格式"
    regions = extractor._parse_response(raw)

    assert len(regions) == 1
    assert regions[0].type == "text"
    assert regions[0].content == raw
    assert regions[0].bbox is None
    assert regions[0].confidence == 0.5


def test_parse_json_in_markdown_block(extractor):
    """VLM 在 markdown 代码块中返回 JSON：提取内部 JSON 再解析。

    为什么 VLM 会包裹代码块：某些模型（如 ChatGPT 系列）默认用
    ```json ... ``` 包裹 JSON 输出，这是模型的格式化习惯而非错误。
    """
    wrapped = f"```json\n{VALID_VLM_RESPONSE}\n```"
    regions = extractor._parse_response(wrapped)

    # 应该和直接 JSON 解析结果一致
    assert len(regions) == 4
    assert regions[0].type == "header"
    assert regions[3].type == "figure"


def test_parse_empty_regions_with_summary(extractor):
    """regions 为空但有 page_summary：用摘要生成一个 text 区域。

    为什么用摘要兜底：VLM 有时认为页面无结构化内容（如纯装饰页），
    但 page_summary 可能仍有信息价值（如"本页为目录页"），
    丢弃摘要会导致该页面在检索中完全不可见。
    """
    response = json.dumps(
        {"regions": [], "page_summary": "本页为目录页，列出各章节标题"},
        ensure_ascii=False,
    )
    regions = extractor._parse_response(response)

    assert len(regions) == 1
    assert regions[0].type == "text"
    assert regions[0].content == "本页为目录页，列出各章节标题"
    assert regions[0].confidence == 0.5


def test_parse_empty_regions_no_summary(extractor):
    """regions 和 page_summary 都为空：返回空列表。

    为什么允许空列表：空白页或纯装饰页不应产生任何区域，
    强制填充内容反而会引入噪声，降低检索质量。
    """
    response = json.dumps({"regions": [], "page_summary": ""}, ensure_ascii=False)
    regions = extractor._parse_response(response)

    assert len(regions) == 0


# ── VLM 使用判断测试 ────────────────────────────────────────────


def test_should_use_vlm_for_scanned_page(extractor):
    """文字很少的页面（扫描件）：应使用 VLM。

    为什么阈值是 200 字符：少于 200 字符的页面大概率是扫描件或
    纯图片页，传统 OCR 提取的文本不足以反映页面内容，
    此时 VLM 的视觉理解能力能显著提升信息提取质量。
    """
    short_text = "仅有一行标题"
    assert len(short_text) < TEXT_THRESHOLD_FOR_VLM
    assert extractor._should_use_vlm_for_page(short_text) is True


def test_should_not_use_vlm_for_text_page(extractor):
    """文字密集的页面：不应使用 VLM，直接用 PyMuPDF 提取的文本。

    为什么长文本跳过 VLM：当 PyMuPDF 已能提取足够文字时，
    VLM 调用不仅浪费 token 和时间，还可能引入识别错误；
    传统文本提取在文字密集页面上更准确、更可靠。
    """
    # 为什么手动生成而非固定字符串：确保长度精确超过阈值，
    # 避免因手动计数错误导致测试在阈值边界误判。
    long_text = "这是一段很长的文本内容。" * 20  # 约 240 字符
    assert len(long_text) > TEXT_THRESHOLD_FOR_VLM
    assert extractor._should_use_vlm_for_page(long_text) is False
