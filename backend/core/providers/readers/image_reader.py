"""图片读取器

使用 OCR 提取图片中的文字，可选使用 VLM 生成图片内容描述。
"""

import logging
from typing import Optional

from ..base import FileReader

logger = logging.getLogger(__name__)


class ImageReader(FileReader):
    """图片文档读取器

    必须提供 ocr_provider 以提取图片中的文字；
    可选提供 vlm_provider 获取图片的自然语言描述。
    """

    def __init__(self, ocr_provider=None, vlm_provider=None):
        """
        Args:
            ocr_provider: OCRProvider 实例，用于图片文字提取
            vlm_provider: VLMProvider 实例，用于图片内容描述（可选）
        """
        self._ocr_provider = ocr_provider
        self._vlm_provider = vlm_provider

    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        return [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]

    def read(self, file_path: str) -> str:
        """读取图片内容

        同时执行 OCR 文字提取和 VLM 内容描述（如可用），
        将两者合并返回。

        Args:
            file_path: 图片文件路径

        Returns:
            图片的文字内容（OCR + VLM 描述）
        """
        import os

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"图片文件不存在: {file_path}")

        parts: list[str] = []

        # OCR 文字提取
        if self._ocr_provider is not None:
            try:
                ocr_text = self._ocr_provider.extract_text(file_path)
                if ocr_text and ocr_text.strip():
                    parts.append(f"[OCR 文字内容]\n{ocr_text.strip()}")
                    logger.debug(
                        "图片 OCR 提取: %s (%d 字符)",
                        file_path,
                        len(ocr_text),
                    )
                else:
                    logger.info("图片 OCR 未提取到文字: %s", file_path)
            except Exception as e:
                logger.warning("图片 OCR 提取失败 %s: %s", file_path, e)
        else:
            logger.debug("未配置 OCR provider，跳过文字提取: %s", file_path)

        # VLM 内容描述
        if self._vlm_provider is not None:
            try:
                description = self._vlm_provider.describe_image(file_path)
                if description and description.strip():
                    parts.append(f"[图片内容描述]\n{description.strip()}")
                    logger.debug(
                        "图片 VLM 描述: %s (%d 字符)",
                        file_path,
                        len(description),
                    )
                else:
                    logger.info("图片 VLM 未生成描述: %s", file_path)
            except Exception as e:
                logger.warning("图片 VLM 描述失败 %s: %s", file_path, e)
        else:
            logger.debug("未配置 VLM provider，跳过图片描述: %s", file_path)

        if not parts:
            logger.warning("图片无任何提取结果: %s", file_path)
            return ""

        return "\n\n".join(parts)
