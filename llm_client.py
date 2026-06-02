from openai import OpenAI, APIError, RateLimitError
from typing import Generator

class LLMClient:
    """LLM 客户端：封装 MiMo API 调用"""

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

    def generate(self, prompt: str) -> str:
        """非流式生成

        Args:
            prompt: 输入提示

        Returns:
            生成的回答
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )

            content = response.choices[0].message.content
            if not content:
                return "未生成有效回答，请重试。"
            return content

        except (APIError, RateLimitError) as e:
            raise RuntimeError(f"LLM API 调用失败: {e}") from e
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e

    def stream_generate(self, prompt: str) -> Generator[str, None, None]:
        """流式生成，逐 token 返回

        Args:
            prompt: 输入提示

        Yields:
            token 字符串
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except (APIError, RateLimitError) as e:
            raise RuntimeError(f"LLM API 流式调用失败: {e}") from e
        except Exception as e:
            raise RuntimeError(f"LLM 流式调用失败: {e}") from e
