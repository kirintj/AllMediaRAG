import os
import re
import numpy as np
from bs4 import BeautifulSoup


class DocumentProcessor:
    """文档处理器：HTML 解析、语义分块、OCR 支持"""

    # 支持的图片格式
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}

    def __init__(self, config, ocr_provider=None, vlm_provider=None,
                 file_reader_registry=None, chunking_strategy=None,
                 image_pipeline=None, image_store=None):
        """初始化

        Args:
            config: 配置对象，需包含 SEMANTIC_CHUNK_PERCENTILE, SEMANTIC_CHUNK_MIN/MAX_SENTENCES
            ocr_provider: OCR 提供者（可选），用于扫描件 PDF 和图片
            vlm_provider: VLM 提供者（可选），用于图表理解
            file_reader_registry: 文件读取器注册表（可选），格式为 {ext: reader}
            chunking_strategy: 切分策略实例（可选），实现 ChunkingStrategy 接口
            image_pipeline: VLM 图片处理管线（可选），用于图片/PDF 的新处理流程
            image_store: 图片存储服务（可选），配合 image_pipeline 保存图片区域
        """
        self.percentile = config.SEMANTIC_CHUNK_PERCENTILE
        self.min_sentences = config.SEMANTIC_CHUNK_MIN_SENTENCES
        self.max_sentences = config.SEMANTIC_CHUNK_MAX_SENTENCES
        self.embedding_service = None  # 延迟注入，避免循环依赖
        self.ocr_provider = ocr_provider
        self.vlm_provider = vlm_provider
        self.file_reader_registry = file_reader_registry or {}
        self.chunking_strategy = chunking_strategy
        self._image_pipeline = image_pipeline
        self._image_store = image_store

    def set_embedding_service(self, embedding_service):
        """注入 embedding 服务（由 RAGEngine 调用）"""
        self.embedding_service = embedding_service
        # 同步注入到切分策略（语义切分需要 embedding 服务）
        if self.chunking_strategy and hasattr(self.chunking_strategy, 'set_embedding_service'):
            self.chunking_strategy.set_embedding_service(embedding_service)

    def read_file(self, file_path: str) -> str:
        """读取文件内容，支持多种格式"""
        import logging
        logger = logging.getLogger(__name__)

        ext = os.path.splitext(file_path)[1].lower()

        # Try registry first
        if ext in self.file_reader_registry:
            reader = self.file_reader_registry[ext]
            if reader.can_handle(file_path):
                return reader.read(file_path)

        # Fallback to hardcoded logic (backward compatible)
        if ext in ['.html', '.htm']:
            return self._read_text_file(file_path)
        elif ext == '.txt':
            return self._read_text_file(file_path)
        elif ext == '.md':
            return self._read_markdown(file_path)
        elif ext == '.pdf':
            return self._read_pdf(file_path)
        elif ext == '.docx':
            return self._read_docx(file_path)
        elif ext in self.IMAGE_EXTENSIONS:
            return self._read_image(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    @staticmethod
    def _read_text_file(file_path: str) -> str:
        """读取纯文本文件，自动检测编码

        按 UTF-8 → UTF-16 → GBK → Latin-1 顺序尝试。
        """
        encodings = ['utf-8', 'utf-16', 'gbk', 'gb2312', 'latin-1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        # 最终兜底：忽略无法解码的字节
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _read_markdown(self, file_path: str) -> str:
        """读取 Markdown 文件"""
        import markdown
        content = self._read_text_file(file_path)
        html = markdown.markdown(content)
        return html

    def _read_pdf(self, file_path: str) -> str:
        """读取 PDF 文件，支持 OCR 降级"""
        import logging
        logger = logging.getLogger(__name__)

        from PyPDF2 import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        # 检查是否为扫描件 PDF（文本量过少）
        if self._is_scanned_pdf(text, len(reader.pages)):
            logger.info("Scanned PDF detected, attempting OCR: %s", file_path)
            ocr_text = self._read_pdf_with_ocr(file_path)
            if ocr_text.strip():
                return ocr_text
            logger.warning("OCR extraction failed, falling back to empty text")

        return text

    def _is_scanned_pdf(self, text: str, page_count: int) -> bool:
        """判断是否为扫描件 PDF

        判断标准：平均每页文本量 < 50 字符
        """
        if page_count == 0:
            return False
        avg_chars_per_page = len(text.strip()) / page_count
        return avg_chars_per_page < 50

    def _read_pdf_with_ocr(self, file_path: str) -> str:
        """使用 OCR 提取扫描件 PDF 的文字"""
        import logging
        logger = logging.getLogger(__name__)

        if not self.ocr_provider or not self.ocr_provider.is_available():
            logger.warning("OCR provider not available")
            return ""

        try:
            return self.ocr_provider.extract_text(file_path)
        except Exception as e:
            logger.warning("OCR extraction failed: %s", e)
            return ""

    def _read_image(self, file_path: str) -> str:
        """读取图片文件，使用 OCR 提取文字"""
        import logging
        logger = logging.getLogger(__name__)

        if not self.ocr_provider or not self.ocr_provider.is_available():
            logger.warning("OCR provider not available for image: %s", file_path)
            return ""

        try:
            ocr_text = self.ocr_provider.extract_text(file_path)

            # 如果 VLM 可用，添加图片描述
            if self.vlm_provider and self.vlm_provider.is_available():
                vlm_desc = self.vlm_provider.describe_image(file_path)
                if vlm_desc.strip():
                    return f"{ocr_text}\n\n[图片描述]\n{vlm_desc}"

            return ocr_text
        except Exception as e:
            logger.warning("Image OCR failed: %s", e)
            return ""

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

            # 使用切分策略（如果已配置）
            if self.chunking_strategy:
                heading = section["heading"] or "概述"
                metadata = {"source": source, "section": heading}
                strategy_chunks = self.chunking_strategy.split(processed_text, metadata)
                for chunk_data in strategy_chunks:
                    chunk_text = self._restore_code_blocks(chunk_data["content"], code_blocks)
                    if chunk_text.strip():
                        chunk_meta = chunk_data["metadata"]
                        chunk_text = f"[{source} - {chunk_meta.get('section', heading)}]\n{chunk_text}"
                        all_chunks.append({
                            "text": chunk_text,
                            "metadata": {
                                "source": source,
                                "section": chunk_meta.get("section", heading),
                                "chunk_index": len(all_chunks),
                            }
                        })
                        all_embeddings.append(None)  # 需要后续编码
                continue

            # 回退：使用内联语义切分（向后兼容）
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

    def _process_with_vlm_extractor(self, file_path: str) -> tuple[list[dict], list[list[float] | None]]:
        """使用 VLMExtractor + RegionChunker 处理图片/PDF"""
        from .chunking.region_chunker import RegionChunker

        # VLM 提取图片中的结构化区域（文字、图表等）
        regions = self._image_pipeline.extract(file_path)
        if not regions:
            return [], []

        source = os.path.basename(file_path)
        # 按空间位置将区域聚合为语义 chunk
        chunker = RegionChunker(text_chunking_strategy=self.chunking_strategy)
        chunks = chunker.chunk(regions, source=source, image_store=self._image_store)
        # 新管线不预计算 embedding，由调用方后续批量编码
        embeddings: list[list[float] | None] = [None] * len(chunks)
        return chunks, embeddings

    def process_file(self, file_path: str) -> tuple[list[dict], list[list[float] | None]]:
        """处理文件，自动识别格式

        Returns:
            (chunks, chunk_embeddings)
        """
        ext = os.path.splitext(file_path)[1].lower()
        # 新管线：图片和 PDF 使用 VLMExtractor 提取结构化区域
        if self._image_pipeline and ext in (self.IMAGE_EXTENSIONS | {'.pdf'}):
            return self._process_with_vlm_extractor(file_path)
        # 旧管线：走原有 HTML 解析 + 语义分块逻辑
        content = self.read_file(file_path)
        source = os.path.basename(file_path)
        return self.process_document(content, source)
