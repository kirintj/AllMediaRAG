"""CV providers -- 视觉理解模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 CvModel 注册表。

每个 provider 实现 ``describe(image_base64, prompt="") -> str`` 接口。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── OpenAI (GPT-4o Vision) ───────────────────────────────────────────────────

class OpenAICV:
    """OpenAI Vision API (gpt-4o, gpt-4o-mini 等)"""

    _FACTORY_NAME = "OpenAI"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def describe(self, image_base64: str, prompt: str = "") -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ],
            }],
        )
        return response.choices[0].message.content


# ── Gemini (via litellm) ─────────────────────────────────────────────────────

class GeminiCV:
    """Google Gemini Vision，通过 litellm 调用"""

    _FACTORY_NAME = "Gemini"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def describe(self, image_base64: str, prompt: str = "") -> str:
        import litellm

        response = litellm.completion(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe this image in detail."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }],
        )
        return response.choices[0].message.content


# ── Tongyi-Qianwen / Qwen-VL (OpenAI-compatible) ────────────────────────────

class TongyiQianwenCV:
    """阿里通义千问视觉理解 (Qwen-VL)，通过 DashScope OpenAI-compatible 接口调用"""

    _FACTORY_NAME = "Tongyi-Qianwen"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def describe(self, image_base64: str, prompt: str = "") -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ],
            }],
        )
        return response.choices[0].message.content


# ── Anthropic (Claude Vision via litellm) ────────────────────────────────────

class AnthropicCV:
    """Anthropic Claude Vision，通过 litellm 调用"""

    _FACTORY_NAME = "Anthropic"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def describe(self, image_base64: str, prompt: str = "") -> str:
        import litellm

        response = litellm.completion(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe this image in detail."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }],
        )
        return response.choices[0].message.content


# ── Ollama (local vision models, OpenAI-compatible) ──────────────────────────

class OllamaCV:
    """Ollama 本地视觉模型 (llava 等)，通过 OpenAI-compatible /v1 端点调用"""

    _FACTORY_NAME = "Ollama"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key or "ollama"
        self._model = model_name
        self._base_url = base_url or "http://localhost:11434/v1"

    def describe(self, image_base64: str, prompt: str = "") -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt or "Describe this image in detail."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ],
            }],
        )
        return response.choices[0].message.content
