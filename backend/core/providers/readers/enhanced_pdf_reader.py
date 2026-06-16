"""增强型 PDF 解析器

支持文本、嵌入图片（OCR+VLM）和表格（pdfplumber）多模态提取。
比基础 PDFReader 更适合包含图表、扫描页的复杂文档。
"""

import logging
import os
import tempfile
from typing import Optional

from ..base import FileReader

logger = logging.getLogger(__name__)


class EnhancedPDFReader(FileReader):
    """增强型 PDF 解析器，支持文本、图片、表格多模态提取

    功能:
    - 文本提取：使用 PyMuPDF（fitz），质量优于 PyPDF2
    - 扫描页检测：平均字符数 < 50/页 时整页 OCR
    - 图片提取：提取嵌入图片，过滤装饰图（< 100x100），
      对每张图片执行 OCR + VLM 描述
    - 表格提取：使用 pdfplumber 提取表格并转为 Markdown 格式
    """

    MIN_IMAGE_SIZE = 100  # 过滤装饰性小图片的边长阈值（像素）
    SCANNED_THRESHOLD = 50  # 平均字符数/页 < 此值 视为扫描件

    def __init__(self, ocr_provider=None, vlm_provider=None):
        """
        Args:
            ocr_provider: OCRProvider 实例，用于图片文字提取（可选）
            vlm_provider: VLMProvider 实例，用于图片内容描述（可选）
        """
        self.ocr = ocr_provider
        self.vlm = vlm_provider

    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        return [".pdf"]

    def read(self, file_path: str) -> str:
        """提取 PDF 全部内容：文本 + 图片描述 + 表格

        Args:
            file_path: PDF 文件路径

        Returns:
            提取的全部文本内容

        Raises:
            FileNotFoundError: 文件不存在
        """
        if not os.path.exists(file_path):
            logger.warning("PDF 文件不存在: %s", file_path)
            return ""

        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "PyMuPDF 未安装，请执行: pip install PyMuPDF"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            doc = fitz.open(file_path)
            page_contents: list[str] = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                parts: list[str] = []

                # 1. 文本提取（PyMuPDF，优于 PyPDF2）
                text = page.get_text("text").strip()

                if len(text) < self.SCANNED_THRESHOLD:
                    # 扫描页 → 整页 OCR
                    scanned = self._process_scanned_page(doc, page_num, temp_dir)
                    if scanned:
                        parts.append(scanned)
                else:
                    parts.append(text)

                # 2. 嵌入图片提取
                image_descs = self._extract_page_images(doc, page, page_num, temp_dir)
                parts.extend(image_descs)

                # 3. 表格提取
                tables = self._extract_page_tables(file_path, page_num)
                parts.extend(tables)

                page_content = "\n\n".join(p for p in parts if p.strip())
                if page_content.strip():
                    page_contents.append(page_content)

            doc.close()

        return "\n\n".join(page_contents)

    def _extract_page_images(
        self, doc, page, page_num: int, temp_dir: str
    ) -> list[str]:
        """提取页面中的嵌入图片，执行 OCR 和 VLM 描述

        Args:
            doc: fitz.Document 对象
            page: fitz.Page 对象
            page_num: 页码（0-indexed）
            temp_dir: 临时目录路径

        Returns:
            图片描述字符串列表
        """
        try:
            import fitz  # noqa: F811
        except ImportError:
            return []

        results: list[str] = []
        image_list = page.get_images(full=True)

        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                img_data = doc.extract_image(xref)
                if not img_data or not img_data.get("image"):
                    continue

                width = img_data.get("width", 0)
                height = img_data.get("height", 0)

                # 过滤装饰性小图片
                if width < self.MIN_IMAGE_SIZE or height < self.MIN_IMAGE_SIZE:
                    logger.debug(
                        "跳过小图片 %dx%d (xref=%d, 第%d页)",
                        width, height, xref, page_num + 1,
                    )
                    continue

                # 保存图片到临时文件
                ext = img_data.get("ext", "png")
                img_path = os.path.join(
                    temp_dir, f"page{page_num}_img{img_index}.{ext}"
                )
                with open(img_path, "wb") as f:
                    f.write(img_data["image"])

                page_display = page_num + 1  # 1-indexed 用于显示

                # OCR 提取图片文字
                if self.ocr is not None:
                    try:
                        ocr_text = self.ocr.extract_text(img_path)
                        if ocr_text and ocr_text.strip():
                            results.append(
                                f"[图片OCR - 第{page_display}页]\n{ocr_text.strip()}"
                            )
                    except Exception as e:
                        logger.warning(
                            "图片 OCR 失败 (第%d页, xref=%d): %s",
                            page_display, xref, e,
                        )

                # VLM 图片内容描述
                if self.vlm is not None:
                    try:
                        description = self.vlm.describe_image(img_path)
                        if description and description.strip():
                            results.append(
                                f"[图片描述 - 第{page_display}页]\n{description.strip()}"
                            )
                    except Exception as e:
                        logger.warning(
                            "图片 VLM 描述失败 (第%d页, xref=%d): %s",
                            page_display, xref, e,
                        )

            except Exception as e:
                logger.warning(
                    "提取图片失败 (xref=%d, 第%d页): %s",
                    xref, page_num + 1, e,
                )

        return results

    def _extract_page_tables(self, pdf_path: str, page_num: int) -> list[str]:
        """使用 pdfplumber 提取页面表格，转为 Markdown 格式

        Args:
            pdf_path: PDF 文件路径
            page_num: 页码（0-indexed）

        Returns:
            Markdown 格式的表格字符串列表
        """
        try:
            import pdfplumber
        except ImportError:
            logger.debug("pdfplumber 未安装，跳过表格提取")
            return []

        results: list[str] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num >= len(pdf.pages):
                    return []
                page = pdf.pages[page_num]
                tables = page.extract_tables()

                for table in tables:
                    if not table or len(table) < 1:
                        continue

                    md_table = self._table_to_markdown(table)
                    if md_table:
                        page_display = page_num + 1
                        results.append(
                            f"[表格 - 第{page_display}页]\n{md_table}"
                        )
        except Exception as e:
            logger.warning(
                "表格提取失败 (第%d页): %s", page_num + 1, e,
            )

        return results

    def _process_scanned_page(
        self, doc, page_num: int, temp_dir: str
    ) -> Optional[str]:
        """处理扫描页：将页面渲染为图片后执行 OCR

        Args:
            doc: fitz.Document 对象
            page_num: 页码（0-indexed）
            temp_dir: 临时目录路径

        Returns:
            OCR 提取的文字，无结果时返回空字符串
        """
        if self.ocr is None:
            logger.debug(
                "扫描页无 OCR provider，跳过: 第%d页", page_num + 1,
            )
            return ""

        try:
            import fitz  # noqa: F811

            page = doc[page_num]
            # 以 2x 分辨率渲染页面
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(temp_dir, f"scanned_page{page_num}.png")
            pix.save(img_path)

            ocr_text = self.ocr.extract_text(img_path)
            if ocr_text and ocr_text.strip():
                logger.info(
                    "扫描页 OCR 成功: 第%d页 (%d 字符)",
                    page_num + 1, len(ocr_text),
                )
                return ocr_text.strip()
            else:
                logger.info("扫描页 OCR 无结果: 第%d页", page_num + 1)
                return ""
        except Exception as e:
            logger.warning(
                "扫描页处理失败 (第%d页): %s", page_num + 1, e,
            )
            return ""

    @staticmethod
    def _table_to_markdown(table: list[list]) -> str:
        """将二维列表转换为 Markdown 表格格式

        Args:
            table: 二维列表，第一行为表头

        Returns:
            Markdown 格式的表格字符串；空输入返回空字符串
        """
        if not table or not table[0]:
            return ""

        # 清洗单元格：None → 空串，去除首尾空白
        def clean(cell):
            if cell is None:
                return ""
            return str(cell).replace("\n", " ").strip()

        headers = [clean(c) for c in table[0]]
        header_line = "| " + " | ".join(headers) + " |"
        separator = "| " + " | ".join(["---"] * len(headers)) + " |"

        rows = []
        for row in table[1:]:
            cells = [clean(c) for c in row]
            # 补齐列数
            while len(cells) < len(headers):
                cells.append("")
            rows.append("| " + " | ".join(cells[:len(headers)]) + " |")

        return "\n".join([header_line, separator] + rows)
