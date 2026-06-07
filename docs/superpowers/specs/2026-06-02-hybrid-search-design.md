---
title: 混合检索（Hybrid Search）设计文档
date: 2026-06-02
status: approved
---

# 混合检索设计

## 背景

当前 RAG 系统仅使用向量检索（ChromaDB + bge-small-zh-v1.5），对关键词精确匹配场景（函数名、错误码、API 名称）召回率不足。需要加入 BM25 关键词检索，通过 RRF 融合提升检索质量。

## 架构

```
用户 Query
    │
    ├──→ 向量检索 (ChromaDB, top-10)
    │         │
    ├──→ BM25 检索 (rank_bm25, top-10)
    │         │
    └────── RRF 融合 (k=60) ──→ 取 top-5 ──→ LLM
```

## 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| BM25 引擎 | rank_bm25 | 零外部依赖，纯 Python，内存索引 |
| 中文分词 | jieba | 成熟稳定，足够覆盖技术文档场景 |
| 融合算法 | RRF (k=60) | 论文默认值，无需调参 |

## 改动文件

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `backend/requirements.txt` | 修改 | 新增 rank_bm25, jieba |
| `backend/core/bm25_retriever.py` | 新建 | BM25 索引构建与检索 |
| `backend/core/rag_engine.py` | 修改 | 加入双路召回 + RRF 融合 |
| `backend/core/config.py` | 修改 | 新增 BM25_TOP_K, RRF_K 参数 |

## 详细设计

### BM25Retriever 类

```python
class BM25Retriever:
    def __init__(self):
        self.bm25 = None
        self.doc_ids = []      # 与 BM25 内部文档顺序对齐
        self.doc_map = {}      # id -> {text, metadata}

    def build_index(self, documents: list[dict]):
        """从文档列表构建 BM25 索引
        documents: [{"id": str, "text": str, "metadata": dict}, ...]
        """
        # jieba 分词 → BM25Okapi

    def search(self, query: str, top_k: int) -> list[dict]:
        """返回 [{"id": str, "score": float, "text": str, "metadata": dict}, ...]"""

    def add_documents(self, documents: list[dict]):
        """增量添加文档，重建索引"""

    def delete_by_source(self, source: str):
        """按来源删除，重建索引"""
```

### RRF 螽合逻辑

```python
def hybrid_retrieve(self, query: str) -> dict:
    # 1. 向量检索 top-K
    vector_results = self.vector_store.query(query_embedding, top_k=self.bm25_top_k)
    # 2. BM25 检索 top-K
    bm25_results = self.bm25_retriever.search(query, top_k=self.bm25_top_k)
    # 3. RRF 融合
    fused = reciprocal_rank_fusion(vector_results, bm25_results, k=self.rrf_k)
    # 4. 取 top-5
    return fused[:self.top_k]
```

RRF 公式：对每个文档，`score = Σ 1/(k + rank_i)`，其中 `rank_i` 是该文档在每路召回中的排名。

### 配置参数

```python
BM25_TOP_K: int = 10       # 每路召回数量
RRF_K: int = 60            # RRF 公式常数
```

### 数据流

**文档入库时：**
1. 原有流程：分块 → embedding → 写入 ChromaDB
2. 新增：分块文本 + metadata → 写入 BM25 索引

**查询时：**
1. 原始 query → jieba 分词 → BM25 检索 top-10
2. 原始 query → embedding → 向量检索 top-10
3. RRF 融合 → 排序 → 取 top-5
4. 构建 prompt → 送 LLM

## 不改动的部分

- `vector_store.py` — 保持纯向量职责不变
- `document_processor.py` — 分块逻辑不变
- `embedding_service.py` — 不变
- `llm_client.py` — 不变
- 前端 — 不需要改动

## 依赖

新增 Python 包：
- `rank-bm25>=0.2.2`
- `jieba>=0.42.1`
