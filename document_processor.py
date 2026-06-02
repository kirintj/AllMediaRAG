from bs4 import BeautifulSoup
import re
import os

class DocumentProcessor:
    """文档处理器：HTML 解析、文本清洗、语义分块"""

    def __init__(self, chunk_size: int, chunk_overlap: int):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if chunk_size <= 0 or chunk_overlap < 0:
            raise ValueError("chunk_size must be positive and chunk_overlap non-negative")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def read_file(self, file_path: str) -> str:
        """读取文件内容，支持多种格式"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.html', '.htm']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext == '.md':
            return self._read_markdown(file_path)
        elif ext == '.pdf':
            return self._read_pdf(file_path)
        elif ext == '.docx':
            return self._read_docx(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _read_markdown(self, file_path: str) -> str:
        """读取 Markdown 文件"""
        import markdown
        with open(file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        # 转换为 HTML 后解析
        html = markdown.markdown(md_content)
        return html

    def _read_pdf(self, file_path: str) -> str:
        """读取 PDF 文件"""
        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n\n"
        return text

    def _read_docx(self, file_path: str) -> str:
        """读取 Word 文档"""
        from docx import Document
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n\n"
        return text

    def parse_html(self, html_content: str) -> str:
        """解析 HTML，提取正文内容"""
        soup = BeautifulSoup(html_content, "html.parser")

        # 移除非正文元素
        for tag in soup.find_all(["nav", "footer", "header", "script", "style", "noscript"]):
            tag.decompose()

        # 移除侧边栏
        for sidebar in soup.find_all(class_=re.compile(r"sidebar|sphinxsidebar|related")):
            sidebar.decompose()

        # 移除导航
        for nav in soup.find_all(class_=re.compile(r"navigation|navbar|breadcrumb")):
            nav.decompose()

        # 提取主内容区域
        main_content = soup.find("div", class_=re.compile(r"document|body|content|main"))
        if not main_content:
            main_content = soup.find("main") or soup.find("article") or soup.body or soup

        # 获取文本，保留代码块
        text = self._extract_text_with_code(main_content)

        # 清理多余空白
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _extract_text_with_code(self, element) -> str:
        """提取文本，保留代码块结构"""
        result = []

        for child in element.children:
            if child.name in ["pre", "code"]:
                code_text = child.get_text()
                result.append(f"```\n{code_text}\n```")
            elif child.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                level = int(child.name[1])
                title = child.get_text().strip()
                result.append(f"{'#' * level} {title}")
            elif child.string:
                text = child.string.strip()
                if text:
                    result.append(text)
            elif hasattr(child, "children"):
                sub_text = self._extract_text_with_code(child)
                if sub_text.strip():
                    result.append(sub_text)

        return "\n\n".join(result)

    def split_by_headings(self, text: str) -> list[dict]:
        """按标题层级切分章节"""
        sections = []
        current_section = {"heading": "", "content": ""}

        for line in text.split("\n"):
            if re.match(r"^#{1,6}\s", line):
                if current_section["content"].strip():
                    sections.append(current_section)
                current_section = {
                    "heading": line.lstrip("#").strip(),
                    "content": ""
                }
            else:
                current_section["content"] += line + "\n"

        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    def split_by_paragraph(self, section_content: str) -> list[str]:
        """章节内按段落切分"""
        paragraphs = section_content.split("\n\n")
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if current_chunk and len(current_chunk) + len(para) > self.chunk_size:
                chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + "\n\n" + para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [section_content.strip()]

    def process_document(self, html_content: str, source: str) -> list[dict]:
        """完整文档处理流程，返回带元数据的 chunks"""
        text = self.parse_html(html_content)
        sections = self.split_by_headings(text)

        all_chunks = []
        for section in sections:
            if len(section["content"]) > self.chunk_size:
                chunks = self.split_by_paragraph(section["content"])
            else:
                chunks = [section["content"].strip()]

            for i, chunk in enumerate(chunks):
                if chunk:
                    all_chunks.append({
                        "text": chunk,
                        "metadata": {
                            "source": source,
                            "section": section["heading"] or "概述",
                            "chunk_index": i
                        }
                    })

        return all_chunks

    def process_file(self, file_path: str) -> list[dict]:
        """处理文件，自动识别格式"""
        content = self.read_file(file_path)
        source = os.path.basename(file_path)
        return self.process_document(content, source)
