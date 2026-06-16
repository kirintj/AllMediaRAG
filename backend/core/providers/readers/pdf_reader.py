"""PDF 文档读取器

使用 PyPDF2 提取文本，对扫描件 PDF 自动降级到 OCR。
"""

import logging

from ..base import FileReader

logger = logging.getLogger(__name__)

# 扫描件判定阈值：平均每页字符数低于此值视为扫描件
_SCANNED_THRESHOLD = 50


class PDFReader(FileReader):
    """PDF 文档读取器

    优先使用 PyPDF2 提取文字；当检测到扫描件（平均字符数 < 50/页）
    且提供了 ocr_provider 时，自动降级到 OCR 提取。
    """

    def __init__(self, ocr_provider=None):
        """
        Args:
            ocr_provider: OCRProvider 实例，用于扫描件文字提取（可选）
        """
        self._ocr_provider = ocr_provider

    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        return [".pdf"]

    def read(self, file_path: str) -> str:
        """读取 PDF 文件内容

        Args:
            file_path: PDF 文件路径

        Returns:
            提取的文本内容

        Raises:
            ImportError: 未安装 PyPDF2
            FileNotFoundError: 文件不存在
        """
        try:
            from PyPDF2 import PdfReader as PyPdfReader
        except ImportError:
            raise ImportError(
                "PyPDF2 未安装，请执行: pip install PyPDF2"
            )

        try:
            reader = PyPdfReader(file_path)
        except Exception as e:
            logger.error("无法打开 PDF 文件 %s: %s", file_path, e)
            raise

        pages = reader.pages
        page_count = len(pages)

        if page_count == 0:
            logger.warning("PDF 文件无页面: %s", file_path)
            return ""

        # 逐页提取文本
        texts: list[str] = []
        for page in pages:
            text = page.extract_text() or ""
            texts.append(text)

        full_text = "\n".join(texts)
        avg_chars = len(full_text) / page_count

        # 检测扫描件：文本极少且有 OCR 支持时降级
        if avg_chars < _SCANNED_THRESHOLD and self._ocr_provider is not None:
            logger.info(
                "PDF 检测为扫描件（平均 %.1f 字/页），启用 OCR: %s",
                avg_chars,
                file_path,
            )
            try:
                ocr_text = self._ocr_provider.extract_text(file_path)
                if ocr_text.strip():
                    return ocr_text
                logger.warning("OCR 未提取到文字，回退到 PyPDF2 结果")
            except Exception as e:
                logger.warning("OCR 提取失败，回退到 PyPDF2 结果: %s", e)

        return full_text
