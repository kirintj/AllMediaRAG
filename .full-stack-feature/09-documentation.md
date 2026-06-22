# 09 - Architecture & Developer Documentation

> Comprehensive reference for the refactored multimodal RAG application.

---

## 1. Project Structure

```
多模态RAG/
├── backend/
│   ├── main.py                          # FastAPI app + lifespan + DI providers
│   ├── api/
│   │   ├── auth.py                      # POST /api/auth/register, /api/auth/login
│   │   ├── chat.py                      # POST /api/chat (SSE streaming)
│   │   ├── conversations.py             # CRUD for conversation history
│   │   └── documents.py                 # Upload, batch upload, sync, delete
│   ├── core/
│   │   ├── config.py                    # AppSettings (unified Pydantic Settings)
│   │   ├── rag_engine.py                # Thin facade over InfraBundle + 3 services
│   │   ├── services/
│   │   │   ├── __init__.py              # InfraBundle dataclass + create_infra()
│   │   │   ├── retrieval_pipeline.py    # RetrievalPipeline (vector + BM25 + rerank)
│   │   │   ├── ingestion_service.py     # IngestionService (index, delete, sync)
│   │   │   └── generation_service.py    # GenerationService (prompt + streaming)
│   │   ├── embedding_service.py         # EmbeddingService (BGE-M3, lazy load)
│   │   ├── vector_store.py              # ChromaDB vector store
│   │   ├── llm_client.py               # OpenAI-compatible LLM client
│   │   ├── document_processor.py        # Document parsing + chunking
│   │   ├── bm25_retriever.py            # BM25 keyword retriever
│   │   ├── index_manager.py             # Incremental index state tracking
│   │   ├── providers/
│   │   │   ├── base.py                  # Abstract interfaces (EmbeddingProvider, etc.)
│   │   │   ├── factory.py               # ProviderFactory (pluggable components)
│   │   │   ├── siliconflow_adapter.py   # SiliconFlow cloud embedding
│   │   │   ├── pgvector_adapter.py      # PgVectorStoreAdapter
│   │   │   └── pgvector_index_adapter.py# PgIndexManager
│   │   ├── query_understanding/
│   │   │   ├── classifier.py            # QueryClassifier (intent detection)
│   │   │   ├── router.py                # QueryRouter (strategy selection)
│   │   │   ├── hyde_generator.py        # HyDE query expansion
│   │   │   └── multi_query.py           # Multi-query rewrite
│   │   ├── reranking/
│   │   │   ├── base.py                  # RerankerProvider interface
│   │   │   ├── cohere_reranker.py       # Cohere API reranker
│   │   │   ├── bge_reranker.py          # Local BGE reranker
│   │   │   ├── siliconflow_reranker.py  # SiliconFlow cloud reranker
│   │   │   └── manager.py              # RerankManager (strategy dispatch)
│   │   ├── verification/
│   │   │   ├── citation_verifier.py     # Citation verification
│   │   │   └── self_rag_reflector.py    # Self-RAG reflection
│   │   ├── performance/cache/
│   │   │   ├── l1_cache.py              # In-memory LRU cache (L1)
│   │   │   ├── l2_cache.py              # Redis cache (L2)
│   │   │   └── manager.py              # CacheManager (L1+L2 orchestration)
│   │   ├── ocr/
│   │   │   ├── base.py                  # OCR provider interface
│   │   │   ├── paddle_provider.py       # PaddleOCR
│   │   │   ├── tesseract_provider.py    # Tesseract
│   │   │   └── vlm_provider.py          # VLM (vision-language model) OCR
│   │   ├── retrieval/
│   │   │   └── confidence_evaluator.py  # Confidence scoring + refetch decision
│   │   ├── observability/
│   │   │   └── logger.py                # Structured logging setup
│   │   ├── auth.py                      # JWT authentication
│   │   ├── db/                          # SQLAlchemy models + engine
│   │   └── chunking/                    # Chunking strategies
│   ├── tests/                           # 155 passing tests
│   ├── eval/                            # Evaluation framework (RAGAS)
│   ├── scripts/                         # Utility scripts (rebuild index, migrate, etc.)
│   ├── alembic/                         # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile                       # Node build + Nginx
│   └── src/
│       ├── App.vue                      # Root component (auth gate + layout)
│       ├── main.js                      # Vue app bootstrap
│       ├── api/
│       │   ├── index.js                 # Axios instance + interceptors
│       │   ├── auth.js                  # Auth API calls
│       │   ├── chat.js                  # Chat SSE streaming
│       │   ├── conversations.js         # Conversation CRUD
│       │   └── documents.js             # Document upload/management
│       ├── stores/
│       │   ├── useAuthStore.js          # Authentication state
│       │   ├── useChatStore.js          # Chat messages + streaming
│       │   ├── useDocumentStore.js      # Document list + upload state
│       │   ├── useConversationStore.js  # Conversation history
│       │   └── useToastStore.js         # Toast notifications
│       └── features/
│           ├── chat/
│           │   ├── ChatView.vue         # Main chat interface
│           │   ├── ChatMessage.vue      # Single message bubble
│           │   └── ChatSidebar.vue      # Conversation list sidebar
│           ├── documents/
│           │   ├── DocumentPanel.vue    # Document upload + management
│           │   └── BatchUploadProgress.vue # Batch upload progress UI
│           └── auth/
│               └── LoginView.vue        # Login/register form
├── docker-compose.yml                   # 4-service stack
├── Dockerfile                           # Backend container
├── nginx.conf                           # Frontend reverse proxy
└── .env.example                         # All environment variables documented
```

---

## 2. Backend Architecture

### 2.1 The 3-Service Decomposition

The former monolithic `RAGEngine` class has been split into three focused
services, each owning a single responsibility:

```
+-----------------+     +-------------------+     +------------------+
| RetrievalPipeline|     | IngestionService   |     | GenerationService|
|                 |     |                   |     |                  |
| - BM25 wait     |     | - ingest_document |     | - build_prompt   |
| - hybrid search |     | - delete_by_source|     | - query_stream   |
| - RRF fusion    |     | - delete_all      |     | - citation check |
| - reranking     |     | - sync_index      |     | - Self-RAG       |
| - confidence    |     | - get_index_stats |     |                  |
| - refetch       |     |                   |     |                  |
| - cache lookup  |     |                   |     |                  |
+--------+--------+     +---------+---------+     +--------+---------+
         |                        |                         |
         +------------------------+-------------------------+
                                  |
                        +---------+---------+
                        |    InfraBundle    |
                        | (shared deps)     |
                        +-------------------+
                        | - embedding_svc   |
                        | - vector_store    |
                        | - llm_client      |
                        | - bm25_retriever  |
                        | - document_proc   |
                        | - rerank_manager  |
                        | - cache_manager   |
                        | - index_manager   |
                        | - classifier      |
                        | - router          |
                        | - rewriters       |
                        | - confidence_eval |
                        | - citation_verif  |
                        | - self_rag_reflect|
                        | - executor        |
                        +-------------------+
```

### 2.2 InfraBundle

`InfraBundle` (`backend/core/services/__init__.py`) is a `@dataclass` that
holds all shared infrastructure components. It is created once at startup
by `create_infra(config)` and passed by reference to every service. This
eliminates circular dependencies and makes testing straightforward -- mock
the bundle, inject it.

```python
@dataclass
class InfraBundle:
    settings: Any               # AppSettings
    embedding_service: Any      # EmbeddingService
    vector_store: Any           # VectorStore or PgVectorStoreAdapter
    llm_client: Any             # LLMClient
    bm25_retriever: Any         # BM25Retriever
    document_processor: Any     # DocumentProcessor
    rerank_manager: Any         # RerankManager
    cache_manager: Any          # CacheManager
    index_manager: Any          # IndexManager or PgIndexManager
    classifier: Any             # QueryClassifier
    router: Any                 # QueryRouter
    rewriters: dict             # {"hyde": HyDERewriter, "multi_query": MultiQueryRewriter}
    confidence_evaluator: Any   # ConfidenceEvaluator
    citation_verifier: Any      # CitationVerifier
    self_rag_reflector: Any     # SelfRAGReflector
    executor: Any               # ThreadPoolExecutor
    bm25_ready: bool            # Background BM25 index status
```

### 2.3 RAGEngine as Thin Facade

`RAGEngine` (`backend/core/rag_engine.py`) now acts as a backward-compatible
facade. It constructs the infra bundle and delegates all methods:

```python
engine = RAGEngine(config)

# Delegates to RetrievalPipeline
engine.retrieve(query)          # -> engine.retrieval.full_retrieve(query)
engine.full_retrieve(query)     # -> engine.retrieval.full_retrieve(query)

# Delegates to IngestionService
engine.ingest_document(path)    # -> engine.ingestion.ingest_document(path)
engine.delete_by_source(src)    # -> engine.ingestion.delete_by_source(src)

# Delegates to GenerationService
engine.query_stream(q, hist)    # -> engine.generation.query_stream(q, hist)
engine.build_prompt(q, ctx)     # -> engine.generation.build_prompt(q, ctx)
```

The `RAGEngine.from_services()` class method allows constructing the facade
from pre-existing services (used by the lifespan handler to avoid double
init).

### 2.4 Dependency Injection via FastAPI Lifespan

```python
# main.py -- lifespan handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    infra = create_infra(config)
    retrieval = RetrievalPipeline(infra)
    ingestion = IngestionService(infra)
    generation = GenerationService(infra, retrieval)

    # Store on app.state
    app.state.config = config
    app.state.infra = infra
    app.state.retrieval = retrieval
    app.state.ingestion = ingestion
    app.state.generation = generation
    app.state.rag_engine = RAGEngine.from_services(...)

    yield  # app runs

    # Cleanup
    rag_engine.close()
```

Route handlers receive services via `Depends()`:

```python
def _get_retrieval(request: Request) -> RetrievalPipeline:
    return request.app.state.retrieval

@router.post("/chat")
async def chat(..., retrieval: RetrievalPipeline = Depends(_get_retrieval)):
    contexts = await retrieval.full_retrieve_async(query)
```

### 2.5 Request Flow

**Chat (RAG mode):**
```
Client  ->  POST /api/chat  ->  chat.py
  |
  +-> retrieval.full_retrieve_async(query)
  |     |
  |     +-> query understanding (classify, HyDE, multi-query) [parallel]
  |     +-> vector search + BM25 search [parallel]
  |     +-> RRF fusion
  |     +-> reranking
  |     +-> confidence evaluation + optional refetch
  |     +-> cache store
  |
  +-> generation.build_prompt(query, contexts, history)
  +-> llm_client.stream_generate(prompt)  [SSE to client]
  +-> citation_verifier.verify()  [post-stream]
  +-> save conversation
```

**Document Upload:**
```
Client  ->  POST /api/upload  ->  documents.py
  |
  +-> validate file (size, extension, MIME)
  +-> save to DATA_DIR
  +-> ingestion.ingest_document(file_path)
        |
        +-> document_processor.process_file(path)  [parse + chunk]
        +-> embedding_service.encode(texts)         [vectorize]
        +-> vector_store.add(texts, embeddings, metadatas)
        +-> bm25_retriever.add(texts, metadatas)
        +-> index_manager.mark_indexed(source)
```

---

## 3. Frontend Architecture

### 3.1 Store Decomposition

The former single Pinia store has been split into five focused stores:

| Store                   | Responsibility                              |
|-------------------------|---------------------------------------------|
| `useAuthStore`          | JWT token, login/register/logout, auth check|
| `useChatStore`          | Messages array, SSE streaming, mode toggle  |
| `useDocumentStore`      | Document list, upload progress, delete      |
| `useConversationStore`  | Conversation history, CRUD, active conv ID  |
| `useToastStore`         | Toast notification queue                    |

### 3.2 Feature Directory Layout

Components are organized by domain:

```
features/
  chat/
    ChatView.vue          # Main chat area (messages + input)
    ChatMessage.vue       # Single message bubble with markdown
    ChatSidebar.vue       # Conversation list + new chat button
  documents/
    DocumentPanel.vue     # Upload zone + document list
    BatchUploadProgress.vue  # Two-phase upload progress display
  auth/
    LoginView.vue         # Login/register form
```

### 3.3 Import Pattern

```vue
<!-- App.vue -->
<script setup>
import ChatSidebar from './features/chat/ChatSidebar.vue'
import ChatView from './features/chat/ChatView.vue'
import DocumentPanel from './features/documents/DocumentPanel.vue'
import LoginView from './features/auth/LoginView.vue'
</script>
```

---

## 4. API Documentation

All endpoints are prefixed with `/api`. Authentication is via JWT Bearer
token in the `Authorization` header.

### 4.1 Authentication

| Method | Path                  | Auth | Description                |
|--------|-----------------------|------|----------------------------|
| POST   | `/api/auth/register`  | No   | Register + auto-login      |
| POST   | `/api/auth/login`     | No   | Login, returns JWT         |
| GET    | `/api/auth/me`        | Yes  | Get current user info      |

**Register / Login Request:**
```json
{"username": "string (2-32 chars)", "password": "string (6-128 chars)"}
```

**Response:**
```json
{"access_token": "eyJ...", "token_type": "bearer"}
```

### 4.2 Chat

| Method | Path       | Auth | Description                        |
|--------|------------|------|------------------------------------|
| POST   | `/api/chat`| Yes  | SSE streaming chat (RAG or direct) |

**Request:**
```json
{
  "message": "string (1-5000 chars)",
  "mode": "rag | direct",
  "conversation_id": "optional string",
  "history": [{"role": "user|assistant", "content": "..."}]  // max 20
}
```

**SSE Events:**
```
data: {"chunk": "partial text", "full_answer": "accumulated", "sources": [...]}
data: {"done": true, "full_answer": "...", "sources": [...], "verification": {...}, "conversation_id": "..."}
```

### 4.3 Documents

| Method | Path                          | Auth | Description                    |
|--------|-------------------------------|------|--------------------------------|
| POST   | `/api/upload`                 | Yes  | Upload single document         |
| POST   | `/api/upload/batch`           | Yes  | Batch upload (sync or async)   |
| GET    | `/api/upload/batch/status/{id}`| Yes | Poll batch upload progress     |
| GET    | `/api/documents`              | Yes  | List indexed documents         |
| DELETE | `/api/documents/{source}`     | Yes  | Delete document by filename    |
| DELETE | `/api/documents`              | Yes  | Clear all documents            |
| POST   | `/api/documents/load`         | Yes  | Load all local documents       |
| GET    | `/api/documents/load/status`  | Yes  | Poll load progress             |
| POST   | `/api/documents/sync`         | Yes  | Incremental index sync         |

**Upload response:**
```json
{"message": "upload success", "filename": "doc.pdf", "chunks": 42}
```

**Batch upload:** Files < 20 are processed synchronously and results
returned directly. Files >= 20 trigger async processing with a `task_id`
for polling.

### 4.4 Conversations

| Method | Path                          | Auth | Description                      |
|--------|-------------------------------|------|----------------------------------|
| GET    | `/api/conversations`          | Yes  | List user conversations          |
| GET    | `/api/conversations/{conv_id}`| Yes  | Get conversation detail          |
| DELETE | `/api/conversations`          | Yes  | Clear all user conversations     |
| DELETE | `/api/conversations/{conv_id}`| Yes  | Delete a specific conversation   |

### 4.5 System

| Method | Path       | Auth | Description                 |
|--------|------------|------|-----------------------------|
| GET    | `/health`  | No   | Health check                |
| GET    | `/`        | No   | API welcome message         |
| GET    | `/api/stats`| Yes | Document/vector/BM25 stats |

### 4.6 DI Pattern in Route Handlers

Each route file defines local dependency providers that read from
`request.app.state`:

```python
# api/chat.py
def _get_retrieval(request: Request) -> RetrievalPipeline:
    return request.app.state.retrieval

@router.post("/chat")
async def chat(
    ...,
    retrieval: RetrievalPipeline = Depends(_get_retrieval),
):
    ...
```

This avoids importing `main.py` (which would cause circular imports) while
still giving handlers typed access to the exact service they need.

---

## 5. Configuration Guide

### 5.1 The Unified AppSettings Class

All configuration is in `backend/core/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",          # unknown env vars are silently ignored
    )

    MIMO_API_KEY: str = ""
    MIMO_API_BASE: str = "https://api.siliconflow.cn/v1"
    # ... 70+ fields with typed defaults
```

### 5.2 How Settings Are Loaded

1. Pydantic Settings reads `.env` file automatically (no manual
   `load_dotenv()` call needed).
2. Environment variables override `.env` file values.
3. If neither is set, the field's default value is used.
4. `extra="ignore"` means unexpected env vars won't cause errors.

### 5.3 Changing Settings

**For development** -- edit `.env`:
```bash
# .env
TOP_K=10
RERANK_STRATEGY=siliconflow
```

**For production** -- set environment variables:
```bash
export TOP_K=10
export RERANK_STRATEGY=siliconflow
```

**For Docker** -- the `docker-compose.yml` passes `.env` via `env_file: .env`.
You can also override individual vars in the `environment:` section:
```yaml
backend:
  environment:
    TOP_K: "10"
```

### 5.4 Backward Compatibility

```python
# Old code that still works:
from core.config import config           # AppSettings instance
from core.config import advanced_config   # Same instance (alias)
from core.config import init_advanced_config  # No-op, safe to call

config.TOP_K  # 5
advanced_config.TOP_K  # 5 (same object)
```

### 5.5 Adding a New Setting

```python
# backend/core/config.py
class AppSettings(BaseSettings):
    # ... existing fields ...

    MY_NEW_FEATURE_ENABLED: bool = False
    MY_NEW_FEATURE_THRESHOLD: float = 0.8
```

Then access it via `infra.settings.MY_NEW_FEATURE_ENABLED` in any service.

---

## 6. Developer Guide: Adding a New Feature

### 6.1 Adding a New API Endpoint

1. **Choose the right API module** -- add to `backend/api/chat.py`,
   `documents.py`, `conversations.py`, or create a new file.

2. **Define dependencies** -- read from `app.state`:
   ```python
   def _get_ingestion(request: Request) -> IngestionService:
       return request.app.state.ingestion

   @router.post("/api/my-endpoint")
   async def my_endpoint(
       ingestion: IngestionService = Depends(_get_ingestion),
   ):
       ...
   ```

3. **Register the router** in `main.py` (if new file):
   ```python
   from api.my_module import router as my_router
   app.include_router(my_router, prefix="/api")
   ```

### 6.2 Adding a New Service

1. Create `backend/core/services/my_service.py`:
   ```python
   class MyService:
       def __init__(self, infra: InfraBundle):
           self._infra = infra
           # Access any infra component
   ```

2. Instantiate in `main.py` lifespan:
   ```python
   my_service = MyService(infra)
   app.state.my_service = my_service
   ```

3. Add a DI provider:
   ```python
   def get_my_service(request: Request) -> MyService:
       return request.app.state.my_service
   ```

### 6.3 Adding a New Frontend Store

1. Create `frontend/src/stores/useMyStore.js`:
   ```javascript
   import { defineStore } from 'pinia'
   import { ref } from 'vue'

   export const useMyStore = defineStore('my', () => {
     const data = ref(null)
     // ... actions ...
     return { data }
   })
   ```

2. Import in the component that needs it.

### 6.4 Adding a New Frontend Feature

1. Create directory: `frontend/src/features/my-feature/`
2. Add components inside.
3. Import from `App.vue` or parent component:
   ```vue
   import MyComponent from './features/my-feature/MyComponent.vue'
   ```

---

## 7. Architecture Decision Records (ADRs)

### ADR-001: Split RAGEngine into 3 Services

**Status**: Accepted

**Context**: The `RAGEngine` class grew to ~1500 lines, mixing retrieval logic
(hybrid search, RRF fusion, reranking, caching), document ingestion (parsing,
chunking, embedding, indexing), and generation (prompt construction, streaming,
citation verification). This made the class hard to test, hard to reason about,
and a merge-conflict hotspot.

**Decision**: Extract three focused services:
- `RetrievalPipeline` -- pure retrieval, no LLM generation, no document I/O
- `IngestionService` -- document processing and vector/BM25 indexing
- `GenerationService` -- prompt building and LLM streaming

Share infrastructure via an `InfraBundle` dataclass. Keep `RAGEngine` as a
thin facade for backward compatibility.

**Consequences**:
- Each service can be tested independently by mocking InfraBundle.
- RetrievalPipeline has no dependency on GenerationService (and vice versa),
  except that GenerationService holds a reference to RetrievalPipeline for
  the full query flow.
- Existing code calling `engine.retrieve()` or `engine.ingest_document()`
  continues to work unchanged.
- New code should inject the specific service via `Depends()` rather than
  using the facade.

### ADR-002: Unified Pydantic Settings

**Status**: Accepted

**Context**: Configuration was split across two files:
- `config.py` -- core settings (LLM, embedding, Chroma, RAG params)
- `advanced_config.py` -- advanced settings (reranking, caching, evaluation,
  observability, alerts)

This caused confusion about where to add new settings, required a manual
`init_advanced_config()` call to load dotenv, and lacked type validation.

**Decision**: Merge both into a single `AppSettings(BaseSettings)` class using
`pydantic-settings`. All 70+ settings are typed fields with defaults. The
`.env` file is loaded automatically by Pydantic. `advanced_config` is aliased
to `config` for backward compatibility.

**Consequences**:
- One place to find and add settings.
- Type validation at startup (e.g., `TOP_K` must be an int).
- IDE autocomplete for all settings.
- `init_advanced_config()` becomes a no-op but safe to call.
- New dependency: `pydantic-settings>=2.0.0`.

### ADR-003: FastAPI Lifespan + Depends DI

**Status**: Accepted

**Context**: The previous pattern created module-level singletons:
```python
# api/chat.py (old)
from core.rag_engine import RAGEngine
engine = RAGEngine(config)  # created at import time
```

This caused circular imports, made testing difficult (can't mock the engine
without patching module globals), and prevented clean startup/shutdown.

**Decision**: Use FastAPI's `lifespan` context manager to create all
infrastructure at startup, store on `app.state`, and inject via `Depends()`.

**Consequences**:
- Clean startup/shutdown lifecycle with resource cleanup.
- No circular imports -- route modules only import types, not instances.
- Testing is straightforward: set `app.state.retrieval = mock_retrieval`.
- All services share one `InfraBundle` (single set of models loaded).

### ADR-004: Frontend Store Decomposition

**Status**: Accepted

**Context**: A single Pinia store managed auth, chat messages, documents,
conversations, and notifications. This made it hard to trace which component
triggered which state change and caused unnecessary re-renders when unrelated
state changed.

**Decision**: Split into 5 stores (`useAuthStore`, `useChatStore`,
`useDocumentStore`, `useConversationStore`, `useToastStore`), each with a
single responsibility.

**Consequences**:
- Components subscribe only to the state they need.
- Each store is independently testable.
- Cross-store communication (e.g., chat store saving to conversation store)
  uses direct store imports.

### ADR-005: Feature Directory Layout for Components

**Status**: Accepted

**Context**: All Vue components lived in a flat `components/` directory.
As the app grew, it was hard to find related files (e.g., ChatView,
ChatMessage, ChatSidebar were scattered).

**Decision**: Move components into `features/{domain}/` directories:
`features/chat/`, `features/documents/`, `features/auth/`.

**Consequences**:
- Related files are co-located.
- New developers can navigate by feature, not by file type.
- Shared/generic components can stay in a top-level `components/` if needed
  (none exist currently).

### ADR-006: Keep RAGEngine Facade

**Status**: Accepted

**Context**: After splitting into 3 services, the question was whether to
remove `RAGEngine` entirely.

**Decision**: Keep `RAGEngine` as a thin facade that delegates to the 3
services. It exposes backward-compatible attributes (e.g.,
`engine.embedding_service`) and methods (e.g., `engine.retrieve()`).

**Consequences**:
- Existing tests that use `RAGEngine` continue to pass without modification.
- New code should prefer injecting individual services.
- The facade adds negligible overhead (all methods are one-line delegates).
- `_setup_backward_compat()` populates ~20 aliases from the infra bundle.

---

## 8. Migration Guide

For developers familiar with the old codebase, here is a reference mapping
old locations and patterns to their new equivalents.

### 8.1 Backend Migration

| Old Location / Pattern | New Location / Pattern |
|------------------------|------------------------|
| `core/config.py` (core settings) | `core/config.py` `AppSettings` class |
| `core/advanced_config.py` | Deleted; all fields merged into `AppSettings` |
| `core/advanced_config.init_advanced_config()` | No-op alias in `core/config.py` (safe to remove call) |
| `core/advanced_config.advanced_config` | `config` (same `AppSettings` instance) |
| `RAGEngine.retrieve()` | `RetrievalPipeline.full_retrieve()` |
| `RAGEngine.ingest_document()` | `IngestionService.ingest_document()` |
| `RAGEngine.delete_by_source()` | `IngestionService.delete_by_source()` |
| `RAGEngine.delete_all()` | `IngestionService.delete_all()` |
| `RAGEngine.sync_index()` | `IngestionService.sync_index()` |
| `RAGEngine.query_stream()` | `GenerationService.query_stream()` |
| `RAGEngine.build_prompt()` | `GenerationService.build_prompt()` |
| `RAGEngine._hybrid_search()` | `RetrievalPipeline._hybrid_search()` |
| `RAGEngine._rrf_fusion()` | `RetrievalPipeline._rrf_fusion()` |
| `RAGEngine._rerank()` | `RetrievalPipeline._rerank()` |
| `api/chat.py` module-level `engine` | `Depends(_get_retrieval)` / `Depends(_get_generation)` |
| `api/documents.py` module-level `engine` | `Depends(_get_ingestion)` |
| `core/providers/adapters.py` | Deleted; adapters merged into `providers/` modules |

### 8.2 Frontend Migration

| Old Location | New Location |
|-------------|-------------|
| `stores/chat.js` (all state) | `stores/useChatStore.js` (chat messages + streaming) |
| `stores/chat.js` (auth state) | `stores/useAuthStore.js` |
| `stores/chat.js` (documents) | `stores/useDocumentStore.js` |
| `stores/chat.js` (conversations) | `stores/useConversationStore.js` |
| `stores/chat.js` (toasts) | `stores/useToastStore.js` |
| `components/ChatView.vue` | `features/chat/ChatView.vue` |
| `components/ChatMessage.vue` | `features/chat/ChatMessage.vue` |
| `components/ChatSidebar.vue` | `features/chat/ChatSidebar.vue` |
| `components/DocumentPanel.vue` | `features/documents/DocumentPanel.vue` |
| `components/BatchUploadProgress.vue` | `features/documents/BatchUploadProgress.vue` |
| `components/LoginView.vue` | `features/auth/LoginView.vue` |
| `api/index.js` (all API calls) | `api/auth.js`, `api/chat.js`, `api/documents.js`, `api/conversations.js` |
| `App.vue` local `ref` for `isLoggedIn` | `useAuthStore().isLoggedIn` |

### 8.3 Quick Search Cheat Sheet

```bash
# Find where a retrieval method lives now:
grep -r "def full_retrieve" backend/core/services/

# Find which store owns a piece of state:
grep -r "messages\b" frontend/src/stores/

# Find all DI dependency providers:
grep -r "def _get_" backend/api/

# Find all app.state assignments (what's available for DI):
grep -r "app.state\." backend/main.py
```

---

## 9. Known Limitations and Future Work

| Item | Status | Notes |
|------|--------|-------|
| TypeScript migration | Not started | Frontend is still plain JavaScript. Migrating to TypeScript would catch store/API shape mismatches at compile time. |
| Frontend unit tests | Not implemented | No Vitest/Jest tests exist for stores or components. The store decomposition makes them testable in isolation -- this is the next step. |
| Conversation migration to PostgreSQL | Partial | `core/pg_conversations.py` exists but conversations still default to ChromaDB-based storage. The PostgreSQL path needs integration testing and a data migration script. |
| `RAGEngine` facade removal | Deferred | The facade is kept for backward compatibility. Once all tests and external callers are migrated to direct service injection, it can be removed. |
| `advanced_config` alias cleanup | Low priority | `from core.config import advanced_config` still works (alias). Search codebase for usages and remove before the next major release. |
| `InfraBundle` field types | All `Any` | Fields are typed as `Any` to avoid circular imports. A future pass could use `TYPE_CHECKING` + string annotations for better IDE support. |
| CI pipeline | Not configured | No GitHub Actions / GitLab CI configuration exists. Docker Compose is available for local dev; CI needs to be added. |
| End-to-end tests | Not implemented | Only unit tests exist (155 passing). Playwright or Cypress E2E tests would cover the full stack. |
