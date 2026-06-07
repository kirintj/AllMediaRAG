# 混合检索（Hybrid Search）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 RAG 系统加入 BM25 关键词检索，通过 RRF 融合与向量检索互补，提升关键词精确匹配场景的召回率。

**Architecture:** 双路召回（向量 + BM25）→ RRF 融合排序 → 取 top-N 送 LLM。BM25 索引存内存，每次启动从 ChromaDB 重建。

**Tech Stack:** rank_bm25, jieba, ChromaDB (unchanged), sentence-transformers (unchanged)

---

### Task 1: 添加依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 添加 rank_bm25 和 jieba 到 requirements.txt**

```txt
fastapi>=0.104.0
uvicorn>=0.24.0
python-multipart>=0.0.6
sse-starlette>=1.8.0
rank-bm25>=0.2.2
jieba>=0.42.1
```

- [ ] **Step 2: 安装依赖**

Run: `cd backend && pip install rank-bm25 jieba`
Expected: Successfully installed

- [ ] **Step 3: 验证导入**

Run: `python -c "from rank_bm25 import BM25Okapi; import jieba; print('OK')"`
Expected: `OK`

---

### Task 2: 添加配置参数

**Files:**
- Modify: `backend/core/config.py:29-30`

- [ ] **Step 1: 在 Config 类末尾添加 BM25 和 RRF 参数**

在 `SIMILARITY_THRESHOLD` 行之后添加：

```python
    # BM25 + RRF 参数
    BM25_TOP_K: int = 10       # 每路召回数量
    RRF_K: int = 60            # RRF 公式常数
```

完整文件应为：

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


config = Config()
```

- [ ] **Step 2: 验证配置加载**

Run: `cd backend && python -c "from core.config import config; print(f'BK={config.BM25_TOP_K}, RRF={config.RRF_K}')"`
Expected: `BK=10, RRF=60`

---

### Task 3: 创建 BM25Retriever

**Files:**
- Create: `backend/core/bm25_retriever.py`

- [ ] **Step 1: 创建 BM25Retriever 类**

```python
import jieba
from rank_bm25 import BM25Okapi


class BM25Retriever:
    """BM25 关键词检索器"""

    def __init__(self):
        self.bm25 = None
        self.doc_ids = []
        self.doc_map = {}

    def _tokenize(self, text: str) -> list[str]:
        """jieba 分词，过滤空白 token"""
        return [w for w in jieba.lcut(text) if w.strip()]

    def build_index(self, documents: list[dict]):
        """从文档列表构建 BM25 索引

        Args:
            documents: [{"id": str, "text": str, "metadata": dict}, ...]
        """
        self.doc_ids = []
        self.doc_map = {}
        tokenized_corpus = []

        for doc in documents:
            doc_id = doc["id"]
            self.doc_ids.append(doc_id)
            self.doc_map[doc_id] = {
                "text": doc["text"],
                "metadata": doc["metadata"],
            }
            tokenized_corpus.append(self._tokenize(doc["text"]))

        self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, query: str, top_k: int) -> list[dict]:
        """检索最相似的文档

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            [{"id": str, "score": float, "text": str, "metadata": dict}, ...]
        """
        if not self.bm25 or not self.doc_ids:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        # 按分数降序取 top_k
        ranked = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]

        results = []
        for idx, score in ranked:
            doc_id = self.doc_ids[idx]
            doc = self.doc_map[doc_id]
            results.append({
                "id": doc_id,
                "score": float(score),
                "text": doc["text"],
                "metadata": doc["metadata"],
            })

        return results

    def add_documents(self, documents: list[dict]):
        """增量添加文档（重建索引）

        Args:
            documents: [{"id": str, "text": str, "metadata": dict}, ...]
        """
        for doc in documents:
            doc_id = doc["id"]
            if doc_id not in self.doc_map:
                self.doc_ids.append(doc_id)
                self.doc_map[doc_id] = {
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                }

        self._rebuild()

    def delete_by_source(self, source: str):
        """按来源删除文档（重建索引）

        Args:
            source: 文档来源标识
        """
        ids_to_remove = set()
        for doc_id, doc in self.doc_map.items():
            if doc["metadata"].get("source") == source:
                ids_to_remove.add(doc_id)

        self.doc_ids = [i for i in self.doc_ids if i not in ids_to_remove]
        for doc_id in ids_to_remove:
            del self.doc_map[doc_id]

        self._rebuild()

    def delete_all(self):
        """清空索引"""
        self.bm25 = None
        self.doc_ids = []
        self.doc_map = {}

    def _rebuild(self):
        """重建 BM25 索引"""
        if not self.doc_ids:
            self.bm25 = None
            return

        tokenized_corpus = [
            self._tokenize(self.doc_map[doc_id]["text"])
            for doc_id in self.doc_ids
        ]
        self.bm25 = BM25Okapi(tokenized_corpus)
```

- [ ] **Step 2: 验证 BM25Retriever 基本功能**

Run: `cd backend && python -c "
from core.bm25_retriever import BM25Retriever
r = BM25Retriever()
r.build_index([
    {'id': '1', 'text': 'Python 列表推导式用法', 'metadata': {'source': 'a.html', 'section': '列表'}},
    {'id': '2', 'text': 'Python 字典操作方法', 'metadata': {'source': 'b.html', 'section': '字典'}},
    {'id': '3', 'text': '列表排序和反转', 'metadata': {'source': 'c.html', 'section': '排序'}},
])
results = r.search('列表排序', top_k=2)
for res in results:
    print(f'{res[\"id\"]}: {res[\"text\"]} (score={res[\"score\"]:.2f})')
"`
Expected: 结果包含 id=3（列表排序）和 id=1（列表推导式），且 id=3 排在前面

- [ ] **Step 3: 验证 delete_by_source**

Run: `cd backend && python -c "
from core.bm25_retriever import BM25Retriever
r = BM25Retriever()
r.build_index([
    {'id': '1', 'text': 'aaa', 'metadata': {'source': 'a.html', 'section': 's'}},
    {'id': '2', 'text': 'bbb', 'metadata': {'source': 'b.html', 'section': 's'}},
])
r.delete_by_source('a.html')
print(f'count={len(r.doc_ids)}, ids={r.doc_ids}')
"`
Expected: `count=1, ids=['2']`

---

### Task 4: 集成混合检索到 RAGEngine

**Files:**
- Modify: `backend/core/rag_engine.py`

- [ ] **Step 1: 修改 rag_engine.py 导入和初始化**

在 `rag_engine.py` 顶部添加 BM25Retriever 导入：

```python
import os
from typing import Generator

from core.embedding_service import EmbeddingService
from core.vector_store import VectorStore
from core.llm_client import LLMClient
from core.document_processor import DocumentProcessor
from core.bm25_retriever import BM25Retriever
```

在 `__init__` 方法中初始化 BM25Retriever 和新配置参数（在 `self.document_processor = ...` 之后）：

```python
        self.bm25_retriever = BM25Retriever()

        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
        self.max_history_turns = config.MAX_HISTORY_TURNS
        self.conversation_history: list[dict] = []
```

- [ ] **Step 2: 修改 ingest_document 方法，同时写入 BM25 索引**

替换 `ingest_document` 方法：

```python
    def ingest_document(self, file_path: str) -> int:
        """导入文档，返回 chunk 数量"""
        source = os.path.basename(file_path)
        chunks = self.document_processor.process_file(file_path)

        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = self.embedding_service.encode(texts)

        # 写入向量库
        self.vector_store.add_documents(texts, embeddings, metadatas)

        # 写入 BM25 索引（需要从向量库获取生成的 id）
        # 重新查询刚写入的文档以获取 id
        # 更好的方式：先生成 id，两边共用
        import uuid
        doc_ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        bm25_docs = [
            {"id": doc_id, "text": text, "metadata": meta}
            for doc_id, text, meta in zip(doc_ids, texts, metadatas)
        ]
        self.bm25_retriever.add_documents(bm25_docs)

        return len(chunks)
```

**注意：** 向量库和 BM25 使用各自的 id 体系，不影响功能。BM25 的 id 仅用于内部管理。

- [ ] **Step 3: 添加 RRF 融合方法和混合检索方法**

在 `filter_by_similarity` 方法之后添加：

```python
    def reciprocal_rank_fusion(
        self,
        results_list: list[list[dict]],
        k: int
    ) -> list[dict]:
        """RRF 融合多路召回结果

        Args:
            results_list: 多路召回结果，每路为 [{"id": str, ...}, ...]
            k: RRF 常数

        Returns:
            融合后的排序结果
        """
        score_map = {}  # id -> (total_score, doc_dict)

        for results in results_list:
            for rank, doc in enumerate(results):
                doc_id = doc["id"]
                rrf_score = 1.0 / (k + rank + 1)  # rank 从 0 开始，+1 对齐

                if doc_id in score_map:
                    score_map[doc_id] = (
                        score_map[doc_id][0] + rrf_score,
                        score_map[doc_id][1],
                    )
                else:
                    score_map[doc_id] = (rrf_score, doc)

        # 按融合分数降序排序
        sorted_docs = sorted(score_map.values(), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in sorted_docs]

    def hybrid_retrieve(self, query: str) -> dict:
        """混合检索：向量 + BM25，RRF 融合

        Args:
            query: 用户查询

        Returns:
            检索结果，格式与原 retrieve 一致
        """
        # 1. 向量检索
        query_embedding = self.embedding_service.encode_single(query)
        vector_raw = self.vector_store.query(query_embedding, self.bm25_top_k)

        # 将向量结果转为统一格式
        vector_results = []
        for doc, meta, dist in zip(
            vector_raw["documents"],
            vector_raw["metadatas"],
            vector_raw["distances"],
        ):
            vector_results.append({
                "id": f"vec_{hash(doc)}",  # 用内容 hash 作为 id
                "text": doc,
                "metadata": meta,
                "distance": dist,
            })

        # 2. BM25 检索
        bm25_raw = self.bm25_retriever.search(query, self.bm25_top_k)
        bm25_results = [
            {"id": r["id"], "text": r["text"], "metadata": r["metadata"]}
            for r in bm25_raw
        ]

        # 3. RRF 融合
        fused = self.reciprocal_rank_fusion(
            [vector_results, bm25_results], k=self.rrf_k
        )

        # 4. 取 top_k，转换为 retrieve 返回格式
        top_docs = fused[: self.top_k]
        return {
            "documents": [d["text"] for d in top_docs],
            "metadatas": [d["metadata"] for d in top_docs],
            "distances": [d.get("distance", 0.0) for d in top_docs],
        }
```

- [ ] **Step 4: 修改 retrieve 方法，使用混合检索**

替换 `retrieve` 方法：

```python
    def retrieve(self, query: str, top_k: int = None) -> dict:
        """检索相关文档（混合检索）

        Args:
            query: 用户查询
            top_k: 未使用，保留接口兼容

        Returns:
            检索结果
        """
        return self.hybrid_retrieve(query)
```

- [ ] **Step 5: 添加 delete_by_source 联动**

在 `rag_engine.py` 中没有 `delete_by_source` 方法，但 `api/documents.py` 直接调用了 `engine.vector_store.delete_by_source`。需要确保 BM25 也同步删除。

在 `rag_engine.py` 的 `clear_history` 方法之前添加：

```python
    def delete_by_source(self, source: str):
        """按来源删除文档（向量库 + BM25）"""
        self.vector_store.delete_by_source(source)
        self.bm25_retriever.delete_by_source(source)

    def delete_all(self):
        """清空所有文档"""
        self.vector_store.delete_all()
        self.bm25_retriever.delete_all()
```

- [ ] **Step 6: 更新 api/documents.py 使用 RAGEngine 的删除方法**

修改 `backend/api/documents.py`，将 `engine.vector_store.delete_by_source(file.filename)` 改为 `engine.delete_by_source(file.filename)`，`engine.vector_store.delete_all()` 改为 `engine.delete_all()`。

- [ ] **Step 7: 验证完整导入**

Run: `cd backend && python -c "from main import app; print('OK')"`
Expected: `OK`

- [ ] **Step 8: 启动服务验证**

Run: `cd backend && python main.py`
Expected: 服务在 8000 端口启动，无报错

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/core/config.py backend/core/bm25_retriever.py backend/core/rag_engine.py backend/api/documents.py
git commit -m "feat: add hybrid search with BM25 + RRF fusion"
```
