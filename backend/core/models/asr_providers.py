"""ASR providers -- 语音转文字模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 AsrModel 注册表。

每个 provider 实现 ``transcription(audio_path: str) -> str`` 接口。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── OpenAI Whisper ───────────────────────────────────────────────────────────

class OpenAIASR:
    """OpenAI Whisper API (audio.transcriptions)"""

    _FACTORY_NAME = "OpenAI"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def transcription(self, audio_path: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model=self._model,
                file=f,
            )
        return response.text


# ── Tongyi-Qianwen / DashScope Paraformer ────────────────────────────────────

class TongyiQianwenASR:
    """阿里通义千问语音识别 (DashScope Paraformer API)"""

    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://dashscope.aliyuncs.com/api/v1"

    def transcription(self, audio_path: str) -> str:
        import requests

        url = f"{self._base_url}/services/audio/asr/transcription"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # First, submit the transcription task with a file URL or local file
        with open(audio_path, "rb") as f:
            files = {"file": f}
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files=files,
                data={"model": self._model},
                timeout=300,
            )
        resp.raise_for_status()
        data = resp.json()

        # DashScope may return results directly or via a task polling mechanism
        output = data.get("output", {})
        results = output.get("results", [])
        if results:
            texts = [r.get("transcription", "") for r in results]
            return "\n".join(texts)

        # Fallback: check for direct text result
        return data.get("output", {}).get("text", "")


# ── SiliconFlow ASR ──────────────────────────────────────────────────────────

class SiliconFlowASR:
    """SiliconFlow ASR API (OpenAI-compatible whisper endpoint)"""

    _FACTORY_NAME = "SILICONFLOW"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://api.siliconflow.cn/v1"

    def transcription(self, audio_path: str) -> str:
        import requests

        url = f"{self._base_url}/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
        }
        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {"model": self._model}
            resp = requests.post(url, headers=headers, files=files, data=data, timeout=300)
        resp.raise_for_status()
        return resp.json().get("text", "")


# ── FunASR (本地) ────────────────────────────────────────────────────────────

class FunASRProvider:
    """本地 FunASR 语音识别 (ModelScope FunASR)"""

    _FACTORY_NAME = "FunASR"

    def __init__(self, api_key: str = "", model_name: str = "", base_url: str = None, **kwargs):
        self._model = model_name or "paraformer-zh"
        self._vad_model = kwargs.get("vad_model", "fsmn-vad")
        self._punc_model = kwargs.get("punc_model", "ct-punc")

    def transcription(self, audio_path: str) -> str:
        from funasr import AutoModel

        model = AutoModel(
            model=self._model,
            vad_model=self._vad_model,
            punc_model=self._punc_model,
        )
        result = model.generate(input=audio_path)
        if result and isinstance(result, list):
            texts = [item.get("text", "") for item in result if isinstance(item, dict)]
            return "".join(texts)
        return ""
