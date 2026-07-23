"""TTS providers -- 文字转语音模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 TtsModel 注册表。

每个 provider 实现 ``tts(text: str) -> bytes`` 接口，返回音频二进制数据。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── OpenAI TTS ───────────────────────────────────────────────────────────────

class OpenAITTS:
    """OpenAI Text-to-Speech API (tts-1 / tts-1-hd)"""

    _FACTORY_NAME = "OpenAI"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url
        self._voice = kwargs.get("voice", "alloy")

    def tts(self, text: str) -> bytes:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        response = client.audio.speech.create(
            model=self._model,
            voice=self._voice,
            input=text,
        )
        return response.content


# ── Tongyi-Qianwen / DashScope CosyVoice ────────────────────────────────────

class TongyiQianwenTTS:
    """阿里通义千问语音合成 (DashScope CosyVoice API)"""

    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://dashscope.aliyuncs.com/api/v1"
        self._voice = kwargs.get("voice", "longxiaochun")

    def tts(self, text: str) -> bytes:
        import requests

        url = f"{self._base_url}/services/aigc/text2audio/generation"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": {"text": text},
            "parameters": {
                "voice": self._voice,
            },
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.content


# ── SiliconFlow TTS ──────────────────────────────────────────────────────────

class SiliconFlowTTS:
    """SiliconFlow TTS API"""

    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://api.siliconflow.cn/v1"
        self._voice = kwargs.get("voice", "alloy")

    def tts(self, text: str) -> bytes:
        import requests

        url = f"{self._base_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": text,
            "voice": self._voice,
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return resp.content
