"""HTML 文档读取器

使用 BeautifulSoup 提取正文内容，去除导航、页脚、脚本和样式标签。
"""

import re
import logging

from ..base import FileReader

logger = logging.getLogger(__name__)

# 应被移除的标签（导航/脚本/样式等干扰内容）
_REMOVE_TAGS = {"nav", "footer", "script", "style", "header", "aside"}


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


class HtmlReader(FileReader):
    """HTML 文档读取器

    优先从 <article> 或 <main> 标签提取正文，若不存在则取 <body>；
    自动移除 nav、footer、script、style 等无关标签。
    """

    def supported_extensions(self) -> list[str]:
        """返回支持的文件扩展名列表"""
        return [".html", ".htm"]

    def read(self, file_path: str) -> str:
        """读取 HTML 文件并提取正文文本

        Args:
            file_path: HTML 文件路径

        Returns:
            清洗后的正文文本
        """
        try:
            from bs4 import BeautifulSoup, Tag
        except ImportError:
            raise ImportError(
                "beautifulsoup4 未安装，请执行: pip install beautifulsoup4"
            )

        try:
            html_content = _read_with_encoding_detection(file_path)
        except Exception:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # 移除无关标签
        for tag_name in _REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 优先查找正文容器
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find("body")
            or soup
        )

        text = self._extract_text_with_code(main_content)
        text = self._clean_text(text)

        logger.debug(
            "HTML 文件已提取: %s (%d 字符)", file_path, len(text)
        )
        return text

    def _extract_text_with_code(self, element) -> str:
        """提取文本，保留代码块内容

        对 <pre>、<code> 标签内容保留原样，其余取文字。

        Args:
            element: BeautifulSoup 元素

        Returns:
            提取的文本
        """
        try:
            from bs4 import Tag, NavigableString
        except ImportError:
            return element.get_text(separator="\n")

        parts: list[str] = []

        for child in element.descendants:
            if isinstance(child, NavigableString):
                # 跳过已在 code/pre 标签内部的文本（由下面的逻辑处理）
                if child.parent and child.parent.name in ("code", "pre"):
                    continue
                text = str(child).strip()
                if text:
                    parts.append(text)
            elif isinstance(child, Tag):
                if child.name in ("pre", "code"):
                    # 跳过嵌套在 pre/code 内部的子标签，避免重复输出
                    if child.parent and child.parent.name in ("pre", "code"):
                        continue
                    code_text = child.get_text()
                    if code_text.strip():
                        parts.append(f"\n```\n{code_text.strip()}\n```\n")
                elif child.name == "br":
                    parts.append("\n")
                elif child.name in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
                    parts.append("\n")

        return "\n".join(parts)

    def _clean_text(self, text: str) -> str:
        """清理多余空白

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 将连续空行压缩为最多两个换行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行尾空白
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
        return text.strip()
