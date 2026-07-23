"""音频文件读取器（ASR 转文字）"""
from __future__ import annotations
import os
import logging

logger = logging.getLogger(__name__)


class AudioReader:
    """读取音频文件，通过 ASR 模型转为文字

    需要 LLMBundle(asr) 在 init 时注入。
    """

    def __init__(self, asr_bundle=None):
        self._asr = asr_bundle

    def set_asr_bundle(self, asr_bundle):
        self._asr = asr_bundle

    def read(self, file_path: str) -> str:
        if not self._asr:
            logger.warning("AudioReader: ASR bundle not configured, skipping %s", file_path)
            return ""
        try:
            return self._asr.transcription(file_path)
        except Exception as e:
            logger.error("AudioReader: ASR failed for %s: %s", file_path, e)
            return ""

    def supported_extensions(self) -> list[str]:
        return [".mp3", ".wav", ".m4a"]
