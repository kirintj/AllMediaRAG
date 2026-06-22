# Architecture Design: 项目结构重构

## 1. 后端架构

### 1.1 目标目录结构

```
backend/
  main.py                          # Lifespan 启动 + DI 注入
  core/
    config.py                      # 单一 Pydantic Settings（合并两个配置文件）
    services/                      # ── 新增服务层 ──
      __init__.py                  # InfraBundle dataclass + create_infra()
      retrieval_pipeline.py        # 检索管线（从 RAGEngine 提取）
      ingestion_service.py         # 文档摄入（从 RAGEngine 提取）
      generation_service.py        # LLM 生成（从 RAGEngine 提取）
    embedding_service.py           # 保留，修复 O(n²) Bug
    vector_store.py                # 保留，直接实现 VectorStoreProvider ABC
    llm_client.py                  # 保留，直接实现 LLMProvider ABC
    document_processor.py          # 保留
    bm25_retriever.py              # 保留
    providers/
      base.py                      # 保留 ABC 定义
      factory.py                   # 保留工厂模式
      siliconflow_adapter.py       # 保留（真正的云端适配器）
      pgvector_adapter.py          # 保留（真正的 pgvector 适配器）
      # adapters.py → 删除（无用包装层）
    query_understanding/           # 保留不变
    reranking/                     # 保留不变
    performance/cache/             # 保留，修复 Bug
    observability/                 # 保留不变
  api/
    chat.py                        # 改用 Depends(get_retrieval, get_generation)
    documents.py                   # 改用 Depends(get_ingestion)
    conversations.py               # 注入 config
    auth.py                        # 保留不变
```

### 1.2 依赖注入：FastAPI Lifespan + Depends

**消除**：模块级 `_engine` 全局变量 + `set_engine()` setter

**替换为**：
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = AppSettings()
    infra = create_infra(settings)
    app.state.retrieval = RetrievalPipeline(infra)
    app.state.ingestion = IngestionService(infra)
    app.state.generation = GenerationService(infra)
    yield
    # shutdown cleanup

def get_retrieval(request: Request) -> RetrievalPipeline:
    return request.app.state.retrieval
```

### 1.3 三大服务接口

| 服务 | 职责 | 依赖 |
|------|------|------|
| **RetrievalPipeline** | 查询理解 → 混合检索 → RRF → 重排序 → 置信度评估 | Embedding, VectorStore, BM25, RerankManager, Cache, Classifier, Router |
| **IngestionService** | 文件解析 → 分块 → 向量化 → 存储 | DocumentProcessor, Embedding, VectorStore, BM25, IndexManager |
| **GenerationService** | Prompt 构建 → LLM 流式生成 → 引用核查 → Self-RAG | LLMClient, CitationVerifier, SelfRAGReflector |

### 1.4 统一配置

合并为单一 `AppSettings(BaseSettings)`，删除 `advanced_config.py`：
- 大写字段名 + Pydantic 自动类型校验
- `config = AppSettings()` 模块级单例保持向后兼容

### 1.5 Bug 修复

| Bug | 位置 | 修复方案 |
|-----|------|----------|
| CacheManager.get_stats() | manager.py:147 | `_cache` → `cache`，添加 `size()` 方法 |
| EmbeddingService O(n²) | embedding_service.py:109 | 改用 `zip(to_encode_idx, embeddings)` 直接迭代 |
| HybridReranker 索引错配 | manager.py:148-163 | 用 `(source, text_hash)` 作为合并 key 替代位置索引 |

### 1.6 删除 Adapter 层

让核心类直接实现 ABC：
- `VectorStore(VectorStoreProvider)` — 加继承声明即可
- `EmbeddingService(EmbeddingProvider)` — 同上
- `LLMClient(LLMProvider)` — 同上
- 删除 `providers/adapters.py`

---

## 2. 前端架构

### 2.1 目标目录结构

```
frontend/src/
  api/
    index.js                  # 仅 Axios 实例 + 拦截器
    auth.js                   # login, register, getMe
    chat.js                   # chatStream
    documents.js              # upload, batch, list, delete, sync, stats
    conversations.js          # list, get, delete, clearAll
  stores/
    useAuthStore.js           # 认证状态（从 App.vue 迁出）
    useChatStore.js           # 精简：仅消息 + 模式 + 发送
    useDocumentStore.js       # 文档列表 + 上传 + 删除
    useConversationStore.js   # 会话列表 + 加载 + 删除
    useToastStore.js          # 统一 Toast 通知
  features/
    auth/LoginView.vue
    chat/ChatView.vue, ChatMessage.vue, ChatSidebar.vue
    documents/DocumentPanel.vue, BatchUploadProgress.vue
```

### 2.2 Store 拆分

| Store | 状态 | 方法 |
|-------|------|------|
| useAuthStore | token, username, isAuthenticated | login, register, logout, checkAuth |
| useChatStore | messages, mode, loading, activeConversationId | sendMessage, clearChatHistory |
| useDocumentStore | documents, stats | fetchDocuments, uploadFile, removeDocument, syncDocuments |
| useConversationStore | conversations | fetchConversations, loadConversation, removeConversation |
| useToastStore | toasts | show, success, error, warning |

### 2.3 认证状态迁移

从 `App.vue` 本地 ref → `useAuthStore`：
- `isAuthenticated`、`onLoginSuccess`、`handleLogout`、`onAuthExpired` 全部迁入 store
- `auth-expired` 事件由 Axios 拦截器直接调用 `useAuthStore().logout()`

### 2.4 统一错误处理

```
后端异常 → FastAPI 异常处理器 → JSON {detail, code}
                              → SSE: data: {"error": "...", "done": true}
前端: Axios 拦截器 → useToastStore.error()
     SSE 错误 → chat 内联显示
```

---

## 3. 迁移路径（每步保证测试通过）

| 步骤 | 内容 | 风险 |
|------|------|------|
| 1 | 合并配置 + 修复 3 个 Bug | 低 |
| 2 | 核心类直接实现 ABC，删除 adapter | 低 |
| 3 | 提取 RetrievalPipeline | 中 |
| 4 | 提取 IngestionService | 低 |
| 5 | 提取 GenerationService | 低 |
| 6 | Lifespan + Depends DI 改造 | 中 |
| 7 | 清理：删除 RAGEngine 残留代码 | 低 |

**策略**：每步在 RAGEngine 内保留委托层，新旧共存直到迁移完成。
