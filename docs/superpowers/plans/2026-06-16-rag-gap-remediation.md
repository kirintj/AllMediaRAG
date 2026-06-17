# RAG 全链路缺口补全实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全审计发现的 4 类缺口——工厂模式解耦、多模态 PDF 处理、测评体系完善、小问题修复，使项目功能完整度从 29 项中 20 项已实现提升到全部实现。

**Architecture:** 三阶段递进：阶段一建立可插拔架构基础（文件解析器工厂 + 切分策略抽象 + 查询改写抽象），阶段二在工厂架构上新增多模态 PDF 处理能力（PyMuPDF + pdfplumber + VLM 流水线），阶段三补全测评体系（RAGAS 集成 + Hit Rate + 配置对比框架）。每阶段独立可验证。

**Tech Stack:** Python 3.10+, FastAPI, ChromaDB, PyMuPDF(fitz), pdfplumber, RAGAS, sentence-transformers, jieba

---

## 阶段一：工厂模式补全

### Task 1: 新增文档解析器 Reader 实现

**Files:**
- Create: `backend/core/providers/readers/__init__.py`
- Create: `backend/core/providers/readers/pdf_reader.py`
- Create: `backend/core/providers/readers/markdown_reader.py`
- Create: `backend/core/providers/readers/docx_reader.py`
- Create: `backend/core/providers/readers/html_reader.py`
- Create: `backend/core/providers/readers/image_reader.py`
- Create: `tests/unit/test_providers/test_readers.py`

**依赖说明:** 基于已有的 `backend/core/providers/base.py` 中的 `FileReader` 抽象基类（第 5-43 行），该基类已定义 `read()`、`supported_extensions()`、`can_handle()` 方法。

- [ ] **Step 1: 创建 readers 包和 PDFReader**

创建 `backend/core/providers/readers/__init__.py`：

```python
"""文档解析器实现包

每个 Reader 实现 backend.core.providers.base.FileReader 接口。
"""
from .pdf_reader import PDFReader
from .markdown_reader import MarkdownReader
from .docx_reader import DocxReader
from .html_reader import HtmlReader
from .image_reader import ImageReader

__all__ = [
    "PDFReader",
    "MarkdownReader",
    "DocxReader",
    "HtmlReader",
    "ImageReader",
]
```

创建 `backend/core/providers/readers/pdf_reader.py`：

```python
"""PDF 文件读取器

从 document_processor._read_pdf 提取，使用 PyPDF2 进行基础文本提取。
"""
import logging
from core.providers.base import FileReader

logger = logging.getLogger(__name__)


class PDFReader(FileReader):
    """PDF 文件读取器（基础版，使用 PyPDF2）"""

    def __init__(self, ocr_provider=None):
        self.ocr_provider = ocr_provider

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def read(self, file_path: str) -> str:
        from PyPDF2 import PdfReader as PyPDF2Reader

        reader = PyPDF2Reader(file_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"

        if self._is_scanned_pdf(text, len(reader.pages)):
            logger.info("Scanned PDF detected, attempting OCR: %s", file_path)
            ocr_text = self._read_pdf_with_ocr(file_path)
            if ocr_text.strip():
                return ocr_text
            logger.warning("OCR extraction failed, falling back to empty text")

        return text

    def _is_scanned_pdf(self, text: str, page_count: int) -> bool:
        if page_count == 0:
            return False
        avg_chars_per_page = len(text.strip()) / page_count
        return avg_chars_per_page < 50

    def _read_pdf_with_ocr(self, file_path: str) -> str:
        if not self.ocr_provider or not self.ocr_provider.is_available():
            logger.warning("OCR provider not available")
            return ""
        try:
            return self.ocr_provider.extract_text(file_path)
        except Exception as e:
            logger.warning("OCR extraction failed: %s", e)
            return ""
```

- [ ] **Step 2: 创建 MarkdownReader**

创建 `backend/core/providers/readers/markdown_reader.py`：

```python
"""Markdown 文件读取器

从 document_processor._read_markdown 提取。
"""
from core.providers.base import FileReader


class MarkdownReader(FileReader):
    """Markdown 文件读取器"""

    def supported_extensions(self) -> list[str]:
        return [".md", ".markdown"]

    def read(self, file_path: str) -> str:
        import markdown
        with open(file_path, "r", encoding="utf-8") as f:
            md_content = f.read()
        return markdown.markdown(md_content)
```

- [ ] **Step 3: 创建 DocxReader**

创建 `backend/core/providers/readers/docx_reader.py`：

```python
"""Word 文档读取器

从 document_processor._read_docx 提取。
"""
from core.providers.base import FileReader


class DocxReader(FileReader):
    """Word (.docx) 文件读取器"""

    def supported_extensions(self) -> list[str]:
        return [".docx"]

    def read(self, file_path: str) -> str:
        from docx import Document
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            if para.text.strip():
                text += para.text + "\n\n"
        return text
```

- [ ] **Step 4: 创建 HtmlReader**

创建 `backend/core/providers/readers/html_reader.py`：

```python
"""HTML 文件读取器

从 document_processor.parse_html 提取。
"""
import re
from bs4 import BeautifulSoup
from core.providers.base import FileReader


class HtmlReader(FileReader):
    """HTML 文件读取器"""

    def supported_extensions(self) -> list[str]:
        return [".html", ".htm"]

    def read(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return self._parse_html(html_content)

    def _parse_html(self, html_content: str) -> str:
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
```

- [ ] **Step 5: 创建 ImageReader**

创建 `backend/core/providers/readers/image_reader.py`：

```python
"""图片文件读取器

从 document_processor._read_image 提取，支持 OCR + VLM 描述。
"""
import logging
from core.providers.base import FileReader

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}


class ImageReader(FileReader):
    """图片文件读取器（OCR + VLM 描述）"""

    def __init__(self, ocr_provider=None, vlm_provider=None):
        self.ocr_provider = ocr_provider
        self.vlm_provider = vlm_provider

    def supported_extensions(self) -> list[str]:
        return list(IMAGE_EXTENSIONS)

    def read(self, file_path: str) -> str:
        if not self.ocr_provider or not self.ocr_provider.is_available():
            logger.warning("OCR provider not available for image: %s", file_path)
            return ""

        try:
            ocr_text = self.ocr_provider.extract_text(file_path)

            if self.vlm_provider and self.vlm_provider.is_available():
                vlm_desc = self.vlm_provider.describe_image(file_path)
                if vlm_desc.strip():
                    return f"{ocr_text}\n\n[图片描述]\n{vlm_desc}"

            return ocr_text
        except Exception as e:
            logger.warning("Image OCR failed: %s", e)
            return ""
```

- [ ] **Step 6: 编写 Reader 单元测试**

创建 `tests/unit/test_providers/test_readers.py`：

```python
"""文档解析器单元测试"""
import os
import pytest
import tempfile


class TestPDFReader:
    def test_supported_extensions(self):
        from core.providers.readers import PDFReader
        reader = PDFReader()
        assert ".pdf" in reader.supported_extensions()

    def test_can_handle(self):
        from core.providers.readers import PDFReader
        reader = PDFReader()
        assert reader.can_handle("test.pdf")
        assert not reader.can_handle("test.txt")


class TestMarkdownReader:
    def test_supported_extensions(self):
        from core.providers.readers import MarkdownReader
        reader = MarkdownReader()
        assert ".md" in reader.supported_extensions()

    def test_read_markdown(self):
        from core.providers.readers import MarkdownReader
        reader = MarkdownReader()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("# 标题\n\n正文内容")
            f.flush()
            path = f.name
        try:
            result = reader.read(path)
            assert "标题" in result
            assert "正文内容" in result
        finally:
            os.unlink(path)


class TestDocxReader:
    def test_supported_extensions(self):
        from core.providers.readers import DocxReader
        reader = DocxReader()
        assert ".docx" in reader.supported_extensions()


class TestHtmlReader:
    def test_supported_extensions(self):
        from core.providers.readers import HtmlReader
        reader = HtmlReader()
        assert ".html" in reader.supported_extensions()
        assert ".htm" in reader.supported_extensions()

    def test_parse_html_removes_nav(self):
        from core.providers.readers import HtmlReader
        reader = HtmlReader()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8") as f:
            f.write("<html><nav>导航</nav><body>正文</body></html>")
            f.flush()
            path = f.name
        try:
            result = reader.read(path)
            assert "导航" not in result
            assert "正文" in result
        finally:
            os.unlink(path)


class TestImageReader:
    def test_supported_extensions(self):
        from core.providers.readers import ImageReader
        reader = ImageReader()
        assert ".png" in reader.supported_extensions()
        assert ".jpg" in reader.supported_extensions()

    def test_no_ocr_returns_empty(self):
        from core.providers.readers import ImageReader
        reader = ImageReader(ocr_provider=None)
        result = reader.read("nonexistent.png")
        assert result == ""
```

- [ ] **Step 7: 运行测试验证**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/unit/test_providers/test_readers.py -v`
Expected: 所有测试 PASS

- [ ] **Step 8: 提交**

```bash
git add backend/core/providers/readers/ tests/unit/test_providers/test_readers.py
git commit -m "feat: add FileReader implementations for PDF, Markdown, DOCX, HTML, Image"
```

---

### Task 2: 改造 DocumentProcessor 使用 Reader 工厂

**Files:**
- Modify: `backend/core/document_processor.py`
- Modify: `backend/core/rag_engine.py:60-67`

- [ ] **Step 1: 改造 DocumentProcessor.__init__ 接收 file_reader_registry**

修改 `backend/core/document_processor.py`，在 `__init__` 中新增 `file_reader_registry` 参数，`read_file` 方法改为通过 registry 查找 Reader：

```python
def __init__(self, config, ocr_provider=None, vlm_provider=None, file_reader_registry=None):
    """初始化

    Args:
        config: 配置对象
        ocr_provider: OCR 提供者（可选）
        vlm_provider: VLM 提供者（可选）
        file_reader_registry: 文件读取器注册表 {ext: FileReader}（可选）
    """
    self.percentile = config.SEMANTIC_CHUNK_PERCENTILE
    self.min_sentences = config.SEMANTIC_CHUNK_MIN_SENTENCES
    self.max_sentences = config.SEMANTIC_CHUNK_MAX_SENTENCES
    self.embedding_service = None
    self.ocr_provider = ocr_provider
    self.vlm_provider = vlm_provider
    self.file_reader_registry = file_reader_registry or {}
```

- [ ] **Step 2: 改造 read_file 方法**

将 `read_file` 方法改为优先从 registry 查找 Reader，找不到时回退到原有硬编码逻辑：

```python
def read_file(self, file_path: str) -> str:
    """读取文件内容，支持多种格式"""
    import logging
    logger = logging.getLogger(__name__)

    ext = os.path.splitext(file_path)[1].lower()

    # 优先从 registry 查找 Reader
    if ext in self.file_reader_registry:
        reader = self.file_reader_registry[ext]
        if reader.can_handle(file_path):
            return reader.read(file_path)

    # 回退到原有硬编码逻辑（向后兼容）
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
    elif ext in self.IMAGE_EXTENSIONS:
        return self._read_image(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
```

- [ ] **Step 3: 改造 RAGEngine 创建 Reader registry 并注入**

修改 `backend/core/rag_engine.py`，在 `__init__` 中（约 line 60-67 区域），创建 Reader registry 并注入到 DocumentProcessor：

在 `__init__` 方法中，OCR/VLM provider 初始化之后、DocumentProcessor 创建之前，新增：

```python
        # 构建文件读取器注册表
        file_reader_registry = self._build_file_reader_registry(ocr_provider, vlm_provider)

        self.document_processor = DocumentProcessor(
            config, ocr_provider, vlm_provider,
            file_reader_registry=file_reader_registry
        )
```

新增 `_build_file_reader_registry` 方法：

```python
    def _build_file_reader_registry(self, ocr_provider, vlm_provider) -> dict:
        """构建文件读取器注册表

        Returns:
            {ext: FileReader} 映射
        """
        from core.providers.readers import (
            PDFReader, MarkdownReader, DocxReader, HtmlReader, ImageReader
        )

        readers = [
            PDFReader(ocr_provider=ocr_provider),
            MarkdownReader(),
            DocxReader(),
            HtmlReader(),
            ImageReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
        ]

        registry = {}
        for reader in readers:
            for ext in reader.supported_extensions():
                registry[ext] = reader

        logger.info("File reader registry built: %s", list(registry.keys()))
        return registry
```

- [ ] **Step 4: 运行现有测试确认无回归**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/ -v --timeout=60 2>/dev/null || echo "部分测试可能需要模型文件，跳过"`
Expected: 无新增失败

- [ ] **Step 5: 提交**

```bash
git add backend/core/document_processor.py backend/core/rag_engine.py
git commit -m "refactor: wire FileReader registry into DocumentProcessor via RAGEngine"
```

---

### Task 3: 新增切分策略抽象层

**Files:**
- Create: `backend/core/chunking/__init__.py`
- Create: `backend/core/chunking/base.py`
- Create: `backend/core/chunking/semantic_strategy.py`
- Create: `backend/core/chunking/fixed_size_strategy.py`
- Create: `backend/core/chunking/recursive_strategy.py`
- Create: `tests/unit/test_chunking/test_strategies.py`
- Modify: `backend/core/providers/factory.py` (新增切分策略注册)
- Modify: `backend/core/config.py` (新增 CHUNKING_STRATEGY 配置)

- [ ] **Step 1: 创建 ChunkingStrategy 基类**

创建 `backend/core/chunking/__init__.py`：

```python
"""切分策略包

每个策略实现 ChunkingStrategy 抽象基类。
"""
from .base import ChunkingStrategy, ChunkData
from .semantic_strategy import SemanticChunking
from .fixed_size_strategy import FixedSizeChunking
from .recursive_strategy import RecursiveChunking

__all__ = [
    "ChunkingStrategy",
    "ChunkData",
    "SemanticChunking",
    "FixedSizeChunking",
    "RecursiveChunking",
]
```

创建 `backend/core/chunking/base.py`：

```python
"""切分策略抽象基类"""
from abc import ABC, abstractmethod
from typing import TypedDict


class ChunkData(TypedDict):
    """切分结果数据结构"""
    content: str
    metadata: dict


class ChunkingStrategy(ABC):
    """切分策略抽象接口

    所有切分策略必须实现此接口。
    """

    @abstractmethod
    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        """将文本切分为 chunk 列表

        Args:
            text: 待切分的文本
            metadata: 附加到每个 chunk 的元数据

        Returns:
            ChunkData 列表
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称，用于配置和日志"""
        pass
```

- [ ] **Step 2: 实现 SemanticChunking 策略（从 DocumentProcessor 提取）**

创建 `backend/core/chunking/semantic_strategy.py`：

```python
"""语义切分策略

基于句子级 embedding 余弦相似度的动态切分。
从 DocumentProcessor.semantic_chunk 逻辑提取。
"""
import re
import numpy as np
from .base import ChunkingStrategy, ChunkData


class SemanticChunking(ChunkingStrategy):
    """语义相似度切分策略"""

    def __init__(self, embedding_service=None, percentile: int = 25,
                 min_sentences: int = 2, max_sentences: int = 20):
        self.embedding_service = embedding_service
        self.percentile = percentile
        self.min_sentences = min_sentences
        self.max_sentences = max_sentences

    @property
    def name(self) -> str:
        return "semantic"

    def set_embedding_service(self, embedding_service):
        """注入 embedding 服务（延迟注入，避免循环依赖）"""
        self.embedding_service = embedding_service

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        metadata = metadata or {}
        sentences = self._split_into_sentences(text)
        if not sentences:
            return []

        if len(sentences) <= self.min_sentences:
            return [{"content": "\n".join(sentences), "metadata": metadata.copy()}]

        if self.embedding_service:
            sentence_embeddings = self.embedding_service.encode(sentences)
            sentence_groups = self._semantic_chunk(sentences, sentence_embeddings)
        else:
            sentence_groups = [
                list(range(i, min(i + self.min_sentences, len(sentences))))
                for i in range(0, len(sentences), self.min_sentences)
            ]

        chunks = []
        for group_indices in sentence_groups:
            chunk_sentences = [sentences[i] for i in group_indices]
            chunk_text = "\n".join(chunk_sentences)
            if chunk_text.strip():
                chunks.append({"content": chunk_text, "metadata": metadata.copy()})

        return chunks

    def _split_into_sentences(self, text: str) -> list[str]:
        paragraphs = re.split(r"\n\n+", text)
        sentences = []
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if re.match(r"^__CODE_BLOCK_\d+__$", para):
                sentences.append(para)
                continue
            parts = re.split(r"(?<=[。？！\n])", para)
            for part in parts:
                part = part.strip()
                if part:
                    sentences.append(part)
        return sentences

    def _semantic_chunk(self, sentences: list[str],
                        embeddings: list[list[float]]) -> list[list[int]]:
        if len(sentences) <= self.min_sentences:
            return [list(range(len(sentences)))]

        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)

        threshold = float(np.percentile(similarities, self.percentile))

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

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        a_arr = np.array(a)
        b_arr = np.array(b)
        dot = np.dot(a_arr, b_arr)
        norm = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
        if norm == 0:
            return 0.0
        return float(dot / norm)
```

- [ ] **Step 3: 实现 FixedSizeChunking 策略**

创建 `backend/core/chunking/fixed_size_strategy.py`：

```python
"""固定大小切分策略

按 token 数（近似字符数）切分，支持重叠。
"""
from .base import ChunkingStrategy, ChunkData


class FixedSizeChunking(ChunkingStrategy):
    """固定大小切分策略"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @property
    def name(self) -> str:
        return "fixed_size"

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        metadata = metadata or {}
        if not text.strip():
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.chunk_size, text_len)

            # 尝试在句子边界切分
            if end < text_len:
                # 在 chunk_size 范围内寻找最后一个句子结束符
                boundary = self._find_sentence_boundary(text, start, end)
                if boundary > start:
                    end = boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({"content": chunk_text, "metadata": metadata.copy()})

            # 下一个 chunk 的起始位置（考虑重叠）
            start = end - self.chunk_overlap if end < text_len else text_len

        return chunks

    @staticmethod
    def _find_sentence_boundary(text: str, start: int, end: int) -> int:
        """在 [start, end) 范围内寻找最后一个句子结束符"""
        for i in range(end - 1, start, -1):
            if text[i] in "。！？\n":
                return i + 1
        return end
```

- [ ] **Step 4: 实现 RecursiveChunking 策略**

创建 `backend/core/chunking/recursive_strategy.py`：

```python
"""递归切分策略

按段落 → 句子 → 字符逐级递归切分。
"""
import re
from .base import ChunkingStrategy, ChunkData


class RecursiveChunking(ChunkingStrategy):
    """递归字符切分策略"""

    SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", " "]

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @property
    def name(self) -> str:
        return "recursive"

    def split(self, text: str, metadata: dict = None) -> list[ChunkData]:
        metadata = metadata or {}
        if not text.strip():
            return []

        raw_chunks = self._recursive_split(text, self.SEPARATORS)
        chunks = []
        for chunk_text in raw_chunks:
            chunk_text = chunk_text.strip()
            if chunk_text:
                chunks.append({"content": chunk_text, "metadata": metadata.copy()})

        return chunks

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        # 选择第一个能切分文本的分隔符
        separator = None
        for sep in separators:
            if sep in text:
                separator = sep
                break

        if separator is None:
            # 无可用分隔符，硬切
            return self._hard_split(text)

        parts = text.split(separator)
        chunks = []
        current = ""

        for part in parts:
            candidate = current + separator + part if current else part
            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current.strip():
                    chunks.append(current.strip())
                # 如果单个 part 仍然超过 chunk_size，递归切分
                if len(part) > self.chunk_size:
                    sub_separators = separators[separators.index(separator) + 1:]
                    if sub_separators:
                        chunks.extend(self._recursive_split(part, sub_separators))
                    else:
                        chunks.extend(self._hard_split(part))
                    current = ""
                else:
                    current = part

        if current.strip():
            chunks.append(current.strip())

        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """硬切分为 chunk_size 大小"""
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunk = text[i:i + self.chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks
```

- [ ] **Step 5: 在 ProviderFactory 中注册切分策略**

修改 `backend/core/providers/factory.py`，新增切分策略注册和创建方法：

在类变量区域（约 line 20-23）新增：

```python
    _chunking_strategies: dict[str, type] = {}
```

新增注册和创建方法：

```python
    @classmethod
    def register_chunking_strategy(cls, name: str, strategy_class):
        """注册切分策略

        Args:
            name: 策略名称
            strategy_class: 策略类
        """
        cls._chunking_strategies[name] = strategy_class
        logger.debug("Registered chunking strategy: %s", name)

    @classmethod
    def create_chunking_strategy(cls, name: str, **kwargs):
        """创建切分策略实例

        Args:
            name: 策略名称
            **kwargs: 传递给构造函数的参数

        Returns:
            ChunkingStrategy 实例
        """
        strategy_class = cls._chunking_strategies.get(name)
        if not strategy_class:
            available = list(cls._chunking_strategies.keys())
            raise ValueError(f"Unknown chunking strategy: {name}. Available: {available}")
        return strategy_class(**kwargs)
```

更新 `get_available_providers` 方法，新增 `chunking_strategies` 键。

- [ ] **Step 6: 在 config.py 新增 CHUNKING_STRATEGY 配置**

修改 `backend/core/config.py`，在 `# 语义切分参数` 区域（约 line 50-53）之后新增：

```python
    # 切分策略配置
    CHUNKING_STRATEGY: str = os.getenv("CHUNKING_STRATEGY", "semantic")  # semantic | fixed_size | recursive
```

- [ ] **Step 7: 编写切分策略单元测试**

创建 `tests/unit/test_chunking/test_strategies.py`：

```python
"""切分策略单元测试"""
import pytest


class TestFixedSizeChunking:
    def test_split_basic(self):
        from core.chunking import FixedSizeChunking
        strategy = FixedSizeChunking(chunk_size=20, chunk_overlap=5)
        text = "这是一段测试文本，用于验证固定大小切分策略的效果。" * 3
        chunks = strategy.split(text)
        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk["content"]
            assert "metadata" in chunk

    def test_empty_text(self):
        from core.chunking import FixedSizeChunking
        strategy = FixedSizeChunking()
        assert strategy.split("") == []

    def test_name(self):
        from core.chunking import FixedSizeChunking
        assert FixedSizeChunking().name == "fixed_size"


class TestRecursiveChunking:
    def test_split_basic(self):
        from core.chunking import RecursiveChunking
        strategy = RecursiveChunking(chunk_size=50, chunk_overlap=10)
        text = "第一段内容。\n\n第二段内容，比较长一些。\n\n第三段。"
        chunks = strategy.split(text)
        assert len(chunks) >= 1

    def test_empty_text(self):
        from core.chunking import RecursiveChunking
        strategy = RecursiveChunking()
        assert strategy.split("") == []

    def test_name(self):
        from core.chunking import RecursiveChunking
        assert RecursiveChunking().name == "recursive"


class TestSemanticChunking:
    def test_short_text_single_chunk(self):
        from core.chunking import SemanticChunking
        strategy = SemanticChunking(min_sentences=2)
        chunks = strategy.split("一句话。")
        assert len(chunks) == 1

    def test_name(self):
        from core.chunking import SemanticChunking
        assert SemanticChunking().name == "semantic"
```

- [ ] **Step 8: 运行测试**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/unit/test_chunking/ -v`
Expected: 所有测试 PASS

- [ ] **Step 9: 提交**

```bash
git add backend/core/chunking/ backend/core/providers/factory.py backend/core/config.py tests/unit/test_chunking/
git commit -m "feat: add ChunkingStrategy abstraction with semantic, fixed_size, recursive strategies"
```

---

### Task 4: 新增查询改写抽象层

**Files:**
- Create: `backend/core/query_understanding/rewriters/__init__.py`
- Create: `backend/core/query_understanding/rewriters/base.py`
- Create: `backend/core/query_understanding/rewriters/hyde_rewriter.py`
- Create: `backend/core/query_understanding/rewriters/multi_query_rewriter.py`
- Modify: `backend/core/rag_engine.py:89-92` (改用 rewriter 注册表)

- [ ] **Step 1: 创建 QueryRewriter 基类**

创建 `backend/core/query_understanding/rewriters/__init__.py`：

```python
"""查询改写策略包"""
from .base import QueryRewriter
from .hyde_rewriter import HyDERewriter
from .multi_query_rewriter import MultiQueryRewriter

__all__ = ["QueryRewriter", "HyDERewriter", "MultiQueryRewriter"]
```

创建 `backend/core/query_understanding/rewriters/base.py`：

```python
"""查询改写策略抽象基类"""
from abc import ABC, abstractmethod
from typing import Optional


class QueryRewriter(ABC):
    """查询改写策略抽象接口

    所有查询改写策略必须实现此接口。
    """

    @abstractmethod
    async def rewrite(self, query: str, context: dict = None) -> list[str]:
        """异步改写查询

        Args:
            query: 原始查询
            context: 上下文信息（意图类型等）

        Returns:
            改写后的查询列表（不含原始查询）
        """
        pass

    def rewrite_sync(self, query: str, context: dict = None) -> list[str]:
        """同步改写查询（默认实现，子类可覆盖）

        Args:
            query: 原始查询
            context: 上下文信息

        Returns:
            改写后的查询列表（不含原始查询）
        """
        import asyncio
        return asyncio.run(self.rewrite(query, context))

    @property
    @abstractmethod
    def name(self) -> str:
        """改写器名称"""
        pass
```

- [ ] **Step 2: 实现 HyDERewriter（包装原有 HyDEGenerator）**

创建 `backend/core/query_understanding/rewriters/hyde_rewriter.py`：

```python
"""HyDE 查询改写策略

包装原有的 HyDEGenerator，实现 QueryRewriter 接口。
"""
import asyncio
import logging
from typing import Any, Optional
from .base import QueryRewriter

logger = logging.getLogger(__name__)


class HyDERewriter(QueryRewriter):
    """HyDE (Hypothetical Document Embeddings) 改写策略"""

    def __init__(self, llm_client: Any):
        from core.query_understanding.hyde_generator import HyDEGenerator
        self._generator = HyDEGenerator(llm_client)

    @property
    def name(self) -> str:
        return "hyde"

    async def rewrite(self, query: str, context: dict = None) -> list[str]:
        intent_type = context.get("intent_type") if context else None
        result = await asyncio.to_thread(
            self._generator.generate_hypothetical_document, query, intent_type
        )
        return [result] if result else []

    def rewrite_sync(self, query: str, context: dict = None) -> list[str]:
        intent_type = context.get("intent_type") if context else None
        result = self._generator.generate_hypothetical_document(query, intent_type)
        return [result] if result else []
```

- [ ] **Step 3: 实现 MultiQueryRewriter（包装原有 MultiQueryGenerator）**

创建 `backend/core/query_understanding/rewriters/multi_query_rewriter.py`：

```python
"""Multi-Query 查询改写策略

包装原有的 MultiQueryGenerator，实现 QueryRewriter 接口。
"""
import asyncio
import logging
from typing import Any
from .base import QueryRewriter

logger = logging.getLogger(__name__)


class MultiQueryRewriter(QueryRewriter):
    """Multi-Query 改写策略"""

    def __init__(self, llm_client: Any, num_queries: int = 3):
        from core.query_understanding.multi_query import MultiQueryGenerator
        self._generator = MultiQueryGenerator(llm_client)
        self.num_queries = num_queries

    @property
    def name(self) -> str:
        return "multi_query"

    async def rewrite(self, query: str, context: dict = None) -> list[str]:
        num = context.get("num_queries", self.num_queries) if context else self.num_queries
        result = await asyncio.to_thread(
            self._generator.generate_queries, query, num
        )
        # generate_queries 返回 [原始查询, ...变体]，去掉原始查询
        return [q for q in result if q != query]

    def rewrite_sync(self, query: str, context: dict = None) -> list[str]:
        num = context.get("num_queries", self.num_queries) if context else self.num_queries
        result = self._generator.generate_queries(query, num)
        return [q for q in result if q != query]
```

- [ ] **Step 4: 在 RAGEngine 中接入 rewriter 抽象层**

修改 `backend/core/rag_engine.py`，在查询理解层初始化区域（约 line 89-92）新增 rewriter 注册：

```python
        # 查询理解层
        self.classifier = QueryClassifier(self.llm_client)
        self.router = QueryRouter()

        # 查询改写器注册表
        from core.query_understanding.rewriters import HyDERewriter, MultiQueryRewriter
        self.rewriters = {}
        if config.USE_HYDE:
            self.rewriters["hyde"] = HyDERewriter(self.llm_client)
        if config.MULTI_QUERY_ENABLED:
            self.rewriters["multi_query"] = MultiQueryRewriter(
                self.llm_client, num_queries=config.MULTI_QUERY_COUNT
            )

        # 向后兼容：保留原有直接引用
        self.hyde_generator = self.rewriters.get("hyde")
        self.multi_query_generator = self.rewriters.get("multi_query")
```

注意：`full_retrieve` 和 `full_retrieve_async` 中的查询改写调用需要适配新接口，但保留原有 `self.hyde_generator` / `self.multi_query_generator` 引用以确保向后兼容。后续可逐步迁移为统一调用 `self.rewriters`。

- [ ] **Step 5: 提交**

```bash
git add backend/core/query_understanding/rewriters/ backend/core/rag_engine.py
git commit -m "feat: add QueryRewriter abstraction with HyDE and MultiQuery implementations"
```

---

### Task 5: 修复小问题（config flag 接线 + 重复调用）

**Files:**
- Modify: `backend/core/rag_engine.py` (CITATION_VERIFY_ENABLED, RETRIEVAL_REFETCH_ENABLED, 重复 router.route)
- Modify: `backend/core/query_understanding/classifier.py` (移除误导性 llm_client 参数)
- Modify: `backend/api/chat.py` (CITATION_VERIFY_ENABLED)

- [ ] **Step 1: 在 rag_engine.py 接入 CITATION_VERIFY_ENABLED**

在 `full_retrieve` 方法中引用核查逻辑处（约 line 1057-1074 区域），在调用 `self.citation_verifier` 之前添加条件检查：

在 `query_stream` 方法中找到类似以下代码块：
```python
        # 引用核查
        verification = self.citation_verifier.verify(...)
```

改为：
```python
        # 引用核查（受 CITATION_VERIFY_ENABLED 控制）
        verification = None
        if getattr(self, '_citation_verify_enabled', True):
            verification = self.citation_verifier.verify(...)
```

在 `__init__` 中新增配置缓存：
```python
        self._citation_verify_enabled = getattr(config, 'CITATION_VERIFY_ENABLED', True)
        self._refetch_enabled = getattr(config, 'RETRIEVAL_REFETCH_ENABLED', True)
```

- [ ] **Step 2: 在 rag_engine.py 接入 RETRIEVAL_REFETCH_ENABLED**

在 `full_retrieve` 方法中二次检索逻辑处（约 line 684-707），在 `if eval_result["needs_refetch"]` 之前添加条件：

```python
        # 6.5 置信度评估 + 二次检索
        if self._refetch_enabled:
            eval_result = self.confidence_evaluator.evaluate(result)
            if eval_result["needs_refetch"]:
                # ... 原有二次检索逻辑不变
```

- [ ] **Step 3: 移除重复的 router.route() 调用**

在 `full_retrieve` 方法中，约 line 671 处有第二次 `route_config = self.router.route(query, intent)` 调用，将其移除。直接使用 line 639 处已有的 `route_config`。

- [ ] **Step 4: 修复 QueryClassifier 参数**

修改 `backend/core/query_understanding/classifier.py`，移除 `__init__` 中的误导性参数：

```python
    def __init__(self):
        """纯规则分类器，无需外部依赖"""
        pass
```

更新 `rag_engine.py` 中的实例化调用（约 line 89 和 line 176 和 line 278）：
```python
        self.classifier = QueryClassifier()
```

- [ ] **Step 5: 在 chat.py 接入 CITATION_VERIFY_ENABLED**

修改 `backend/api/chat.py`，在引用核查调用处添加条件检查。

- [ ] **Step 6: 运行测试确认无回归**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/ -v --timeout=60 2>/dev/null || echo "部分测试需要模型文件"`
Expected: 无新增失败

- [ ] **Step 7: 提交**

```bash
git add backend/core/rag_engine.py backend/core/query_understanding/classifier.py backend/api/chat.py
git commit -m "fix: wire CITATION_VERIFY_ENABLED/RETRIEVAL_REFETCH_ENABLED, remove duplicate router call, fix classifier params"
```

---

## 阶段二：多模态 PDF 处理

### Task 6: 安装新依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 安装 PyMuPDF 和 pdfplumber**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend && pip install PyMuPDF>=1.24.0 pdfplumber>=0.11.0`

- [ ] **Step 2: 更新 requirements.txt**

修改 `backend/requirements.txt`，在 `# === 文本处理 ===` 区域新增：

```
# === PDF 增强解析 ===
PyMuPDF>=1.24.0
pdfplumber>=0.11.0
```

- [ ] **Step 3: 验证安装**

Run: `python -c "import fitz; import pdfplumber; print('OK')"`
Expected: `OK`

- [ ] **Step 4: 提交**

```bash
git add backend/requirements.txt
git commit -m "deps: add PyMuPDF and pdfplumber for enhanced PDF parsing"
```

---

### Task 7: 实现 EnhancedPDFReader

**Files:**
- Create: `backend/core/providers/readers/enhanced_pdf_reader.py`
- Modify: `backend/core/providers/readers/__init__.py`
- Create: `tests/unit/test_providers/test_enhanced_pdf_reader.py`

- [ ] **Step 1: 实现 EnhancedPDFReader**

创建 `backend/core/providers/readers/enhanced_pdf_reader.py`：

```python
"""增强型 PDF 解析器

支持文本提取、内嵌图片提取（OCR + VLM）、表格提取（pdfplumber）。
替代基础 PDFReader，提供多模态 PDF 内容提取能力。
"""
import os
import re
import logging
import tempfile
from typing import Optional

from core.providers.base import FileReader

logger = logging.getLogger(__name__)


class EnhancedPDFReader(FileReader):
    """增强型 PDF 解析器，支持文本、图片、表格多模态提取

    处理流程：
    1. 逐页使用 PyMuPDF 提取文本（支持多栏布局）
    2. 提取内嵌图片 → OCR + VLM 描述
    3. 使用 pdfplumber 提取表格 → Markdown 格式
    4. 扫描页面自动降级为整页 OCR
    """

    MIN_IMAGE_SIZE = 100  # 过滤 < 100x100 的装饰性图片
    SCANNED_THRESHOLD = 50  # 每页平均字符数 < 50 判定为扫描页

    def __init__(self, ocr_provider=None, vlm_provider=None):
        self.ocr = ocr_provider
        self.vlm = vlm_provider

    def supported_extensions(self) -> list[str]:
        return [".pdf"]

    def read(self, file_path: str) -> str:
        """提取 PDF 全部内容（文本 + 图片描述 + 表格）"""
        import fitz  # PyMuPDF

        if not os.path.exists(file_path):
            logger.warning("PDF file not found: %s", file_path)
            return ""

        page_contents = []

        with tempfile.TemporaryDirectory() as temp_dir:
            doc = fitz.open(file_path)

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_parts = []

                # 1. 文本提取
                text = self._extract_page_text(page)

                # 判断是否为扫描页
                if len(text.strip()) < self.SCANNED_THRESHOLD:
                    scanned_text = self._process_scanned_page(file_path, page_num, temp_dir)
                    if scanned_text:
                        page_parts.append(scanned_text)
                else:
                    page_parts.append(text)

                # 2. 内嵌图片提取
                image_descriptions = self._extract_page_images(page, page_num, temp_dir)
                page_parts.extend(image_descriptions)

                # 3. 表格提取
                table_texts = self._extract_page_tables(file_path, page_num)
                page_parts.extend(table_texts)

                page_content = "\n\n".join(part for part in page_parts if part.strip())
                if page_content.strip():
                    page_contents.append(page_content)

            doc.close()

        return "\n\n".join(page_contents)

    def _extract_page_text(self, page) -> str:
        """PyMuPDF 文本提取（支持多栏布局）"""
        text = page.get_text("text")
        return text.strip() if text else ""

    def _extract_page_images(self, page, page_num: int, temp_dir: str) -> list[str]:
        """提取页面内嵌图片，返回描述列表"""
        descriptions = []

        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            try:
                xref = img_info[0]
                description = self._process_image(page.parent, xref, page_num, img_idx, temp_dir)
                if description:
                    descriptions.append(description)
            except Exception as e:
                logger.debug("Image extraction failed (page %d, img %d): %s",
                             page_num, img_idx, e)

        return descriptions

    def _process_image(self, doc, xref: int, page_num: int,
                       img_idx: int, temp_dir: str) -> Optional[str]:
        """处理单个内嵌图片：提取 → 过滤 → OCR → VLM"""
        import fitz

        base_image = doc.extract_image(xref)
        if not base_image:
            return None

        image_bytes = base_image["image"]
        width = base_image.get("width", 0)
        height = base_image.get("height", 0)

        # 过滤装饰性小图
        if width < self.MIN_IMAGE_SIZE or height < self.MIN_IMAGE_SIZE:
            return None

        # 保存到临时文件
        ext = base_image.get("ext", "png")
        image_path = os.path.join(temp_dir, f"page{page_num}_img{img_idx}.{ext}")
        with open(image_path, "wb") as f:
            f.write(image_bytes)

        parts = []

        # OCR 提取文字
        if self.ocr and self.ocr.is_available():
            try:
                ocr_text = self.ocr.extract_text(image_path)
                if ocr_text and ocr_text.strip():
                    parts.append(f"[图片OCR - 第{page_num + 1}页]\n{ocr_text}")
            except Exception as e:
                logger.debug("Image OCR failed: %s", e)

        # VLM 语义描述
        if self.vlm and self.vlm.is_available():
            try:
                vlm_desc = self.vlm.describe_image(image_path)
                if vlm_desc and vlm_desc.strip():
                    parts.append(f"[图片描述 - 第{page_num + 1}页]\n{vlm_desc}")
            except Exception as e:
                logger.debug("VLM description failed: %s", e)

        return "\n\n".join(parts) if parts else None

    def _extract_page_tables(self, pdf_path: str, page_num: int) -> list[str]:
        """使用 pdfplumber 提取页面表格，返回 Markdown 格式列表"""
        try:
            import pdfplumber
        except ImportError:
            return []

        tables_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if page_num >= len(pdf.pages):
                    return []

                page = pdf.pages[page_num]
                tables = page.extract_tables()

                for table_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        continue

                    md_table = self._table_to_markdown(table)
                    if md_table:
                        tables_text.append(
                            f"[表格 - 第{page_num + 1}页]\n{md_table}"
                        )
        except Exception as e:
            logger.debug("Table extraction failed (page %d): %s", page_num, e)

        return tables_text

    @staticmethod
    def _table_to_markdown(table: list[list]) -> str:
        """将二维列表转换为 Markdown 表格格式"""
        if not table or not table[0]:
            return ""

        # 清洗单元格
        cleaned = []
        for row in table:
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            cleaned.append(cleaned_row)

        # 确保所有行等长
        max_cols = max(len(row) for row in cleaned)
        for row in cleaned:
            while len(row) < max_cols:
                row.append("")

        lines = []
        # 表头
        lines.append("| " + " | ".join(cleaned[0]) + " |")
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        # 数据行
        for row in cleaned[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def _process_scanned_page(self, pdf_path: str, page_num: int, temp_dir: str) -> str:
        """处理扫描页面：整页转图片 → OCR"""
        import fitz

        if not self.ocr or not self.ocr.is_available():
            return ""

        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]

            # 高分辨率渲染
            mat = fitz.Matrix(2, 2)  # 2x 缩放
            pix = page.get_pixmap(matrix=mat)
            image_path = os.path.join(temp_dir, f"scanned_page{page_num}.png")
            pix.save(image_path)
            doc.close()

            ocr_text = self.ocr.extract_text(image_path)
            return ocr_text if ocr_text else ""
        except Exception as e:
            logger.warning("Scanned page OCR failed (page %d): %s", page_num, e)
            return ""
```

- [ ] **Step 2: 更新 readers/__init__.py 导出 EnhancedPDFReader**

修改 `backend/core/providers/readers/__init__.py`，新增导入：

```python
from .enhanced_pdf_reader import EnhancedPDFReader
```

并在 `__all__` 中新增 `"EnhancedPDFReader"`。

- [ ] **Step 3: 编写 EnhancedPDFReader 单元测试**

创建 `tests/unit/test_providers/test_enhanced_pdf_reader.py`：

```python
"""EnhancedPDFReader 单元测试"""
import pytest


class TestEnhancedPDFReader:
    def test_supported_extensions(self):
        from core.providers.readers.enhanced_pdf_reader import EnhancedPDFReader
        reader = EnhancedPDFReader()
        assert ".pdf" in reader.supported_extensions()

    def test_table_to_markdown(self):
        from core.providers.readers.enhanced_pdf_reader import EnhancedPDFReader
        table = [["姓名", "年龄"], ["张三", "25"], ["李四", "30"]]
        md = EnhancedPDFReader._table_to_markdown(table)
        assert "| 姓名 | 年龄 |" in md
        assert "| --- | --- |" in md
        assert "| 张三 | 25 |" in md

    def test_table_to_markdown_empty(self):
        from core.providers.readers.enhanced_pdf_reader import EnhancedPDFReader
        assert EnhancedPDFReader._table_to_markdown([]) == ""
        assert EnhancedPDFReader._table_to_markdown([[]]) == ""

    def test_read_nonexistent_file(self):
        from core.providers.readers.enhanced_pdf_reader import EnhancedPDFReader
        reader = EnhancedPDFReader()
        result = reader.read("/nonexistent/file.pdf")
        assert result == ""

    def test_init_without_providers(self):
        from core.providers.readers.enhanced_pdf_reader import EnhancedPDFReader
        reader = EnhancedPDFReader()
        assert reader.ocr is None
        assert reader.vlm is None
```

- [ ] **Step 4: 运行测试**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/unit/test_providers/test_enhanced_pdf_reader.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/providers/readers/enhanced_pdf_reader.py backend/core/providers/readers/__init__.py tests/unit/test_providers/test_enhanced_pdf_reader.py
git commit -m "feat: add EnhancedPDFReader with embedded image/table extraction and VLM integration"
```

---

### Task 8: 集成 EnhancedPDFReader 到 RAGEngine

**Files:**
- Modify: `backend/core/rag_engine.py:_build_file_reader_registry`

- [ ] **Step 1: 修改 _build_file_reader_registry 使用 EnhancedPDFReader**

修改 `backend/core/rag_engine.py` 中的 `_build_file_reader_registry` 方法，将 `PDFReader` 替换为 `EnhancedPDFReader`：

```python
    def _build_file_reader_registry(self, ocr_provider, vlm_provider) -> dict:
        """构建文件读取器注册表"""
        from core.providers.readers import (
            EnhancedPDFReader, MarkdownReader, DocxReader, HtmlReader, ImageReader
        )

        readers = [
            EnhancedPDFReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
            MarkdownReader(),
            DocxReader(),
            HtmlReader(),
            ImageReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
        ]

        registry = {}
        for reader in readers:
            for ext in reader.supported_extensions():
                registry[ext] = reader

        logger.info("File reader registry built: %s", list(registry.keys()))
        return registry
```

- [ ] **Step 2: 更新 import 语句**

将 `from core.providers.readers import PDFReader` 替换为 `from core.providers.readers import EnhancedPDFReader`。

- [ ] **Step 3: 验证集成**

手动测试：上传一个包含图片和表格的 PDF 文件，检查日志中是否出现 `[图片OCR]`、`[图片描述]`、`[表格]` 标签。

- [ ] **Step 4: 提交**

```bash
git add backend/core/rag_engine.py
git commit -m "feat: integrate EnhancedPDFReader into RAGEngine file reader registry"
```

---

## 阶段三：测评体系完善

### Task 9: 新增 Hit Rate 指标并集成到现有评估器

**Files:**
- Create: `backend/eval/metrics.py`
- Modify: `backend/eval/evaluator.py` (集成 hit_rate)
- Create: `tests/unit/test_eval/test_metrics.py`

- [ ] **Step 1: 创建 metrics.py**

创建 `backend/eval/metrics.py`：

```python
"""自定义评估指标集合

提供 RAG 检索和生成的评估指标函数。
"""
import numpy as np


def hit_rate(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """Hit Rate：至少命中一个相关文档返回 1.0，否则 0.0

    Args:
        retrieved_sources: 检索到的文档来源列表
        expected_sources: 期望命中的文档来源集合

    Returns:
        1.0 或 0.0
    """
    if not expected_sources:
        return 0.0
    return 1.0 if any(src in expected_sources for src in retrieved_sources) else 0.0


def recall_at_k(retrieved_sources: list[str], expected_sources: set[str], k: int = 5) -> float:
    """Recall@K：前 K 个结果中命中的相关文档比例

    Args:
        retrieved_sources: 检索到的文档来源列表
        expected_sources: 期望命中的文档来源集合
        k: 截断数量

    Returns:
        命中比例 [0, 1]
    """
    if not expected_sources:
        return 0.0
    retrieved_top_k = retrieved_sources[:k]
    hits = sum(1 for src in retrieved_top_k if src in expected_sources)
    return hits / len(expected_sources)


def mrr(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """MRR (Mean Reciprocal Rank)：第一个命中结果的排名倒数

    Args:
        retrieved_sources: 检索到的文档来源列表
        expected_sources: 期望命中的文档来源集合

    Returns:
        排名倒数 [0, 1]
    """
    for i, src in enumerate(retrieved_sources):
        if src in expected_sources:
            return 1.0 / (i + 1)
    return 0.0


def precision(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """Precision：召回结果中匹配的比例

    Args:
        retrieved_sources: 检索到的文档来源列表
        expected_sources: 期望命中的文档来源集合

    Returns:
        精确率 [0, 1]
    """
    if not retrieved_sources:
        return 0.0
    retrieved_set = set(retrieved_sources)
    hits = len(retrieved_set & expected_sources)
    return hits / len(retrieved_set)


def keyword_coverage(answer: str, expected_keywords: list[str]) -> float:
    """关键词覆盖率：回答中包含的期望关键词比例

    Args:
        answer: 系统生成的回答
        expected_keywords: 期望出现的关键词列表

    Returns:
        覆盖率 [0, 1]
    """
    if not expected_keywords:
        return 0.0
    hits = sum(1 for kw in expected_keywords if kw in answer)
    return hits / len(expected_keywords)
```

- [ ] **Step 2: 在 evaluator.py 中集成 hit_rate**

修改 `backend/eval/evaluator.py`，在 `_aggregate` 方法中新增 hit_rate 聚合：

在 `evaluate_retrieval` 方法的返回值中新增 hit_rate：

```python
        from eval.metrics import hit_rate as calc_hit_rate

        return {
            "recall": recall,
            "mrr": mrr,
            "precision": precision,
            "hit_rate": calc_hit_rate(retrieved_sources, expected_set),
            "retrieved_sources": retrieved_sources,
        }
```

在 `_aggregate` 方法中新增 hit_rate 聚合：

```python
        hit_rates = [r["retrieval"]["hit_rate"] for r in results if r["retrieval"]["hit_rate"] is not None]

        # 在 report 的 retrieval 部分新增：
        "hit_rate": float(np.mean(hit_rates)) if hit_rates else None,
```

- [ ] **Step 3: 编写 metrics 单元测试**

创建 `tests/unit/test_eval/test_metrics.py`：

```python
"""评估指标单元测试"""
import pytest


class TestHitRate:
    def test_hit(self):
        from eval.metrics import hit_rate
        assert hit_rate(["doc_a", "doc_b"], {"doc_a"}) == 1.0

    def test_miss(self):
        from eval.metrics import hit_rate
        assert hit_rate(["doc_a", "doc_b"], {"doc_c"}) == 0.0

    def test_empty_expected(self):
        from eval.metrics import hit_rate
        assert hit_rate(["doc_a"], set()) == 0.0


class TestRecallAtK:
    def test_full_recall(self):
        from eval.metrics import recall_at_k
        assert recall_at_k(["doc_a", "doc_b"], {"doc_a", "doc_b"}, k=5) == 1.0

    def test_partial_recall(self):
        from eval.metrics import recall_at_k
        assert recall_at_k(["doc_a"], {"doc_a", "doc_b"}, k=5) == 0.5

    def test_k_truncation(self):
        from eval.metrics import recall_at_k
        assert recall_at_k(["doc_a", "doc_b", "doc_c"], {"doc_c"}, k=2) == 0.0


class TestMRR:
    def test_first_rank(self):
        from eval.metrics import mrr
        assert mrr(["doc_a"], {"doc_a"}) == 1.0

    def test_second_rank(self):
        from eval.metrics import mrr
        assert mrr(["doc_b", "doc_a"], {"doc_a"}) == 0.5

    def test_no_match(self):
        from eval.metrics import mrr
        assert mrr(["doc_b"], {"doc_a"}) == 0.0


class TestKeywordCoverage:
    def test_full_coverage(self):
        from eval.metrics import keyword_coverage
        assert keyword_coverage("这是答案包含关键词", ["答案", "关键词"]) == 1.0

    def test_partial_coverage(self):
        from eval.metrics import keyword_coverage
        assert keyword_coverage("这是答案", ["答案", "关键词"]) == 0.5

    def test_empty_keywords(self):
        from eval.metrics import keyword_coverage
        assert keyword_coverage("任何文本", []) == 0.0
```

- [ ] **Step 4: 运行测试**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/unit/test_eval/test_metrics.py -v`
Expected: 所有测试 PASS

- [ ] **Step 5: 提交**

```bash
git add backend/eval/metrics.py backend/eval/evaluator.py tests/unit/test_eval/test_metrics.py
git commit -m "feat: add hit_rate metric and integrate into evaluator"
```

---

### Task 10: 集成 RAGAS 评估框架

**Files:**
- Create: `backend/eval/ragas_evaluator.py`
- Modify: `backend/eval/run_eval.py` (新增 --framework 参数)
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 安装 RAGAS**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend && pip install ragas>=0.2.0`

更新 `backend/requirements.txt`，新增：

```
# === 评估框架 ===
ragas>=0.2.0
```

- [ ] **Step 2: 实现 RAGASEvaluator**

创建 `backend/eval/ragas_evaluator.py`：

```python
"""RAGAS 标准评估器

基于 RAGAS 框架实现标准化的 RAG 评估。
与自研评估器 (evaluator.py) 并存互补。
"""
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """基于 RAGAS 框架的标准评估器

    支持 4 个核心指标：
    - Faithfulness: 回答是否基于参考文档
    - Answer Relevancy: 回答是否切题
    - Context Precision: 检索上下文的精确度
    - Context Recall: 检索上下文的召回率
    """

    def __init__(self, llm_client=None, embedding_service=None):
        """初始化

        Args:
            llm_client: LLM 客户端（RAGAS 内部使用）
            embedding_service: Embedding 服务（RAGAS 内部使用）
        """
        self.llm_client = llm_client
        self.embedding_service = embedding_service

    def evaluate(self, dataset: list[dict]) -> dict:
        """运行 RAGAS 评估

        Args:
            dataset: 评估数据集
                [{question, contexts, answer, ground_truth}]

        Returns:
            评估报告（与自研评估器的 report.json 结构对齐）
        """
        try:
            from ragas import evaluate as ragas_evaluate
            from ragas.metrics import (
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
            )
            from datasets import Dataset
        except ImportError as e:
            logger.error("RAGAS import failed: %s. Install with: pip install ragas", e)
            return {"error": str(e)}

        # 转换为 RAGAS 要求的格式
        ragas_data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": [],
        }

        for sample in dataset:
            ragas_data["question"].append(sample["question"])
            ragas_data["answer"].append(sample.get("answer", ""))
            ragas_data["contexts"].append(sample.get("contexts", []))
            ragas_data["ground_truth"].append(sample.get("ground_truth", ""))

        hf_dataset = Dataset.from_dict(ragas_data)

        metrics = [faithfulness, answer_relevancy, context_precision, context_recall]

        try:
            result = ragas_evaluate(
                dataset=hf_dataset,
                metrics=metrics,
            )

            # 转换为对齐的报告格式
            report = {
                "total_samples": len(dataset),
                "framework": "ragas",
                "retrieval": {
                    "context_precision": float(result["context_precision"]),
                    "context_recall": float(result["context_recall"]),
                },
                "generation": {
                    "faithfulness": float(result["faithfulness"]),
                    "answer_relevancy": float(result["answer_relevancy"]),
                },
                "details": [],
            }

            # 逐条结果（如果可用）
            if hasattr(result, "to_pandas"):
                df = result.to_pandas()
                for _, row in df.iterrows():
                    report["details"].append({
                        "question": row.get("question", ""),
                        "faithfulness": float(row.get("faithfulness", 0)),
                        "answer_relevancy": float(row.get("answer_relevancy", 0)),
                        "context_precision": float(row.get("context_precision", 0)),
                        "context_recall": float(row.get("context_recall", 0)),
                    })

            return report

        except Exception as e:
            logger.error("RAGAS evaluation failed: %s", e)
            return {"error": str(e), "total_samples": len(dataset)}

    def evaluate_single(self, sample: dict) -> dict:
        """单条样本评估（批量评估的便捷方法）

        Args:
            sample: {question, contexts, answer, ground_truth}

        Returns:
            单条评估结果
        """
        return self.evaluate([sample])
```

- [ ] **Step 3: 改造 run_eval.py 支持 --framework 参数**

修改 `backend/eval/run_eval.py`，在 argparse 中新增 `--framework` 参数：

```python
    parser.add_argument(
        "--framework",
        choices=["custom", "ragas"],
        default="custom",
        help="评估框架: custom (自研 LLM-as-Judge) 或 ragas (RAGAS 标准) (default: custom)"
    )
```

在 `main()` 函数中，根据 framework 选择评估器：

```python
    if args.framework == "ragas":
        from eval.ragas_evaluator import RAGASEvaluator
        # 需要准备 RAGAS 格式的数据集
        evaluator = RAGASEvaluator(llm_client=llm_client)
        # 加载数据集并转换格式
        with open(str(dataset_path), "r", encoding="utf-8") as f:
            raw_dataset = json.load(f)
        ragas_dataset = []
        for sample in raw_dataset:
            rag_result = engine.full_retrieve(sample["question"])
            ragas_dataset.append({
                "question": sample["question"],
                "answer": "",  # 需要生成
                "contexts": rag_result["documents"],
                "ground_truth": sample.get("reference_answer", ""),
            })
        report = evaluator.evaluate(ragas_dataset)
    else:
        evaluator = RAGEvaluator(engine, llm_client)
        report = evaluator.run(str(dataset_path), top_k=args.top_k)
```

- [ ] **Step 4: 更新 print_report 支持 RAGAS 格式**

在 `print_report` 函数中新增 RAGAS 报告格式支持：

```python
    if report.get("framework") == "ragas":
        print("评估框架: RAGAS")
        if "error" in report:
            print(f"  错误: {report['error']}")
            return
        retrieval = report["retrieval"]
        print("检索指标 (RAGAS):")
        if "context_precision" in retrieval:
            print(f"  Context Precision: {retrieval['context_precision']:.4f}")
        if "context_recall" in retrieval:
            print(f"  Context Recall:    {retrieval['context_recall']:.4f}")
        print()
        generation = report["generation"]
        print("生成指标 (RAGAS):")
        print(f"  Faithfulness:     {generation['faithfulness']:.4f}")
        print(f"  Answer Relevancy: {generation['answer_relevancy']:.4f}")
        return  # RAGAS 报告到此结束
```

- [ ] **Step 5: 提交**

```bash
git add backend/eval/ragas_evaluator.py backend/eval/run_eval.py backend/requirements.txt
git commit -m "feat: integrate RAGAS evaluation framework with --framework flag"
```

---

### Task 11: 实现自动化配置对比框架

**Files:**
- Create: `backend/eval/config_comparator.py`

- [ ] **Step 1: 实现 ConfigComparator**

创建 `backend/eval/config_comparator.py`：

```python
"""自动化配置对比评估框架

支持多配置 A/B 对比，输出 Markdown 格式对比报告。
"""
import json
import copy
import logging
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class ComparisonReport:
    """对比报告"""
    baseline: dict
    candidates: list[dict]
    best_config: dict
    summary_table: str


class ConfigComparator:
    """自动化多配置对比评估

    用法：
        comparator = ConfigComparator(engine, evaluator)
        report = comparator.compare(
            base_config={"TOP_K": 5},
            candidates=[{"TOP_K": 10}, {"TOP_K": 20}],
            dataset_path="eval_dataset.json"
        )
    """

    def __init__(self, rag_engine, evaluator):
        """
        Args:
            rag_engine: RAGEngine 实例
            evaluator: RAGEvaluator 实例
        """
        self.engine = rag_engine
        self.evaluator = evaluator

    def compare(self, base_config: dict, candidates: list[dict],
                dataset_path: str, top_k: int = 5) -> ComparisonReport:
        """运行多配置对比评估

        Args:
            base_config: 基准配置
            candidates: 候选配置列表
            dataset_path: 评估数据集路径
            top_k: 检索返回数量

        Returns:
            ComparisonReport 对比报告
        """
        results = []

        # 评估基准配置
        logger.info("Evaluating baseline config: %s", base_config)
        self._apply_config(base_config)
        baseline_result = self.evaluator.run(dataset_path, top_k=top_k)
        results.append({
            "config": base_config,
            "label": "baseline",
            "metrics": baseline_result,
        })

        # 评估候选配置
        for i, candidate in enumerate(candidates):
            logger.info("Evaluating candidate %d: %s", i + 1, candidate)
            self._apply_config(candidate)
            candidate_result = self.evaluator.run(dataset_path, top_k=top_k)
            results.append({
                "config": candidate,
                "label": f"candidate_{i + 1}",
                "metrics": candidate_result,
            })

        # 找出最优配置
        best = max(results, key=lambda r: self._score_config(r["metrics"]))

        # 生成 Markdown 报告
        summary_table = self._generate_markdown_table(results)

        return ComparisonReport(
            baseline=results[0]["metrics"],
            candidates=[r["metrics"] for r in results[1:]],
            best_config=best["config"],
            summary_table=summary_table,
        )

    def _apply_config(self, config: dict):
        """将配置参数应用到 RAG 引擎"""
        for key, value in config.items():
            key_lower = key.lower()
            if hasattr(self.engine, key_lower):
                setattr(self.engine, key_lower, value)
            elif hasattr(self.engine, key):
                setattr(self.engine, key, value)
            else:
                logger.warning("Unknown config key: %s", key)

    @staticmethod
    def _score_config(metrics: dict) -> float:
        """计算配置综合评分（用于排序）

        评分 = MRR * 0.4 + Recall * 0.3 + Faithfulness_norm * 0.3
        """
        retrieval = metrics.get("retrieval", {})
        generation = metrics.get("generation", {})

        mrr = retrieval.get("mrr") or 0.0
        recall = retrieval.get("recall_at_k") or 0.0
        faithfulness = (generation.get("faithfulness") or 0.0) / 5.0  # 归一化到 [0, 1]

        return mrr * 0.4 + recall * 0.3 + faithfulness * 0.3

    @staticmethod
    def _generate_markdown_table(results: list[dict]) -> str:
        """生成 Markdown 格式对比表格"""
        lines = []
        lines.append("# 配置对比评估报告\n")

        # 表头
        headers = ["配置", "MRR", "Recall@K", "Precision", "Faithfulness", "Relevancy", "综合评分"]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # 数据行
        for r in results:
            config_str = str(r["config"]) if r["config"] else "默认"
            retrieval = r["metrics"].get("retrieval", {})
            generation = r["metrics"].get("generation", {})

            mrr_val = retrieval.get("mrr")
            recall_val = retrieval.get("recall_at_k")
            precision_val = retrieval.get("precision")
            faith_val = generation.get("faithfulness")
            relevancy_val = generation.get("relevancy")
            score = ConfigComparator._score_config(r["metrics"])

            row = [
                f"`{config_str}`",
                f"{mrr_val:.3f}" if mrr_val is not None else "N/A",
                f"{recall_val:.3f}" if recall_val is not None else "N/A",
                f"{precision_val:.3f}" if precision_val is not None else "N/A",
                f"{faith_val:.1f}/5" if faith_val is not None else "N/A",
                f"{relevancy_val:.1f}/5" if relevancy_val is not None else "N/A",
                f"{score:.3f}",
            ]
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)


def main():
    """CLI 入口"""
    parser = argparse.ArgumentParser(description="RAG 配置对比评估工具")
    parser.add_argument("--dataset", required=True, help="评估数据集路径")
    parser.add_argument("--compare", action="append", required=True,
                        help="对比维度，格式: key:value1,value2 (可多次指定)")
    parser.add_argument("--output", default="comparison_report.md", help="输出报告路径")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回数量")

    args = parser.parse_args()

    # 解析对比维度
    comparisons = {}
    for spec in args.compare:
        key, values_str = spec.split(":", 1)
        values = values_str.split(",")
        comparisons[key] = values

    # 生成配置组合
    configs = _generate_config_combinations(comparisons)

    # 初始化引擎和评估器
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    backend_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(backend_dir))

    from core.config import config
    from core.rag_engine import RAGEngine
    from core.llm_client import LLMClient
    from eval.evaluator import RAGEvaluator

    engine = RAGEngine(config)
    llm_client = LLMClient(config.MIMO_API_KEY, config.MIMO_API_BASE, config.MIMO_MODEL)
    evaluator = RAGEvaluator(engine, llm_client)

    comparator = ConfigComparator(engine, evaluator)
    report = comparator.compare(
        base_config={},
        candidates=configs,
        dataset_path=args.dataset,
        top_k=args.top_k,
    )

    # 输出报告
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report.summary_table)

    print(report.summary_table)
    print(f"\n报告已保存到: {args.output}")
    print(f"最优配置: {report.best_config}")


def _generate_config_combinations(comparisons: dict) -> list[dict]:
    """从对比维度生成配置组合"""
    if not comparisons:
        return [{}]

    keys = list(comparisons.keys())
    values = [comparisons[k] for k in keys]

    # 笛卡尔积
    from itertools import product
    configs = []
    for combo in product(*values):
        config_dict = {}
        for k, v in zip(keys, combo):
            # 尝试转换为数值
            try:
                config_dict[k] = int(v)
            except ValueError:
                try:
                    config_dict[k] = float(v)
                except ValueError:
                    config_dict[k] = v
        configs.append(config_dict)

    return configs


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行基础验证**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend && python -c "from eval.config_comparator import ConfigComparator, ComparisonReport; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add backend/eval/config_comparator.py
git commit -m "feat: add ConfigComparator for automated multi-config evaluation"
```

---

## 完成验证

### Task 12: 全量测试与集成验证

- [ ] **Step 1: 运行全部单元测试**

Run: `cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG && python -m pytest tests/ -v --timeout=120 2>/dev/null || echo "部分测试需要模型/数据库"`
Expected: 所有新增测试 PASS，无回归

- [ ] **Step 2: 验证新配置项**

检查 `config.py` 中新增的配置项是否正确加载：
- `CHUNKING_STRATEGY`
- `CITATION_VERIFY_ENABLED`（已有，验证已接线）
- `RETRIEVAL_REFETCH_ENABLED`（已有，验证已接线）

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "chore: complete RAG gap remediation - factory pattern, multimodal PDF, evaluation framework"
```
