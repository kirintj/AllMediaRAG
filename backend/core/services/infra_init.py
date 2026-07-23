"""基础设施组件初始化辅助函数。

每个函数负责初始化一个可选组件，统一使用 _try_init 包装
以提供 try/except + 日志模式。由 infra_factory.create_infra 调用。
"""
import logging

from core.ocr.paddle_provider import PaddleOCRProvider
from core.ocr.tesseract_provider import TesseractOCRProvider
from core.ocr.vlm_provider import VLMProvider

logger = logging.getLogger(__name__)


def _try_init(name: str, factory, *args, **kwargs):
    """通用组件初始化辅助：统一 try/except + 日志模式。

    为什么抽取：所有 _init_* 函数都有相同的 try/init/log-success-or-warning 结构，
    用工厂函数 + 名称参数消除重复。

    Args:
        name: 组件名称（用于日志）
        factory: 工厂函数/类构造器
        *args, **kwargs: 传给 factory 的参数

    Returns:
        factory 的返回值，失败时返回 None
    """
    try:
        component = factory(*args, **kwargs)
        logger.info("%s initialized", name)
        return component
    except Exception as e:
        logger.warning("Failed to init %s: %s", name, e)
        return None


def _init_ocr_provider(config):
    """初始化 OCR 提供者（PaddleOCR / Tesseract / 禁用）。"""
    ocr_type = config.OCR_PROVIDER.lower()
    if ocr_type == "none":
        logger.info("OCR disabled by config")
        return None
    if ocr_type == "paddle":
        provider = _try_init(
            "PaddleOCR provider",
            lambda: PaddleOCRProvider(lang=config.OCR_LANG, use_gpu=config.OCR_USE_GPU),
        )
        return provider
    elif ocr_type == "tesseract":
        provider = _try_init(
            "TesseractOCR provider",
            lambda: TesseractOCRProvider(lang="chi_sim+eng"),
        )
        return provider
    logger.warning("Unknown OCR_PROVIDER: %s", ocr_type)
    return None


def _init_vlm_provider(config):
    """初始化 VLM 提供者（DashScope/MIMO 接口）。"""
    if not config.USE_VLM:
        logger.info("VLM disabled by config")
        return None
    if not config.VLM_MODEL or not config.VLM_API_BASE:
        logger.warning("VLM_MODEL or VLM_API_BASE not configured")
        return None
    provider = _try_init(
        "VLM provider",
        lambda: VLMProvider(
            api_key=config.MIMO_API_KEY,
            api_base=config.VLM_API_BASE,
            model=config.VLM_MODEL,
        ),
    )
    if provider:
        logger.info("VLM provider model=%s", config.VLM_MODEL)
    return provider


def _init_vlm_extractor(config):
    """初始化 VLMExtractor（新版统一提取器）

    为什么与 _init_vlm_provider 分开：
    两者使用不同的 API（DashScope vs SiliconFlow/MIMO），
    配置项也不同，分开初始化避免混淆。
    """
    if not config.USE_VLM_EXTRACTOR:
        logger.info("VLM Extractor disabled by config")
        return None
    if not config.VLM_EXTRACTOR_API_KEY:
        logger.warning("VLM_EXTRACTOR_API_KEY not configured, VLM Extractor disabled")
        return None

    def _create_extractor():
        from core.ocr.vlm_extractor import VLMExtractor
        return VLMExtractor(
            api_key=config.VLM_EXTRACTOR_API_KEY,
            api_base=config.VLM_EXTRACTOR_API_BASE,
            model=config.VLM_EXTRACTOR_MODEL,
            max_tokens=config.VLM_EXTRACTOR_MAX_TOKENS,
            timeout=config.VLM_EXTRACTOR_TIMEOUT,
            max_image_size=config.VLM_EXTRACTOR_MAX_IMAGE_SIZE,
        )

    extractor = _try_init("VLM Extractor", _create_extractor)
    if extractor:
        logger.info("VLM Extractor model=%s", config.VLM_EXTRACTOR_MODEL)
    return extractor


def _init_image_store(config):
    """初始化 ImageStore

    为什么与 VLMExtractor 分开初始化：
    ImageStore 的生命周期独立于 VLMExtractor，
    即使 VLMExtractor 未启用，旧管线未来也可能需要图片存储。
    """
    if not config.IMAGE_STORE_ENABLED:
        logger.info("ImageStore disabled by config")
        return None

    def _create_store():
        from core.image_store import ImageStore
        return ImageStore(base_dir=config.IMAGE_STORE_DIR)

    store = _try_init("ImageStore", _create_store)
    if store:
        logger.info("ImageStore dir=%s", config.IMAGE_STORE_DIR)
    return store


def _init_chunking_strategy(config):
    """初始化文档分块策略（semantic / fixed_size / recursive / parent_child）。"""
    from core.chunking import (
        SemanticChunking,
        FixedSizeChunking,
        RecursiveChunking,
        ParentChildChunking,
    )

    strategy_name = getattr(config, "CHUNKING_STRATEGY", "semantic")

    if strategy_name == "fixed_size":
        strategy = FixedSizeChunking(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
    elif strategy_name == "recursive":
        strategy = RecursiveChunking(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
    elif strategy_name == "parent_child":
        strategy = ParentChildChunking(
            child_sentences=getattr(config, "PC_CHILD_SENTENCES", 3),
            parent_groups=getattr(config, "PC_PARENT_GROUPS", 4),
            overlap_sentences=getattr(config, "PC_OVERLAP_SENTENCES", 1),
        )
    else:
        strategy = SemanticChunking(
            percentile=config.SEMANTIC_CHUNK_PERCENTILE,
            min_sentences=config.SEMANTIC_CHUNK_MIN_SENTENCES,
            max_sentences=config.SEMANTIC_CHUNK_MAX_SENTENCES,
        )

    logger.info("Chunking strategy initialized: %s", strategy.name)
    return strategy


def _build_file_reader_registry(ocr_provider, vlm_provider) -> dict:
    """构建文件读取器注册表：{ 文件扩展名 → Reader 实例 }。"""
    from core.providers.readers import (
        EnhancedPDFReader,
        MarkdownReader,
        DocxReader,
        HtmlReader,
        ImageReader,
        ExcelReader,
        PptxReader,
        JsonReader,
        AudioReader,
    )

    readers = [
        EnhancedPDFReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
        MarkdownReader(),
        DocxReader(),
        HtmlReader(),
        ImageReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
        ExcelReader(),
        PptxReader(),
        JsonReader(),
        AudioReader(),  # ASR bundle not yet available; configure via set_asr_bundle()
    ]
    registry: dict = {}
    for reader in readers:
        for ext in reader.supported_extensions():
            registry[ext] = reader
    logger.info("File reader registry built: %s", list(registry.keys()))
    return registry
