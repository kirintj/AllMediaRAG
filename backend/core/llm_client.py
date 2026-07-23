"""LLMClient -- DEPRECATED, use core.models.llm_bundle.LLMBundle instead.

This module is kept for backward compatibility with existing tests and
direct imports. New code should use LLMBundle.from_config() or the
LLMBundle(tenant_id, model_type, tenant_llm_service) constructor.
"""
from openai import OpenAI, APIError, RateLimitError
from typing import Generator

from core.providers.base import LLMProvider


class LLMClient(LLMProvider):
    """LLM 客户端：封装 MiMo API 调用，支持多模态输入

    设计说明：
    - key / base_url / model 在每次请求时从 `config` 动态读取，而不是在 __init__ 里缓存字符串
    - 这样前端 Settings Drawer 里热更新的 MIMO_API_KEY / MIMO_API_BASE / MIMO_MODEL
      能立即对下一次请求生效，无需重启后端进程。
    """

    def __init__(self, api_key: str, api_base: str, model: str):
        """初始化 LLM 客户端

        注意：参数只用于第一次启动时验证"配置是否提供"。
        真正发起请求时，api_key / api_base / model 都是从 `core.config.config` 动态读取的。
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )
        self.model = model
        # 延迟导入，避免循环依赖（config 也可能 import 到这里）
        self._config = None

    # ── 关键：每次请求时重新从 config 读取 ──
    def _get_config(self):
        if self._config is None:
            from core.config import config  # noqa: WPS433
            self._config = config
        return self._config

    def _refresh_client(self):
        """根据当前 config 重建 OpenAI 客户端（每次热更新后都要调一次）"""
        cfg = self._get_config()
        api_key = cfg.MIMO_API_KEY
        api_base = cfg.MIMO_API_BASE
        model = cfg.MIMO_MODEL
        # 模型名跟随配置更新
        self.model = model
        # 替换 client 对象；旧对象没有 close，这里直接丢掉即可
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
        )
        return api_key, api_base, model

    # ── 为避免每次请求都重新 new 一个 client，
    #    我们只在"保存后"调用一次 refresh；但为了简单可靠，
    #    这里退化为：只要 api_key / api_base 与当前不一致就重建。
    def _ensure_current_client(self):
        cfg = self._get_config()
        expected_key = cfg.MIMO_API_KEY
        expected_base = cfg.MIMO_API_BASE
        expected_model = cfg.MIMO_MODEL
        if (
            self.client.api_key != expected_key
            or getattr(self.client, "base_url", None) != expected_base
            or self.model != expected_model
        ):
            self._refresh_client()
        else:
            # 保证 model 也对齐（上面 self.model = model 已在 _refresh_client 里做）
            self.model = expected_model

    def _build_content(self, prompt: str, images: list[str] | None = None):
        """构造多模态 content，无图片时返回纯文本以保持向后兼容

        Args:
            prompt: 文本提示
            images: base64 编码的图片列表，None 或空列表表示纯文本

        Returns:
            纯文本字符串或多模态 content 数组
        """
        # 无图片时直接返回文本，避免不必要的数组结构变更
        if not images:
            return prompt

        # 按 OpenAI 多模态格式组装 content 数组
        content = [{"type": "text", "text": prompt}]
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img}"}
            })
        return content

    def generate(self, prompt: str, images: list[str] | None = None) -> str:
        """非流式生成，支持多模态图片输入

        Args:
            prompt: 输入提示
            images: 可选的 base64 图片列表

        Returns:
            生成的回答
        """
        try:
            self._ensure_current_client()
            # 使用 _build_content 统一处理纯文本和多模态场景
            content = self._build_content(prompt, images)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                stream=False
            )

            result = response.choices[0].message.content
            if not result:
                return "未生成有效回答，请重试。"
            return result

        except (APIError, RateLimitError) as e:
            raise RuntimeError(f"LLM API 调用失败: {e}") from e
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e

    def stream_generate(self, prompt: str, images: list[str] | None = None) -> Generator[str, None, None]:
        """流式生成，逐 token 返回，支持多模态图片输入

        Args:
            prompt: 输入提示
            images: 可选的 base64 图片列表

        Yields:
            token 字符串
        """
        try:
            self._ensure_current_client()
            # 使用 _build_content 统一处理纯文本和多模态场景
            content = self._build_content(prompt, images)
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": content}],
                stream=True
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except (APIError, RateLimitError) as e:
            raise RuntimeError(f"LLM API 流式调用失败: {e}") from e
        except Exception as e:
            raise RuntimeError(f"LLM 流式调用失败: {e}") from e
