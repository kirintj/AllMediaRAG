# 向量数据库抽象层重构设计文档

## 概述

将 DataPilotAI 的向量存储从 ChromaDB 单一实现重构为 Elasticsearch-only 架构，参照 RAGFlow 的 `DocStoreConnection` 设计重写 `VectorStoreProvider` 接口，实现表达式驱动的统一查询，将混合检索（向量 + 全文）下沉到存储层。

## 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 向量数据库 | 仅 Elasticsearch 8.x | 生产最成熟，原生混合检索 |
| 旧后端处理 | 全部删除（ChromaDB / Simple / pgvector） | 简化维护，统一到一个后端 |
| 接口设计 | 与 RAGFlow 对齐 | 表达式类 + 统一 search() + CRUD |
| 混合检索位置 | 下沉到存储层 | ES 原生 knn+bool 单次查询，性能最优 |
| BM25Retriever | 删除 | ES 原生全文检索替代 |
| 索引结构 | 多租户模式 allrag_{tenant_id} | 预留多租户，后续无需迁移 |
| 分词方案 | whitespace + jieba 预分词 | 与 RAGFlow 一致，分词策略可控 |
| 向量维度 | 可配置 EMBEDDING_DIM，默认 1024 | 适配不同 Embedding 模型 |

## 架构

```
                         ┌─────────────────────┐
                         │  Elasticsearch 8.x  │
                         │                     │
                         │  index: allrag_{tenant_id}  │
                         │  fields:            │
                         │    text (whitespace) │
                         │    text_raw          │
                         │    embedding (HNSW)  │
                         │    source, kb_id     │
                         │    tenant_id, meta   │
                         └──────────┬──────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              search()        insert()         delete()
           (表达式驱动)       (批量写入)       (条件删除)
                    │               │               │
         RetrievalPipeline   IngestionService    API层
```

## 查询表达式

与 RAGFlow 对齐的表达式体系：

```python
class MatchTextExpr:
    """全文检索表达式"""
    fields: list[str]           # 检索字段 ["text"]
    matching_text: str          # 查询文本
    topn: int                   # 返回数量
    extra_options: dict | None  # {"minimum_should_match": "70%"}

class MatchDenseExpr:
    """向量检索表达式"""
    embedding_data: list[float] # 查询向量
    topn: int = 10              # 返回数量
    distance_type: str = "cosine"
    extra_options: dict | None  # {"similarity": 0.1} 阈值

class FusionExpr:
    """多信号融合表达式"""
    method: str                 # "weighted_sum" / "rrf"
    topn: int                   # 融合后返回数量
    fusion_params: dict | None  # {"weights": "0.7,0.3"}

class OrderByExpr:
    """排序表达式，链式调用"""
    def asc(field) -> self
    def desc(field) -> self
```

## VectorStoreProvider 接口

```python
class VectorStoreProvider(ABC):

    # ── 连接信息 ──
    def db_type(self) -> str
    def health(self) -> dict

    # ── 索引管理 ──
    def create_idx(self, index_name: str, vector_size: int)
    def delete_idx(self, index_name: str)
    def index_exist(self, index_name: str) -> bool

    # ── 统一查询（核心方法）──
    def search(
        self,
        select_fields: list[str],           # ["id", "text", "source", "metadata"]
        condition: dict | None,             # {"source": "a.pdf"} 过滤条件
        match_expressions: list[MatchExpr], # [MatchTextExpr, MatchDenseExpr, FusionExpr]
        order_by: OrderByExpr | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> dict
    # 返回: {"documents": [...], "metadatas": [...], "distances": [...], "total": int}

    # ── CRUD ──
    def insert(self, rows: list[dict]) -> list[str]
    # rows 每项: {"id", "text", "text_raw", "embedding", "source", "metadata", ...}
    # 返回: 错误列表（空 = 全部成功）

    def get(self, doc_id: str) -> dict | None
    def delete(self, condition: dict) -> int
    def update(self, condition: dict, new_value: dict) -> bool

    # ── 结果解析（便捷方法）──
    def get_total(self, res: dict) -> int
    def get_doc_ids(self, res: dict) -> list[str]
    def get_fields(self, res: dict, fields: list[str]) -> dict[str, dict]
```

### 旧接口迁移对照

| 旧方法 | 新等效调用 |
|--------|-----------|
| `add_documents(texts, embeddings, metadatas)` | `insert(rows)` |
| `query(embedding, top_k)` | `search(select_fields, None, [MatchDenseExpr(...)])` |
| `delete_by_source(source)` | `delete({"source": source})` |
| `get_all_sources()` | `search(["source"], None, [], limit=9999)` + 去重 |
| `get_document_count()` | ES count API |
| `delete_all()` | `delete_idx()` + `create_idx()` |
| `get_all_documents()` | `search(["id", "text", "metadata"], None, [], limit=99999)` |
| `get_source_details()` | ES terms 聚合 on source |

## ES 索引 Mapping

索引名：`allrag_{tenant_id}`，默认 `allrag_default`。

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
  },
  "mappings": {
    "properties": {
      "text":       { "type": "text", "analyzer": "whitespace" },
      "text_raw":   { "type": "text", "index": false },
      "embedding":  { "type": "dense_vector", "dims": 1024, "index": true, "similarity": "cosine", "index_options": { "type": "hnsw", "m": 16, "ef_construction": 100 } },
      "source":     { "type": "keyword" },
      "kb_id":      { "type": "keyword" },
      "tenant_id":  { "type": "keyword" },
      "chunk_id":   { "type": "keyword" },
      "metadata":   { "type": "object", "enabled": false },
      "created_at": { "type": "date" }
    }
  }
}
```

字段说明：
- `text`：jieba 预分词后空格连接，whitespace 分析器检索
- `text_raw`：原始文本，不建索引，仅存储用于展示
- `embedding`：dense_vector HNSW 索引，dims 从 EMBEDDING_DIM 配置读取
- `source`：文档来源文件名，过滤和聚合用
- `kb_id`：预留知识库 ID
- `tenant_id`：预留租户 ID
- `metadata`：原始 metadata 存储，不建索引

## ElasticsearchStore 实现

### 分词预处理

写入前用 jieba 对 text 字段预分词：

```python
def _tokenize(self, text: str) -> str:
    """jieba 分词后用空格连接"""
    return " ".join(jieba.cut(text))
```

`insert()` 方法中：`text` 字段存分词结果，`text_raw` 存原始文本。

### 混合检索实现

`search()` 方法内部根据 `match_expressions` 构建 ES 查询：

```python
def search(self, select_fields, condition, match_expressions, ...):
    text_expr = find_expr(match_expressions, MatchTextExpr)
    dense_expr = find_expr(match_expressions, MatchDenseExpr)
    fusion_expr = find_expr(match_expressions, FusionExpr)

    if text_expr and dense_expr and fusion_expr:
        # 混合检索：knn + bool query，ES 内部 RRF 融合
        body = {
            "knn": {
                "field": "embedding",
                "query_vector": dense_expr.embedding_data,
                "k": dense_expr.topn,
                "num_candidates": dense_expr.topn * 10,
            },
            "query": {
                "match": {
                    "text": {
                        "query": text_expr.matching_text,
                        "minimum_should_match": text_expr.extra_options.get("minimum_should_match", "70%") if text_expr.extra_options else "70%",
                    }
                }
            },
            "size": limit,
        }
        # 权重通过 knn.boost 和 query.boost 实现
    elif dense_expr:
        # 纯向量检索
        body = {"knn": {...}, "size": limit}
    elif text_expr:
        # 纯全文检索
        body = {"query": {"match": {...}}, "size": limit}

    # 添加 condition 过滤
    if condition:
        body["query"] = {"bool": {"must": [...], "filter": [term queries]}}

    return self._client.search(index=self._index_name, body=body)
```

### 索引名计算

```python
@property
def _index_name(self) -> str:
    return f"{self._index_prefix}_{self._tenant_id}"

def __init__(self, hosts, index_prefix="allrag", tenant_id="default", ...):
    self._index_prefix = index_prefix
    self._tenant_id = tenant_id
    self._client = Elasticsearch(hosts, ...)
    self._ensure_index(self._index_name)
```

## RetrievalPipeline 改造

### 当前逻辑（删除）

```
向量检索(vector_store.query) + BM25(bm25_retriever.search) → RRF 融合 → Rerank
```

### 改造后

```
ES.search([MatchTextExpr, MatchDenseExpr, FusionExpr]) → Rerank
```

```python
class RetrievalPipeline:
    def __init__(self, infra):
        self.doc_store = infra.vector_store
        # 删除: self.bm25_retriever
        ...

    def full_retrieve(self, query, ...):
        # 1. 查询理解（保留现有 classifier/router）
        intent = self.classifier.classify(query)

        # 2. 构建表达式
        embedding = self.embedding_service.encode([query])[0]
        expressions = [
            MatchTextExpr(fields=["text"], matching_text=query, topn=self.bm25_top_k),
            MatchDenseExpr(embedding_data=embedding, topn=self.top_k),
            FusionExpr(method="weighted_sum", topn=self.top_k,
                       fusion_params={"weights": f"{bm25_weight},{vector_weight}"}),
        ]

        # 3. 单次 ES 查询
        results = self.doc_store.search(
            select_fields=["id", "text_raw", "source", "metadata"],
            condition=None,
            match_expressions=expressions,
            limit=self.rerank_top_k,
        )

        # 4. Rerank（保留现有 reranker）
        ...
```

### 删除的代码

- `RetrievalPipeline._rebuild_bm25_index()` — 不再需要
- `RetrievalPipeline.vector_search()` — 被 `doc_store.search()` 替代
- 所有 `bm25_retriever` 调用

## IngestionService 改造

```python
class IngestionService:
    def ingest_document(self, file_path: str) -> int:
        chunks, precomputed_embeddings = self._document_processor.process_file(file_path)
        ...

        # jieba 预分词
        rows = []
        for text, emb, meta in zip(texts, embeddings, metadatas):
            rows.append({
                "id": str(uuid.uuid4()),
                "text": self._tokenize(text),     # 分词后
                "text_raw": text,                  # 原始文本
                "embedding": emb,
                "source": meta.get("source", ""),
                "metadata": meta,
                "tenant_id": self._tenant_id,
                "created_at": datetime.utcnow().isoformat(),
            })

        errors = self._doc_store.insert(rows)
        return len(chunks)

    def _tokenize(self, text: str) -> str:
        return " ".join(jieba.cut(text))
```

## InfraBundle 改造

```python
@dataclass
class InfraBundle:
    # 删除: bm25_retriever, bm25_ready
    vector_store: VectorStoreProvider  # ElasticsearchStore 实例
    embedding_service: ...
    document_processor: ...
    rerank_manager: ...
    cache_manager: ...
    ...
```

## 配置

### config.py 新增

```python
# -- Elasticsearch ------------------------------------------------
ES_HOSTS: str = "http://localhost:9200"
ES_USERNAME: str = ""
ES_PASSWORD: str = ""
ES_INDEX_PREFIX: str = "allrag"
ES_NUMBER_OF_SHARDS: int = 1
ES_NUMBER_OF_REPLICAS: int = 0
EMBEDDING_DIM: int = 1024
DEFAULT_TENANT_ID: str = "default"
```

### config.py 删除

```python
CHROMA_PERSIST_DIR: str = "./chroma_db"    # 删除
BM25_PERSIST_DIR: str = ""                 # 删除
```

### .env.example 新增

```env
# ---------- Elasticsearch ----------
ES_HOSTS=http://localhost:9200
ES_USERNAME=
ES_PASSWORD=
ES_INDEX_PREFIX=allrag
EMBEDDING_DIM=1024
DEFAULT_TENANT_ID=default
```

### requirements.txt 新增

```
# === Elasticsearch ===
elasticsearch>=8.0.0,<9.0.0
```

### requirements.txt 删除

```
chromadb>=0.4.0        # 删除
pgvector>=0.2.0        # 删除
psycopg2-binary>=2.9.0 # 删除
alembic>=1.13.0        # 删除
rank-bm25>=0.2.2       # 删除（ES 原生替代）
```

## Docker Compose 改造

### 新增 ES 服务

```yaml
  elasticsearch:
    image: elasticsearch:8.13.0
    container_name: multimodal-rag-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "${ES_PORT:-9200}:9200"
    volumes:
      - multimodal_rag_es_data:/usr/share/elasticsearch/data
    healthcheck:
      test: ["CMD-SHELL", "curl -s http://localhost:9200/_cluster/health | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks:
      - multimodal-rag-network
```

### backend / worker 服务新增 depends_on

```yaml
  backend:
    depends_on:
      elasticsearch:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    depends_on:
      elasticsearch:
        condition: service_healthy
      redis:
        condition: service_healthy
```

### volumes 新增

```yaml
volumes:
  multimodal_rag_es_data:
    driver: local
```

## 变更文件清单

### 新增（1 个）

- `backend/core/providers/elasticsearch_store.py` — ES 适配器

### 修改（9 个）

- `backend/core/providers/base.py` — 重写接口 + 表达式类
- `backend/core/services/infra_factory.py` — 删除 if/elif，直接创建 ES
- `backend/core/services/infra_bundle.py` — 删除 bm25 相关字段
- `backend/core/services/retrieval_pipeline.py` — 改用 search() + 表达式
- `backend/core/services/ingestion_service.py` — insert + jieba 分词
- `backend/api/documents.py` — 适配新接口
- `backend/core/config.py` — 新增 ES_* 配置，删除 CHROMA/BM25
- `docker-compose.yml` — 新增 ES 服务
- `.env.example` / `requirements.txt`

### 删除（4 个）

- `backend/core/vector_store.py` — ChromaDB 实现
- `backend/core/providers/simple_vector_store.py` — Simple 实现
- `backend/core/providers/pgvector_adapter.py` — pgvector 实现
- `backend/core/bm25_retriever.py` — ES 原生替代

## 测试策略

### 单元测试

`tests/unit/test_elasticsearch_store.py`：
- test_health / test_create_idx / test_index_exist
- test_insert / test_search_dense / test_search_hybrid
- test_search_condition / test_get / test_delete / test_update
- test_delete_idx / test_delete_all

### 集成测试（需真实 ES）

`tests/integration/test_es_integration.py`：
- test_full_ingest_and_retrieve
- test_hybrid_search_quality
- test_delete_by_source

### 现有测试适配

- 引用 bm25_retriever 的测试需要修改
- 引用旧 vector_store 的测试需要修改
- test_task_queue / test_worker 不受影响
