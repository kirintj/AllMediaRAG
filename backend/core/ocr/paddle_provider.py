import os
import logging
from typing import Optional
from .base import OCRProvider

logger = logging.getLogger(__name__)


class PaddleOCRProvider(OCRProvider):
    """PaddleOCR 实现：支持中文和英文 OCR

    延迟加载 PaddleOCR，避免启动时拉起重量级依赖。
    支持图片文件和扫描件 PDF。
    """

    def __init__(self, lang: str = "ch", use_gpu: bool = False):
        """
        Args:
            lang: 语言，"ch" 中文，"en" 英文
            use_gpu: 是否使用 GPU（PaddleOCR 3.x 自动检测，此参数保留兼容）
        """
        self._ocr = None
        self._lang = lang
        self._use_gpu = use_gpu
        self._init_failed = False

    @property
    def ocr(self):
        """延迟初始化 PaddleOCR"""
        if self._ocr is None and not self._init_failed:
            try:
                from paddleocr import PaddleOCR
                # PaddleOCR 3.x 使用 device 参数
                device = "gpu" if self._use_gpu else "cpu"
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self._lang,
                    device=device
                )
                logger.info("PaddleOCR initialized (lang=%s, device=%s)", self._lang, device)
            except Exception as e:
                logger.warning("PaddleOCR initialization failed: %s", e)
                self._init_failed = True
        return self._ocr

    def extract_text(self, image_or_pdf_path: str) -> str:
        """从图片或 PDF 提取文字

        Args:
            image_or_pdf_path: 图片或 PDF 文件路径

        Returns:
            提取的文字内容
        """
        if not self._validate_path(image_or_pdf_path):
            logger.warning("File not found: %s", image_or_pdf_path)
            return ""

        if not self.is_available():
            logger.warning("PaddleOCR not available")
            return ""

        ext = os.path.splitext(image_or_pdf_path)[1].lower()

        # PDF 文件：转图片后逐页 OCR
        if ext == ".pdf":
            return self._extract_from_pdf(image_or_pdf_path)

        # 图片文件：直接 OCR
        return self._extract_from_image(image_or_pdf_path)

    def _extract_from_image(self, image_path: str) -> str:
        """从单张图片提取文字"""
        try:
            # 尝试 PaddleOCR 3.x 的 ocr 方法（兼容旧 API）
            result = self.ocr.ocr(image_path)
            if not result or not result[0]:
                return ""

            texts = []
            for line in result[0]:
                if line and len(line) >= 2:
                    # (bbox, (text, confidence)) 格式
                    text = line[1][0]
                    texts.append(text)

            return "\n".join(texts)
        except Exception as e:
            logger.warning("OCR extraction failed for %s: %s", image_path, e)
            return ""

    def _extract_from_pdf(self, pdf_path: str) -> str:
        """从 PDF 提取文字（每页转图片后 OCR）"""
        try:
            from pdf2image import convert_from_path
            from PIL import Image
            import tempfile

            # 将 PDF 每页转为图片
            images = convert_from_path(pdf_path, dpi=200)
            all_texts = []

            for i, image in enumerate(images):
                # 保存为临时文件
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
            logger.warning("PDF OCR extraction failed for %s: %s", pdf_path, e)
            return ""

    def is_available(self) -> bool:
        """检查 PaddleOCR 是否可用"""
        return self.ocr is not None
