import os
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class VLMProvider:
    """视觉语言模型：理解图表、流程图等非纯文字内容

    复用 OpenAI 兼容 API，发送图片 base64 进行视觉理解。
    适用于：图表、流程图、架构图、截图等。
    """

    def __init__(self, api_key: str, api_base: str, model: str):
        """
        Args:
            api_key: API 密钥
            api_base: API 基础 URL
            model: VLM 模型名称，如 "gpt-4o" 或其他支持视觉的模型
        """
        self._api_key = api_key
        self._api_base = api_base
        self._model = model
        self._client = None
        self._init_failed = False

    @property
    def client(self):
        """延迟初始化 OpenAI 客户端"""
        if self._client is None and not self._init_failed:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self._api_key,
                    base_url=self._api_base
                )
                logger.info("VLM client initialized (model=%s)", self._model)
            except Exception as e:
                logger.warning("VLM client initialization failed: %s", e)
                self._init_failed = True
        return self._client

    def describe_image(self, image_path: str) -> str:
        """将图片转为文字描述，用于索引

        Args:
            image_path: 图片文件路径

        Returns:
            图片的文字描述
        """
        if not self.is_available():
            return ""

        if not os.path.exists(image_path):
            logger.warning("Image file not found: %s", image_path)
            return ""

        try:
            # 读取图片并转为 base64
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # 获取 MIME 类型
            ext = os.path.splitext(image_path)[1].lower()
            mime_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".tiff": "image/tiff",
            }
            mime_type = mime_map.get(ext, "image/png")

            # 调用 VLM API
            response = self.client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "请详细描述这张图片的内容。要求：\n"
                                        "1. 如果是图表（柱状图、折线图、饼图等），说明图表类型、标题、坐标轴含义、关键数据点和趋势\n"
                                        "2. 如果是流程图或架构图，说明各节点名称、连接关系和流程步骤\n"
                                        "3. 如果是表格，提取表头和所有数据行\n"
                                        "4. 如果是普通图片，描述主要元素、场景和文字信息\n"
                                        "请用中文输出，保持客观准确。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1500
            )

            description = response.choices[0].message.content
            logger.info("VLM described image: %s (%d chars)", os.path.basename(image_path), len(description))
            return description

        except Exception as e:
            logger.warning("VLM description failed for %s: %s", image_path, e)
            return ""

    def is_available(self) -> bool:
        """检查 VLM 是否可用"""
        return self.client is not None
