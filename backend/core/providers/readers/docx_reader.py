"""Word 文档读取器

使用 python-docx 读取 .docx 文件段落文本。
"""

import logging

from ..base import FileReader

logger = logging.getLogger(__name__)


class DocxReader(FileReader):
    """Word 文档读取器

    使用 python-docx 逐段落提取文本。
    """

    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        return [".docx"]

    def read(self, file_path: str) -> str:
        """读取 Word 文档内容

        Args:
            file_path: .docx 文件路径

        Returns:
            提取的段落文本，段落之间以换行分隔
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx 未安装，请执行: pip install python-docx"
            )

        try:
            doc = Document(file_path)
        except Exception as e:
            logger.error("无法打开 Word 文件 %s: %s", file_path, e)
            raise

        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)

        result = "\n".join(paragraphs)
        logger.debug(
            "Word 文档已读取: %s (%d 段落, %d 字符)",
            file_path,
            len(paragraphs),
            len(result),
        )
        return result
