import os
import re
import numpy as np
from bs4 import BeautifulSoup


class DocumentProcessor:
    """文档处理器：HTML 解析、语义分块"""

    def __init__(self, config):
        """初始化

        Args:
            config: 配置对象，需包含 SEMANTIC_CHUNK_PERCENTILE, SEMANTIC_CHUNK_MIN/MAX_SENTENCES
        """
        self.percentile = config.SEMANTIC_CHUNK_PERCENTILE
        self.min_sentences = config.SEMANTIC_CHUNK_MIN_SENTENCES
        self.max_sentences = config.SEMANTIC_CHUNK_MAX_SENTENCES
        self.embedding_service = None  # 延迟注入，避免循环依赖

    def set_embedding_service(self, embedding_service):
        """注入 embedding 服务（由 RAGEngine 调用）"""
        self.embedding_service = embedding_service

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

        for tag in soup.find_all(["nav", "footer", "header", "script", "style", "noscript"]):
            tag.decompose()

        for sidebar in soup.find_all(class_=re.compile(r"sidebar|sphinxsidebar|related")):
            sidebar.decompose()

        for nav in soup.find_all(class_=re.compile(r"navigation|navbar|breadcrumb")):
            nav.decompose()

        main_content = soup.find("div", class_=re.compile(r"document|body|content|main"))
        if not main_content:
            main_content = soup.find("main") or soup.find("article") or soup.body or soup

        text = self._extract_text_with_code(main_content)
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

    def _extract_code_blocks(self, text: str) -> tuple[str, dict]:
        """提取代码块，替换为占位符

        Returns:
            (处理后文本, {占位符: 原始代码块})
        """
        code_blocks = {}
        counter = [0]

        def replace_code(match):
            placeholder = f"__CODE_BLOCK_{counter[0]}__"
            code_blocks[placeholder] = match.group(0)
            counter[0] += 1
            return placeholder

        processed = re.sub(r"```[\s\S]*?```", replace_code, text)
        return processed, code_blocks

    def _restore_code_blocks(self, text: str, code_blocks: dict) -> str:
        """恢复代码块占位符"""
        for placeholder, code in code_blocks.items():
            text = text.replace(placeholder, code)
        return text

    def split_into_sentences(self, text: str) -> list[str]:
        """将文本切分为句子

        规则：
        - 按中文句号、问号、感叹号、换行符切分
        - 代码块占位符作为整体不拆分
        - 过滤空白句子
        """
        paragraphs = re.split(r"\n\n+", text)
        sentences = []

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果是代码块占位符，整体作为一个句子
            if re.match(r"^__CODE_BLOCK_\d+__$", para):
                sentences.append(para)
                continue

            # 按中文标点切分，保留标点
            parts = re.split(r"(?<=[。？！\n])", para)
            for part in parts:
                part = part.strip()
                if part:
                    sentences.append(part)

        return sentences

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """计算余弦相似度"""
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot = np.dot(a_arr, b_arr)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(dot / norm)

    def semantic_chunk(self, sentences: list[str], embeddings: list[list[float]]) -> list[list[int]]:
        """基于语义相似度切分句子

        Args:
            sentences: 句子列表
            embeddings: 句子级 embedding 列表

        Returns:
            chunk 列表，每个 chunk 是句子索引的列表
        """
        if len(sentences) <= self.min_sentences:
            return [list(range(len(sentences)))]

        # 计算相邻句子的余弦相似度
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        # 动态阈值：取百分位数
        threshold = float(np.percentile(similarities, self.percentile))

        # 低于阈值处切分
        chunks = []
        current_chunk = [0]
        for i, sim in enumerate(similarities):
            if sim < threshold:
                if len(current_chunk) >= self.min_sentences:
                    chunks.append(current_chunk)
                    current_chunk = [i + 1]
                else:
                    current_chunk.append(i + 1)
            else:
                current_chunk.append(i + 1)

            if len(current_chunk) >= self.max_sentences:
                chunks.append(current_chunk)
                current_chunk = []

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def process_document(self, html_content: str, source: str) -> tuple[list[dict], list[list[float] | None]]:
        """完整文档处理流程，返回 (chunks, chunk_embeddings)

        chunk_embeddings 与 chunks 等长等序。当语义分块可用时，
        chunk embedding 由其句子 embedding 均值池化得到，避免二次编码。
        当无 embedding 服务时，对应位置为 None。

        Returns:
            (chunks, chunk_embeddings)
        """
        text = self.parse_html(html_content)
        sections = self.split_by_headings(text)

        all_chunks = []
        all_embeddings: list[list[float] | None] = []

        for section in sections:
            section_text = section["content"].strip()
            if not section_text:
                continue

            # 提取代码块占位符
            processed_text, code_blocks = self._extract_code_blocks(section_text)

            # 句子切分
            sentences = self.split_into_sentences(processed_text)
            if not sentences:
                continue

            # 如果句子数太少，直接作为一个 chunk
            if len(sentences) <= self.min_sentences:
                chunk_text = self._restore_code_blocks(
                    "\n".join(sentences), code_blocks
                )
                heading = section["heading"] or "概述"
                chunk_text = f"[{source} - {heading}]\n{chunk_text}"
                all_chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source": source,
                        "section": heading,
                        "chunk_index": len(all_chunks),
                    }
                })
                all_embeddings.append(None)  # 需要后续编码
                continue

            # 句子级 embedding（单次编码，后续复用）
            if self.embedding_service:
                sentence_embeddings = self.embedding_service.encode(sentences)
            else:
                sentence_embeddings = None

            # 语义切分
            if sentence_embeddings:
                sentence_groups = self.semantic_chunk(sentences, sentence_embeddings)
            else:
                # 退化：每 min_sentences 个句子一组
                sentence_groups = [
                    list(range(i, min(i + self.min_sentences, len(sentences))))
                    for i in range(0, len(sentences), self.min_sentences)
                ]

            # 合并为 chunk + 均值池化得到 chunk embedding
            for group_indices in sentence_groups:
                chunk_sentences = [sentences[i] for i in group_indices]
                chunk_text = "\n".join(chunk_sentences)
                chunk_text = self._restore_code_blocks(chunk_text, code_blocks)

                if chunk_text.strip():
                    heading = section["heading"] or "概述"
                    chunk_text = f"[{source} - {heading}]\n{chunk_text}"
                    all_chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "source": source,
                            "section": heading,
                            "chunk_index": len(all_chunks),
                        }
                    })

                    # 均值池化：chunk embedding = mean(sentence embeddings)
                    if sentence_embeddings:
                        group_vecs = [sentence_embeddings[i] for i in group_indices]
                        chunk_emb = np.mean(group_vecs, axis=0)
                        # 归一化
                        norm = np.linalg.norm(chunk_emb)
                        if norm > 0:
                            chunk_emb = chunk_emb / norm
                        all_embeddings.append(chunk_emb.tolist())
                    else:
                        all_embeddings.append(None)

        return all_chunks, all_embeddings

    def process_file(self, file_path: str) -> tuple[list[dict], list[list[float] | None]]:
        """处理文件，自动识别格式

        Returns:
            (chunks, chunk_embeddings)
        """
        content = self.read_file(file_path)
        source = os.path.basename(file_path)
        return self.process_document(content, source)
