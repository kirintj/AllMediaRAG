import os
import logging
from typing import Optional
from .base import OCRProvider

logger = logging.getLogger(__name__)


class TesseractOCRProvider(OCRProvider):
    """Tesseract OCR 实现：轻量级备选方案

    延迟加载 pytesseract，适合没有 PaddleOCR 环境的场景。
    """

    def __init__(self, lang: str = "chi_sim+eng"):
        """
        Args:
            lang: Tesseract 语言代码，"chi_sim" 简体中文，"eng" 英文
        """
        self._lang = lang
        self._init_failed = False
        self._available = None

    def _check_available(self) -> bool:
        """检查 Tesseract 是否可用"""
        if self._available is not None:
            return self._available

        try:
            import pytesseract
            # 测试是否能调用 tesseract
            pytesseract.get_tesseract_version()
            self._available = True
            logger.info("Tesseract OCR available")
        except Exception as e:
            logger.warning("Tesseract OCR not available: %s", e)
            self._available = False
            self._init_failed = True

        return self._available

    def extract_text(self, image_or_pdf_path: str) -> str:
        """从图片或 PDF 提取文字"""
        if not self._validate_path(image_or_pdf_path):
            return ""

        if not self.is_available():
            return ""

        ext = os.path.splitext(image_or_pdf_path)[1].lower()

        if ext == ".pdf":
            return self._extract_from_pdf(image_or_pdf_path)

        return self._extract_from_image(image_or_pdf_path)

    def _extract_from_image(self, image_path: str) -> str:
        """从单张图片提取文字"""
        try:
            import pytesseract
            from PIL import Image

            image = Image.open(image_path)
            text = pytesseract.image_to_string(image, lang=self._lang)
            return text.strip()
        except Exception as e:
            logger.warning("Tesseract OCR failed for %s: %s", image_path, e)
            return ""

    def _extract_from_pdf(self, pdf_path: str) -> str:
        """从 PDF 提取文字"""
        try:
            from pdf2image import convert_from_path
            import tempfile

            images = convert_from_path(pdf_path, dpi=200)
            all_texts = []

            for i, image in enumerate(images):
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    image.save(tmp.name, "PNG")
                    tmp_path = tmp.name

                try:
                    page_text = self._extract_from_image(tmp_path)
                    if page_text.strip():
                        all_texts.append(f"--- 第 {i + 1} 页 ---\n{page_text}")
                finally:
                    os.unlink(tmp_path)

            return "\n\n".join(all_texts)
        except Exception as e:
            logger.warning("Tesseract PDF OCR failed for %s: %s", pdf_path, e)
            return ""

    def is_available(self) -> bool:
        """检查 Tesseract 是否可用"""
        return self._check_available()
