"""VLM 管线端到端集成测试

模拟完整流程：VLMExtractor -> RegionChunker -> ImageStore -> DocumentProcessor，
不依赖真实 API，使用 Mock 验证数据在组件间正确流转。
"""

import base64
import os
import pytest
from unittest.mock import MagicMock

from core.models.document_region import DocumentRegion
from core.chunking.region_chunker import RegionChunker
from core.image_store import ImageStore
from core.document_processor import DocumentProcessor


# 使用合法的 base64 字符串，因为 ImageStore.save 会执行 base64.b64decode；
# 前缀 \x89PNG 使 ImageStore._detect_ext 识别为 .png 格式。
VALID_B64 = base64.b64encode(b"\x89PNG\r\n\x1a\nfakepngdata").decode("ascii")


def test_full_pipeline_image_to_chunks(tmp_path):
    """完整流程：图片 -> VLMExtractor -> RegionChunker -> chunks with image metadata"""

    # Mock VLMExtractor 返回结构化区域，避免调用真实 API
    mock_extractor = MagicMock()
    mock_extractor.extract.return_value = [
        DocumentRegion("header", "系统架构", None, 0.99),
        DocumentRegion("text", "本系统采用微服务架构，包含三个核心模块", None, 0.95),
        DocumentRegion(
            "figure",
            "架构图展示了用户服务、订单服务和支付服务的调用关系",
            (10, 200, 500, 600),
            0.88,
            VALID_B64,
        ),
        DocumentRegion(
            "table",
            "| 服务 | 端口 |\n|------|------|\n| 用户 | 8001 |",
            None,
            0.92,
        ),
    ]

    # 使用 tmp_path 作为真实 ImageStore 存储目录，验证文件实际落盘
    image_store = ImageStore(str(tmp_path))

    # config 需暴露语义切分参数，DocumentProcessor 构造函数会读取
    mock_config = MagicMock()
    mock_config.SEMANTIC_CHUNK_PERCENTILE = 25
    mock_config.SEMANTIC_CHUNK_MIN_SENTENCES = 2
    mock_config.SEMANTIC_CHUNK_MAX_SENTENCES = 20

    # mock chunking strategy：返回单个子 chunk，模拟文本切分行为
    mock_chunking = MagicMock()
    mock_chunking.split.return_value = [
        {"content": "本系统采用微服务架构", "metadata": {"section": ""}}
    ]

    # 组装完整管线，各组件通过依赖注入连接
    processor = DocumentProcessor(
        mock_config,
        image_pipeline=mock_extractor,
        image_store=image_store,
        chunking_strategy=mock_chunking,
    )

    # 执行端到端处理，验证不抛异常
    chunks, embeddings = processor.process_file("test_architecture.png")

    # 至少应产出 text + figure + table 三种类型的 chunk
    assert len(chunks) >= 3

    # figure chunk 必须携带图片元数据，供下游多模态检索使用
    figure_chunks = [
        c for c in chunks if c["metadata"].get("region_type") == "figure"
    ]
    assert len(figure_chunks) == 1
    assert figure_chunks[0]["metadata"]["has_image"] is True
    assert "image_path" in figure_chunks[0]["metadata"]

    # 验证图片文件确实写入了 tmp_path 磁盘，而非仅存在于内存
    image_path = figure_chunks[0]["metadata"]["image_path"]
    assert os.path.exists(os.path.join(str(tmp_path), image_path))

    # table 是不可拆分的语义单元，应保持原样不被切分
    table_chunks = [
        c for c in chunks if c["metadata"].get("region_type") == "table"
    ]
    assert len(table_chunks) == 1
    assert "| 服务 |" in table_chunks[0]["text"]

    # section 应从 header 区域继承，而非留空
    assert figure_chunks[0]["metadata"]["section"] == "系统架构"
    assert table_chunks[0]["metadata"]["section"] == "系统架构"

    # embeddings 列表长度必须与 chunks 一一对应
    assert len(embeddings) == len(chunks)


def test_legacy_pipeline_still_works():
    """旧管线（USE_VLM_EXTRACTOR=False）行为不变

    当 image_pipeline 为 None 时，DocumentProcessor 不应尝试
    调用 VLM 管线，而是保留旧管线的处理路径。
    """
    mock_config = MagicMock()
    mock_config.SEMANTIC_CHUNK_PERCENTILE = 25
    mock_config.SEMANTIC_CHUNK_MIN_SENTENCES = 2
    mock_config.SEMANTIC_CHUNK_MAX_SENTENCES = 20

    # image_pipeline=None 表示不启用 VLM 管线
    processor = DocumentProcessor(
        mock_config,
        image_pipeline=None,
        image_store=None,
    )

    # 旧管线模式下 _image_pipeline 必须为 None
    assert processor._image_pipeline is None

    # image_store 也应为 None，避免旧管线意外调用图片存储
    assert processor._image_store is None
