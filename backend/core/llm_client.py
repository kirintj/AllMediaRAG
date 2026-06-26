from openai import OpenAI, APIError, RateLimitError
from typing import Generator

from core.providers.base import LLMProvider


class LLMClient(LLMProvider):
    """LLM 客户端：封装 MiMo API 调用，支持多模态输入"""

    def __init__(self, api_key: str, api_base: str, model: str):
        """初始化 LLM 客户端

        Args:
            api_key: API Key
            api_base: API 基础地址
            model: 模型名称
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )
        self.model = model

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
