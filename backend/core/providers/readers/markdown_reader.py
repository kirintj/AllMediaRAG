"""Markdown 文档读取器

将 Markdown 转换为 HTML 后提取纯文本。
"""

import logging

from ..base import FileReader

logger = logging.getLogger(__name__)


def _read_with_encoding_detection(file_path: str) -> str:
    """读取文本文件，自动检测编码"""
    encodings = ['utf-8', 'utf-16', 'gbk', 'gb2312', 'latin-1']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


class MarkdownReader(FileReader):
    """Markdown 文档读取器

    使用 markdown 库将 .md 文件转换为 HTML。
    """

    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        return [".md", ".markdown"]

    def read(self, file_path: str) -> str:
        """读取 Markdown 文件并转为 HTML

        Args:
            file_path: Markdown 文件路径

        Returns:
            转换后的 HTML 内容
        """
        try:
            import markdown
        except ImportError:
            raise ImportError(
                "markdown 未安装，请执行: pip install markdown"
            )

        try:
            md_text = _read_with_encoding_detection(file_path)
        except Exception:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                md_text = f.read()

        html = markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code"],
        )

        logger.debug("Markdown 文件已转换: %s (%d 字符)", file_path, len(html))
        return html
