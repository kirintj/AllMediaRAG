# 语义相似度切分（Semantic Chunking）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将固定长度切分替换为语义相似度切分，用 embedding 余弦相似度检测话题边界，代码块作为不可拆分单元。

**Architecture:** 文本 → 提取代码块占位符 → 句子切分 → 句子级 embedding → 相邻相似度计算 → 动态阈值切分 → 合并为 chunk → 恢复代码块

**Tech Stack:** numpy (相似度计算), 复用现有 EmbeddingService

---

### Task 1: 添加配置参数

**Files:**
- Modify: `backend/core/config.py:33`

- [ ] **Step 1: 添加语义切分配置参数**

在 `RRF_K: int = 60` 行之后添加：

```python
    # 语义切分参数
    SEMANTIC_CHUNK_PERCENTILE: int = 25    # 相似度阈值百分位
    SEMANTIC_CHUNK_MIN_SENTENCES: int = 2  # 每个 chunk 最少句子数
    SEMANTIC_CHUNK_MAX_SENTENCES: int = 20 # 每个 chunk 最多句子数
```

完整文件：

```python
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """配置管理类，从环境变量加载配置"""

    # MiMo API 配置
    MIMO_API_KEY: str = os.getenv("MIMO_API_KEY", "")
    MIMO_API_BASE: str = os.getenv("MIMO_API_BASE", "https://api.siliconflow.cn/v1")
    MIMO_MODEL: str = os.getenv("MIMO_MODEL", "mimo-v2.5")

    # Embedding 模型配置
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "./models/bge-small-zh-v1.5")

    # Chroma 配置
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # 数据目录
    DATA_DIR: str = os.getenv("DATA_DIR", "./data/python-docs")

    # RAG 参数
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
    MAX_HISTORY_TURNS: int = 5

    # BM25 + RRF 参数
    BM25_TOP_K: int = 10       # 每路召回数量
    RRF_K: int = 60            # RRF 公式常数

    # 语义切分参数
    SEMANTIC_CHUNK_PERCENTILE: int = 25    # 相似度阈值百分位
    SEMANTIC_CHUNK_MIN_SENTENCES: int = 2  # 每个 chunk 最少句子数
    SEMANTIC_CHUNK_MAX_SENTENCES: int = 20 # 每个 chunk 最多句子数


config = Config()
```

- [ ] **Step 2: 验证配置加载**

Run: `cd "D:\HuaweiMoveData\Users\28966\Desktop\Agent智能助手\backend" && python -c "from core.config import config; print(f'P={config.SEMANTIC_CHUNK_PERCENTILE}, MIN={config.SEMANTIC_CHUNK_MIN_SENTENCES}, MAX={config.SEMANTIC_CHUNK_MAX_SENTENCES}')"`
Expected: `P=25, MIN=2, MAX=20`

---

### Task 2: 重写 DocumentProcessor 实现语义切分

**Files:**
- Modify: `backend/core/document_processor.py`

- [ ] **Step 1: 重写 document_processor.py**

将整个文件替换为：

```python
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
        # 先按段落分隔
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
                # 切分点
                if len(current_chunk) >= self.min_sentences:
                    chunks.append(current_chunk)
                    current_chunk = [i + 1]
                else:
                    # 不够最小句子数，继续累积
                    current_chunk.append(i + 1)
            else:
                current_chunk.append(i + 1)

            # 超过最大句子数，强制切分
            if len(current_chunk) >= self.max_sentences:
                chunks.append(current_chunk)
                current_chunk = []

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def process_document(self, html_content: str, source: str) -> list[dict]:
        """完整文档处理流程，返回带元数据的 chunks

        使用语义切分替代固定长度切分。
        """
        text = self.parse_html(html_content)
        sections = self.split_by_headings(text)

        all_chunks = []
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
                all_chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "source": source,
                        "section": section["heading"] or "概述",
                        "chunk_index": len(all_chunks),
                    }
                })
                continue

            # 句子级 embedding
            if self.embedding_service:
                embeddings = self.embedding_service.encode(sentences)
            else:
                # 无 embedding 服务时退化为按段落切分
                embeddings = None

            # 语义切分
            if embeddings:
                sentence_groups = self.semantic_chunk(sentences, embeddings)
            else:
                # 退化：每 min_sentences 个句子一组
                sentence_groups = [
                    list(range(i, min(i + self.min_sentences, len(sentences))))
                    for i in range(0, len(sentences), self.min_sentences)
                ]

            # 合并为 chunk
            for group_indices in sentence_groups:
                chunk_sentences = [sentences[i] for i in group_indices]
                chunk_text = "\n".join(chunk_sentences)
                chunk_text = self._restore_code_blocks(chunk_text, code_blocks)

                if chunk_text.strip():
                    all_chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "source": source,
                            "section": section["heading"] or "概述",
                            "chunk_index": len(all_chunks),
                        }
                    })

        return all_chunks

    def process_file(self, file_path: str) -> list[dict]:
        """处理文件，自动识别格式"""
        content = self.read_file(file_path)
        source = os.path.basename(file_path)
        return self.process_document(content, source)
```

- [ ] **Step 2: 验证语法正确**

Run: `cd "D:\HuaweiMoveData\Users\28966\Desktop\Agent智能助手\backend" && python -c "from core.document_processor import DocumentProcessor; print('OK')"`
Expected: `OK`

---

### Task 3: 更新 RAGEngine 适配新 DocumentProcessor

**Files:**
- Modify: `backend/core/rag_engine.py`

- [ ] **Step 1: 修改 RAGEngine 的 __init__ 和 ingest_document**

`DocumentProcessor` 的构造函数签名变了（从 `(chunk_size, chunk_overlap)` 改为 `(config)`），且需要注入 embedding_service。

在 `rag_engine.py` 中，将 `__init__` 里的：

```python
        self.document_processor = DocumentProcessor(
            config.CHUNK_SIZE,
            config.CHUNK_OVERLAP
        )
```

替换为：

```python
        self.document_processor = DocumentProcessor(config)
        self.document_processor.set_embedding_service(self.embedding_service)
```

完整的 `__init__` 方法应为：

```python
    def __init__(self, config):
        self.embedding_service = EmbeddingService(config.EMBEDDING_MODEL_PATH)
        self.vector_store = VectorStore(config.CHROMA_PERSIST_DIR)
        self.llm_client = LLMClient(
            config.MIMO_API_KEY,
            config.MIMO_API_BASE,
            config.MIMO_MODEL
        )
        self.document_processor = DocumentProcessor(config)
        self.document_processor.set_embedding_service(self.embedding_service)
        self.bm25_retriever = BM25Retriever()

        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
        self.max_history_turns = config.MAX_HISTORY_TURNS
        self.conversation_history: list[dict] = []
```

- [ ] **Step 2: 验证完整导入**

Run: `cd "D:\HuaweiMoveData\Users\28966\Desktop\Agent智能助手\backend" && python -c "from main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/core/config.py backend/core/document_processor.py backend/core/rag_engine.py
git commit -m "feat: semantic chunking based on embedding similarity"
```
