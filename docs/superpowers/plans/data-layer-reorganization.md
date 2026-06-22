# Data Layer Reorganization Design

## Current State Summary

The RAG project's data layer is spread across several modules with no unified access pattern:

- **Conversations**: Dual implementations -- `backend/api/conversations.py` (JSON files, no locking, no pagination) and `backend/core/pg_conversations.py` (PostgreSQL ORM). Both coexist but the JSON version is the one wired into the API router.
- **Vector storage**: `backend/core/vector_store.py` (ChromaDB, hardcoded collection name "python_docs") and `backend/core/providers/pgvector_adapter.py` (PostgreSQL+pgvector). Both implement `VectorStoreProvider` from `backend/core/providers/base.py`.
- **BM25 index**: `backend/core/bm25_retriever.py` -- full rebuild on every `add_documents()` call, pickle serialization on every save.
- **Cache**: Two-level (L1 memory + L2 Redis) in `backend/core/performance/cache/`. `CacheManager.get_stats()` has a confirmed attribute name bug. `L2Cache.clear()` and `invalidate_by_pattern()` use the `KEYS` command (O(N)).
- **Configuration**: Two independent config classes (`Config` in `backend/core/config.py` and `AdvancedRAGConfig` in `backend/core/advanced_config.py`) with overlapping keys and conflicting defaults (e.g., `RERANK_TOP_K`: 40 vs 20).

---

## 1. Data Access Layer Reorganization

### Problem

The new modular architecture (RetrievalPipeline, IngestionService, GenerationService) needs clean data access boundaries, but today the `RAGEngine` class directly instantiates and orchestrates every data component -- VectorStore, BM25Retriever, CacheManager, IndexManager, ConversationStore. There is no repository/DAO abstraction, so each service would need to know the internals of every data source.

### Design: Repository Interfaces

Define lightweight repository interfaces that each service depends on, rather than depending on concrete implementations.

**Proposed interfaces** (to live in `backend/core/repositories/`):

```
DocumentRepository
    add_chunks(texts, embeddings, metadatas) -> None
    delete_by_source(source) -> None
    get_all_sources() -> list[str]
    get_document_count() -> int
    get_all_documents() -> list[dict]
    delete_all() -> None

SearchRepository
    vector_search(embedding, top_k) -> dict
    bm25_search(query, top_k) -> list[dict]
    hybrid_search(queries, vector_weight, bm25_weight, top_k) -> list[dict]

ConversationRepository
    list_conversations(username, offset, limit) -> (list[dict], total_count)
    get_conversation(conv_id, username) -> dict | None
    save_conversation(conv_id, username, title, messages, mode) -> dict
    delete_conversation(conv_id, username) -> bool
    clear_all(username) -> int

CacheRepository
    get(key) -> Any | None
    set(key, value) -> None
    delete(key) -> bool
    invalidate_by_source(source) -> None
    get_stats() -> dict
```

### How This Maps to Services

- **RetrievalPipeline** depends on `SearchRepository` (for query execution) and `CacheRepository` (for result caching). It does not need to know whether the vector store is Chroma or pgvector.
- **IngestionService** depends on `DocumentRepository` (for writing chunks) and `SearchRepository` (for updating BM25). It also uses `IndexManager` internally for change detection.
- **GenerationService** depends on `CacheRepository` and whatever LLM client is configured. It receives retrieved documents from RetrievalPipeline, not from the data layer directly.
- **ConversationService** (new thin wrapper) depends on `ConversationRepository`.

### Migration Strategy

1. Create the repository interfaces as abstract base classes.
2. Wrap existing implementations (VectorStore, PgVectorStoreAdapter, BM25Retriever, CacheManager, conversations.py) behind these interfaces. No logic changes -- just delegation.
3. Update RAGEngine to accept repositories via constructor injection instead of creating them internally.
4. Once the new services (RetrievalPipeline, IngestionService, GenerationService) are built, they consume repositories directly. RAGEngine becomes a thin composition root.

This is a pure structural refactor -- no behavioral changes, no test breakage.

---

## 2. Conversation Storage Improvement

### Problem

`backend/api/conversations.py` stores conversations as JSON files with:
- No file locking (concurrent writes corrupt data)
- No pagination (reads every file in the user directory on every list call)
- No indexing (sorting requires loading all files)
- Global mutable state (`_conversations_dir`)

There is already a PostgreSQL-based implementation in `backend/core/pg_conversations.py` with proper ORM models (`ConversationModel`, `MessageModel` in `backend/core/db/user_models.py`), but it is not wired into the API router.

### Design: Two-Track Approach

**Track A (short-term, keep JSON files)**: Improve the existing JSON storage with minimal disruption.

1. **Add file locking** using `fcntl.flock` (Linux) or `msvcrt.locking` (Windows) behind a cross-platform wrapper. Every read-modify-write cycle in `save_conversation()` must acquire an exclusive lock. This is a ~20 line utility.

2. **Add pagination** to `_list_user()`:
   - Write a lightweight sidecar index file (`_index.json`) per user directory. On each save, update the index entry with `{id, title, updated_at, message_count}`.
   - `_list_user()` reads only the sidecar index (one file), not every conversation JSON.
   - Accept `offset` and `limit` parameters; return `(items, total_count)`.

3. **Extract a `JsonConversationRepository` class** that implements `ConversationRepository`. This replaces the module-level functions with a proper class that holds the base directory as instance state (no globals).

**Track B (medium-term, switch to PostgreSQL)**: The ORM models already exist. Wire `pg_conversations.py` into the API router as an alternative backend selected by config.

- Add a `CONVERSATION_BACKEND` config key: `"json"` (default) or `"postgres"`.
- `pg_conversations.py` already supports pagination natively via SQLAlchemy `.offset().limit()`.
- When PostgreSQL is selected, the JSON locking concerns disappear entirely.

### API Backward Compatibility

The API endpoints (`GET /conversations`, `GET /conversations/{conv_id}`, `DELETE /conversations`, `DELETE /conversations/{conv_id}`) remain unchanged. The only addition is optional `offset` and `limit` query parameters on the list endpoint, which default to current behavior (return all).

---

## 3. Cache Layer Bug Fixes and Improvements

### 3a. Fix `get_stats()` Attribute Name Bug

**Location**: `backend/core/performance/cache/manager.py`, line 147.

**Current code**:
```python
"l1_size": len(self.l1_cache._cache) if hasattr(self.l1_cache, '_cache') else 0,
```

**Problem**: `L1Cache` (in `l1_cache.py`) stores its data in `self.cache` (no underscore prefix), not `self._cache`. The `hasattr` check returns `False`, so `l1_size` always reports `0`.

**Fix**: Change `_cache` to `cache`:
```python
"l1_size": len(self.l1_cache.cache),
```

The `hasattr` guard is unnecessary since `L1Cache` always defines `self.cache` in `__init__`. Remove it.

### 3b. Migrate L2Cache from `KEYS` to `SCAN`

**Location**: `backend/core/performance/cache/l2_cache.py`, lines 126 and 146.

**Current code** in `clear()`:
```python
keys = self.client.keys(f"{self.prefix}*")
if keys:
    self.client.delete(*keys)
```

Same pattern in `invalidate_by_pattern()`.

**Problem**: Redis `KEYS` is O(N) over the entire keyspace and blocks the Redis server during execution. In production with many keys, this causes latency spikes for all connected clients.

**Fix**: Replace with `SCAN` cursor iteration:

- `clear()`: Use `SCAN` with `match=f"{self.prefix}*"` and `count=100`. Accumulate keys in batches and `DELETE` each batch. This yields the event loop between iterations and does not block Redis.
- `invalidate_by_pattern()`: Same SCAN-based approach. This is the method called by `invalidate_by_source()` which is called on every document upload/delete.

The SCAN approach has the same end result but spreads the work across multiple round-trips, each touching only a small cursor window.

### 3c. Consistent Invalidation

**Problem**: `CacheManager.invalidate_by_source()` only invalidates L2. It does not invalidate L1 entries that match the source. After a document is re-ingested, stale results can persist in L1 until TTL expiry.

**Fix**: Add L1 pattern-matching invalidation. Since L1 is an in-memory OrderedDict, iterate over keys and delete matches. This is acceptable because L1 is bounded at `max_size` (default 1000).

```python
def invalidate_by_source(self, source: str) -> None:
    # L1: scan and remove matching keys
    keys_to_remove = [k for k in self.l1_cache.cache if source in k]
    for key in keys_to_remove:
        self.l1_cache.delete(key)

    # L2: pattern-based scan
    if self.l2_cache:
        deleted = self.l2_cache.invalidate_by_source(source)
```

---

## 4. BM25 Index Optimization

### Problem

`BM25Retriever.add_documents()` calls `self._rebuild()` which reconstructs the entire BM25Okapi index from scratch every time. The rebuild iterates all documents, re-tokenizes all text, and rebuilds the internal scoring matrix. Then `save()` re-tokenizes everything again for the pickle file. For a corpus of 10,000 chunks, each new document triggers O(N) work.

### Why Full Rebuild Is Inherent

The `rank_bm25.BM25Okapi` library precomputes IDF values and document-length statistics across the entire corpus at construction time. Adding a single document changes the IDF of every term. True incremental BM25 would require a custom implementation that maintains per-document statistics and lazily recomputes IDF. This is not worth building for this project's scale.

### Optimization Strategy: Batch and Defer

Since full rebuilds are unavoidable, minimize how often they happen:

1. **Buffer new documents in memory**. Instead of rebuilding on every `add_documents()` call, accumulate new documents in a `_pending` list. Mark the retriever as "dirty."

2. **Rebuild on a threshold or timer**. Trigger the actual `_rebuild()` when:
   - `_pending` exceeds a configurable batch size (e.g., 50 documents), OR
   - A search is requested while the retriever is dirty (lazy rebuild), OR
   - A configurable idle timeout elapses (e.g., 30 seconds after last add).

3. **Separate tokenization from index construction**. Currently `save()` re-tokenizes everything. Instead, cache the tokenized corpus alongside the BM25 model. The `_rebuild()` method already stores `tokenized_corpus` in the pickle -- reuse it on load rather than re-tokenizing.

4. **Async save**. After rebuild, pickle the index to disk in a background thread so the caller does not block on I/O. The current `save()` is synchronous and called inside `_rebuild()` which is called inside `add_documents()`.

### Concrete Changes

In `BM25Retriever`:
- Add `self._pending: list[dict] = []` and `self._dirty: bool = False`.
- Modify `add_documents()`: append to `_pending`, set `_dirty = True`, return immediately.
- Add `_maybe_rebuild()`: checks `_pending` size against threshold; if exceeded, calls `_rebuild()` with merged `doc_map + _pending`, clears `_pending`.
- Modify `search()`: call `_maybe_rebuild()` before scoring if `_dirty`.
- Modify `save()`: include tokenized corpus in the pickle (already done), and run in a background thread.
- Modify `load()`: reuse the stored `tokenized_corpus` directly (already done -- this part is correct).

For `delete_by_source()`: this is infrequent enough that immediate rebuild is acceptable.

---

## 5. Config Unification Design

### Problem

Two independent config classes with overlapping responsibilities:

| Setting | `config.py` default | `advanced_config.py` default |
|---|---|---|
| `RERANK_TOP_K` | 40 | 20 |
| `USE_HYDE` | True | True |
| `MULTI_QUERY_ENABLED` | True | True |
| `MULTI_QUERY_COUNT` | 3 | 3 |
| `RERANK_STRATEGY` | "cohere" | "cohere" |
| `COHERE_API_KEY` | "" | "" |
| `BGE_RERANKER_PATH` | "BAAI/bge-reranker-base" | "BAAI/bge-reranker-base" |
| `USE_CACHE` | True | True |
| `CACHE_L1_MAX_SIZE` | 1000 | 1000 |
| `CACHE_L1_TTL` | 300 | 300 |
| `USE_REDIS` | False | False |
| `REDIS_HOST` | "localhost" | "localhost" |
| `REDIS_PORT` | 6379 | 6379 |

`RERANK_TOP_K` has conflicting defaults (40 vs 20). Other keys are duplicated. There is no clear ownership -- consumers import from whichever file they feel like.

Additionally, `config.py` uses raw `os.getenv()` with manual type conversion, while `advanced_config.py` uses helper functions (`_int_env`, `_bool_env`, `_float_env`). Neither uses Pydantic Settings, so there is no validation, no `.env` file documentation, and no environment-variable-to-field binding.

### Design: Single Pydantic Settings Class

Replace both files with a single `backend/core/config.py` using `pydantic-settings`:

```
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Group 1: LLM
    mimo_api_key: str = Field(default="", alias="MIMO_API_KEY")
    mimo_api_base: str = Field(default="https://api.siliconflow.cn/v1", alias="MIMO_API_BASE")
    mimo_model: str = Field(default="mimo-v2.5", alias="MIMO_MODEL")

    # Group 2: Embedding
    embedding_model_path: str = Field(default="./models/bge-m3", alias="EMBEDDING_MODEL_PATH")
    embedding_provider: str = Field(default="sentence-transformer", alias="EMBEDDING_PROVIDER")

    # Group 3: Vector Store
    chroma_persist_dir: str = Field(default="./chroma_db", alias="CHROMA_PERSIST_DIR")
    vector_store_provider: str = Field(default="chroma", alias="VECTOR_STORE_PROVIDER")

    # ... (all other settings, one canonical definition per key)
```

### Migration Strategy

1. **Create the new `Settings` class** in `backend/core/config.py`. Import both old files, identify every unique key, pick the correct default (for `RERANK_TOP_K`, use 20 since it is the safer, more conservative default, or document the chosen value clearly).

2. **Expose a backward-compatible shim**. The old code accesses `config.RERANK_TOP_K` (uppercase class attribute). Pydantic Settings uses lowercase field names by default. Two options:
   - Option A: Use uppercase field names in the Pydantic model (supported by Pydantic v2 with `alias`).
   - Option B: Keep lowercase fields but add `__getattr__` to the singleton that uppercases the lookup.

   **Recommendation**: Option A -- use uppercase field names with `alias` pointing to the env var names. This means existing code `config.RERANK_TOP_K` continues to work unchanged.

3. **Create a singleton**: `settings = Settings()` at module level. Replace `from core.config import config` with `from core.config import settings` (or alias `config = settings` during transition).

4. **Delete `advanced_config.py`**. All its settings are absorbed into the unified `Settings` class. Update all imports from `from core.advanced_config import advanced_config` to use the unified config.

5. **Validation**: Pydantic Settings validates types at import time. A `RERANK_TOP_K=abc` env var will raise a clear error instead of silently falling back to a default. This is a strict improvement.

### Handling `database_url` as a Computed Property

The current `Config.database_url` is a `@property` that constructs the URL from `PG_*` fields when `DATABASE_URL` is empty. Pydantic Settings supports `@computed_field` (Pydantic v2) or `@property` with `model_config = ConfigDict(ignored_types=(property,))`. Use `@computed_field` for clean serialization.

---

## 6. Collection/Namespace Management

### Problem

`VectorStore.__init__()` hardcodes `name="python_docs"` on line 17 of `backend/core/vector_store.py`. This means:
- All documents go into a single ChromaDB collection regardless of project or tenant.
- `delete_all()` on line 93 also hardcodes `"python_docs"` when recreating the collection.
- `PgVectorStoreAdapter` does not have this problem (it uses `document_chunks` table, which is a single namespace by design), but the Chroma path does.

### Design: Configurable Collection Name

1. **Add `COLLECTION_NAME` to the unified config** with a default of `"documents"` (neutral name replacing the misleading "python_docs").

2. **Pass collection name through the adapter chain**:
   - `VectorStore.__init__(persist_dir, collection_name="documents")` -- accept as constructor parameter.
   - `ChromaVectorStoreAdapter.__init__(persist_dir, collection_name="documents")` -- pass through to VectorStore.
   - `ProviderFactory.create_vector_store("chroma", persist_dir=..., collection_name=...)` -- pass through.

3. **In `RAGEngine._init_direct()` and `_init_with_factory()`**: read `config.COLLECTION_NAME` and pass it to the vector store constructor.

4. **In `delete_all()`**: use `self.collection_name` instead of the hardcoded string.

### Future: Multi-Tenant Namespacing

If multi-tenancy is needed later, the collection name could be composed as `f"{base_name}_{tenant_id}"`. The configurable parameter enables this without code changes. For now, a single configurable name is sufficient.

### PgVector Consideration

PgVectorStoreAdapter uses a fixed table (`document_chunks`). If namespace isolation is needed for pgvector, it would be done via PostgreSQL schemas or a `tenant_id` column, not collection names. This is out of scope for this refactoring but the repository interface abstraction (Section 1) ensures the switch is clean.

---

## Summary of Changes by File

| File | Change | Section |
|---|---|---|
| `backend/core/config.py` | Replace with unified Pydantic Settings class | 5 |
| `backend/core/advanced_config.py` | Delete entirely | 5 |
| `backend/core/performance/cache/manager.py` | Fix `_cache` -> `cache` in `get_stats()`; add L1 invalidation in `invalidate_by_source()` | 3a, 3c |
| `backend/core/performance/cache/l2_cache.py` | Replace `KEYS` with `SCAN` in `clear()` and `invalidate_by_pattern()` | 3b |
| `backend/core/bm25_retriever.py` | Add pending buffer, deferred rebuild, background save | 4 |
| `backend/core/vector_store.py` | Accept `collection_name` parameter, remove hardcoded "python_docs" | 6 |
| `backend/core/providers/adapters.py` | Pass `collection_name` through ChromaVectorStoreAdapter | 6 |
| `backend/api/conversations.py` | Add file locking, pagination, extract JsonConversationRepository | 2 |
| `backend/core/repositories/` (new) | Define repository interfaces | 1 |

## Ordering

The changes should be applied in this order to minimize risk:

1. **Config unification** (Section 5) -- foundation for everything else. All other changes depend on config values.
2. **Cache bug fixes** (Section 3) -- isolated, low-risk, immediate value.
3. **Collection name** (Section 6) -- small, isolated change.
4. **BM25 optimization** (Section 4) -- self-contained module change.
5. **Conversation storage** (Section 2) -- independent of the other changes.
6. **Repository interfaces** (Section 1) -- largest structural change, do last so the underlying data components are already stable.
