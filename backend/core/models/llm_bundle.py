"""LLMBundle -- 统一模型门面

一个类代理所有模型类型的所有操作。
用法:
    bundle = LLMBundle(tenant_id, "chat", tenant_llm_service)
    answer = bundle.chat([{"role": "user", "content": "hello"}])
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.models import (
    ChatModel,
    EmbeddingModel,
    RerankModel,
    CvModel,
    OcrModel,
    TtsModel,
    AsrModel,
)

if TYPE_CHECKING:
    from core.models.tenant_llm_service import TenantLLMService

logger = logging.getLogger(__name__)

_REGISTRY_MAP = {
    "chat": ChatModel,
    "embedding": EmbeddingModel,
    "rerank": RerankModel,
    "cv": CvModel,
    "ocr": OcrModel,
    "tts": TtsModel,
    "asr": AsrModel,
}


class LLMBundle:
    """统一模型门面：一个类代理所有模型类型的所有操作"""

    def __init__(
        self,
        tenant_id: str,
        model_type: str,
        tenant_llm_service: TenantLLMService,
    ):
        self._model_type = model_type
        self._tenant_id = tenant_id

        model_config = tenant_llm_service.get_default_model(tenant_id, model_type)
        if not model_config:
            raise ValueError(
                f"No default {model_type} model configured for tenant {tenant_id}"
            )

        self._mdl = self._model_instance(model_config)
        logger.info(
            "LLMBundle initialized: tenant=%s, type=%s, factory=%s, model=%s",
            tenant_id,
            model_type,
            model_config["llm_factory"],
            model_config["llm_name"],
        )

    def _model_instance(self, model_config: dict):
        registry = _REGISTRY_MAP.get(self._model_type)
        if not registry:
            raise ValueError(f"Unknown model type: {self._model_type}")

        factory_name = model_config["llm_factory"]
        if factory_name not in registry:
            raise ValueError(
                f"Unknown {self._model_type} provider: {factory_name}. "
                f"Available: {list(registry.keys())}"
            )

        cls = registry[factory_name]
        return cls(
            api_key=model_config.get("api_key", ""),
            model_name=model_config["llm_name"],
            base_url=model_config.get("api_base"),
        )

    @property
    def model_type(self) -> str:
        return self._model_type

    @property
    def provider_name(self) -> str:
        return getattr(self._mdl, "_FACTORY_NAME", "unknown")

    # -- Chat --

    def chat(self, messages: list[dict], **kwargs) -> str:
        return self._mdl.chat(messages, **kwargs)

    async def chat_streamly(self, messages: list[dict], **kwargs):
        async for chunk in self._mdl.chat_streamly(messages, **kwargs):
            yield chunk

    # -- Embedding --

    def encode(self, texts: list[str]) -> list[list[float]]:
        return self._mdl.encode(texts)

    def encode_queries(self, queries: list[str]) -> list[list[float]]:
        if hasattr(self._mdl, "encode_queries"):
            return self._mdl.encode_queries(queries)
        return self._mdl.encode(queries)

    def similarity(self, a: list[float], b: list[float]) -> float:
        if hasattr(self._mdl, "similarity"):
            return self._mdl.similarity(a, b)
        import numpy as np

        a_np, b_np = np.array(a), np.array(b)
        return float(
            np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np) + 1e-8)
        )

    # -- Rerank --

    def rerank(self, query: str, documents: list[str], top_k: int = 10) -> list[dict]:
        return self._mdl.rerank(query, documents, top_k)

    # -- CV / Vision --

    def describe(self, image_base64: str, prompt: str = "") -> str:
        return self._mdl.describe(image_base64, prompt)

    # -- OCR --

    def extract_text(self, image_path: str) -> str:
        return self._mdl.extract_text(image_path)

    # -- TTS --

    def tts(self, text: str) -> bytes:
        return self._mdl.tts(text)

    # -- ASR --

    def transcription(self, audio_path: str) -> str:
        return self._mdl.transcription(audio_path)
