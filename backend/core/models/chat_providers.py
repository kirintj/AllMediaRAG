"""Chat providers -- 对话模型实现

所有 provider 类必须拥有 _FACTORY_NAME 属性，
__init__.py 的自动发现机制会将其注册到 ChatModel 注册表。
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── OpenAI ────────────────────────────────────────────────────────────────────

class OpenAIChat:
    """OpenAI Chat Completions API"""

    _FACTORY_NAME = "OpenAI"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def chat(self, messages: list[dict], **kwargs) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = client.chat.completions.create(
            model=self._model, messages=messages, **kwargs
        )
        return resp.choices[0].message.content

    async def chat_streamly(self, messages: list[dict], **kwargs):
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        stream = await client.chat.completions.create(
            model=self._model, messages=messages, stream=True, **kwargs
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ── Ollama (OpenAI-compatible at /v1) ─────────────────────────────────────────

class OllamaChat:
    """Ollama 本地模型，通过 OpenAI-compatible /v1 端点调用"""

    _FACTORY_NAME = "Ollama"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key or "ollama"
        self._model = model_name
        self._base_url = base_url or "http://localhost:11434/v1"

    def chat(self, messages: list[dict], **kwargs) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = client.chat.completions.create(
            model=self._model, messages=messages, **kwargs
        )
        return resp.choices[0].message.content

    async def chat_streamly(self, messages: list[dict], **kwargs):
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        stream = await client.chat.completions.create(
            model=self._model, messages=messages, stream=True, **kwargs
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ── DeepSeek (OpenAI-compatible) ──────────────────────────────────────────────

class DeepSeekChat:
    """DeepSeek API，兼容 OpenAI 接口"""

    _FACTORY_NAME = "DeepSeek"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url or "https://api.deepseek.com/v1"

    def chat(self, messages: list[dict], **kwargs) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        resp = client.chat.completions.create(
            model=self._model, messages=messages, **kwargs
        )
        return resp.choices[0].message.content

    async def chat_streamly(self, messages: list[dict], **kwargs):
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)
        stream = await client.chat.completions.create(
            model=self._model, messages=messages, stream=True, **kwargs
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ── Azure OpenAI ──────────────────────────────────────────────────────────────

class AzureOpenAIChat:
    """Azure OpenAI Service"""

    _FACTORY_NAME = "Azure-OpenAI"

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url  # Azure endpoint URL

    def chat(self, messages: list[dict], **kwargs) -> str:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=self._api_key,
            azure_endpoint=self._base_url,
            api_version="2024-02-01",
        )
        resp = client.chat.completions.create(
            model=self._model, messages=messages, **kwargs
        )
        return resp.choices[0].message.content

    async def chat_streamly(self, messages: list[dict], **kwargs):
        from openai import AsyncAzureOpenAI

        client = AsyncAzureOpenAI(
            api_key=self._api_key,
            azure_endpoint=self._base_url,
            api_version="2024-02-01",
        )
        stream = await client.chat.completions.create(
            model=self._model, messages=messages, stream=True, **kwargs
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ── LiteLLM (统一多厂商) ─────────────────────────────────────────────────────

class LiteLLMChat:
    """通过 litellm 调用多种 LLM 厂商

    _FACTORY_NAME 为列表，注册时会为每个名称创建一条记录。
    """

    _FACTORY_NAME = [
        "Tongyi-Qianwen",
        "Bedrock",
        "Moonshot",
        "xAI",
        "DeepInfra",
        "Groq",
        "Cohere",
        "Gemini",
        "NVIDIA",
        "TogetherAI",
        "Anthropic",
        "StepFun",
        "OpenRouter",
        "SILICONFLOW",
    ]

    def __init__(self, api_key: str, model_name: str, base_url: str = None, **kwargs):
        self._api_key = api_key
        self._model = model_name
        self._base_url = base_url

    def chat(self, messages: list[dict], **kwargs) -> str:
        import litellm

        resp = litellm.completion(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            messages=messages,
            **kwargs,
        )
        return resp.choices[0].message.content

    async def chat_streamly(self, messages: list[dict], **kwargs):
        import litellm

        response = await litellm.acompletion(
            model=self._model,
            api_key=self._api_key,
            base_url=self._base_url,
            messages=messages,
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
