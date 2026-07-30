"""模型自动发现注册表

扫描所有 provider 模块，发现带有 _FACTORY_NAME 的类，
自动注册到对应类型的全局注册表中。

同时保留原有 DocumentRegion 导出（VLMExtractor / RegionChunker 使用）。
"""

import inspect
import importlib
import logging

# ── 原有导出（保持向后兼容） ──
from .document_region import DocumentRegion

__all__ = [
    "DocumentRegion",
    "ModelType",
    "ChatModel",
    "EmbeddingModel",
    "RerankModel",
    "CvModel",
    "OcrModel",
    "TtsModel",
    "AsrModel",
    "get_registry",
    "list_registered_providers",
    "_infer_factory",
]

logger = logging.getLogger(__name__)


class ModelType:
    CHAT = "chat"
    EMBEDDING = "embedding"
    RERANK = "rerank"
    CV = "cv"
    OCR = "ocr"
    TTS = "tts"
    ASR = "asr"


# 每种类型的注册表：{factory_name: ProviderClass}
ChatModel: dict[str, type] = {}
EmbeddingModel: dict[str, type] = {}
RerankModel: dict[str, type] = {}
CvModel: dict[str, type] = {}
OcrModel: dict[str, type] = {}
TtsModel: dict[str, type] = {}
AsrModel: dict[str, type] = {}

_REGISTRY_MAP = {
    ModelType.CHAT: ChatModel,
    ModelType.EMBEDDING: EmbeddingModel,
    ModelType.RERANK: RerankModel,
    ModelType.CV: CvModel,
    ModelType.OCR: OcrModel,
    ModelType.TTS: TtsModel,
    ModelType.ASR: AsrModel,
}


def _register(provider_cls, factory_name, registry):
    if isinstance(factory_name, list):
        for name in factory_name:
            registry[name] = provider_cls
    else:
        registry[factory_name] = provider_cls


def _discover_providers(module_name: str, model_type: str):
    try:
        module = importlib.import_module(f"core.models.{module_name}")
    except ImportError as e:
        logger.debug("Cannot import %s: %s", module_name, e)
        return

    registry = _REGISTRY_MAP.get(model_type)
    if registry is None:
        return

    for name, cls in inspect.getmembers(module, inspect.isclass):
        factory_name = getattr(cls, "_FACTORY_NAME", None)
        if factory_name and hasattr(cls, "__init__"):
            _register(cls, factory_name, registry)
            logger.debug("Registered %s: %s -> %s", model_type, factory_name, name)


# Auto-discover all provider modules
_discover_providers("chat_providers", ModelType.CHAT)
_discover_providers("embedding_providers", ModelType.EMBEDDING)
_discover_providers("rerank_providers", ModelType.RERANK)
_discover_providers("cv_providers", ModelType.CV)
_discover_providers("ocr_providers", ModelType.OCR)
_discover_providers("tts_providers", ModelType.TTS)
_discover_providers("asr_providers", ModelType.ASR)


def get_registry(model_type: str) -> dict[str, type]:
    """获取指定类型的注册表"""
    return _REGISTRY_MAP.get(model_type, {})


def list_registered_providers() -> dict[str, list[str]]:
    """列出所有已注册的 provider"""
    return {mt: list(reg.keys()) for mt, reg in _REGISTRY_MAP.items() if reg}


# ── 厂商自动推断 ────────────────────────────────────────────────────────────
# 根据 API Base URL 自动匹配厂商，无需用户手动选择

_API_BASE_PATTERNS: list[tuple[str, str]] = [
    ("deepseek.com", "DeepSeek"),
    ("siliconflow.cn", "SILICONFLOW"),
    ("dashscope.aliyuncs.com", "Tongyi-Qianwen"),
    ("jina.ai", "Jina"),
    ("cohere.ai", "Cohere"),
    ("anthropic.com", "Anthropic"),
    ("gemini", "Gemini"),
    ("localhost", "Ollama"),       # Ollama local
    ("11434", "Ollama"),           # Ollama default port
    ("openai.com", "OpenAI"),
]


def _infer_factory(api_base: str, model_type: str = "") -> str:
    """根据 API Base URL 自动推断厂商名。
    如果 API Base 为空或匹配不到，默认用 OpenAI。
    """
    if not api_base:
        return "OpenAI"

    base = api_base.lower().strip().rstrip("/")
    for pattern, factory in _API_BASE_PATTERNS:
        if pattern in base:
            return factory

    # 默认兜底：OpenAI 兼容
    return "OpenAI"
