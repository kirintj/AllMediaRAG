"""RAG 服务基础设施包。

对外导出 InfraBundle（依赖容器）和 create_infra（工厂函数），
以及初始化辅助函数（供 RAGEngine 向后兼容委托使用）。
"""
from .infra_bundle import InfraBundle
from .infra_factory import create_infra
from .infra_init import (
    _try_init,
    _init_ocr_provider,
    _init_vlm_provider,
    _init_vlm_extractor,
    _init_image_store,
    _init_chunking_strategy,
    _build_file_reader_registry,
)
