# Data Layer Implementation Summary

## 已完成的修改

### 1. CacheManager.get_stats() Bug 修复
- **文件**: `backend/core/performance/cache/l1_cache.py` — 新增 `size()` 方法
- **文件**: `backend/core/performance/cache/manager.py` — `self.l1_cache._cache` → `self.l1_cache.size()`

### 2. EmbeddingService O(n²) Bug 修复
- **文件**: `backend/core/embedding_service.py` — 将 `to_encode_text` 加入 `zip` 迭代，消除 `.index()` 线性查找

### 3. HybridReranker 索引错配修复
- **文件**: `backend/core/reranking/manager.py` — 新增 `_doc_key()` 方法，用 source+text hash 作为合并 key 替代位置索引

### 4. L2Cache KEYS → SCAN
- **文件**: `backend/core/performance/cache/l2_cache.py` — `clear()` 和 `invalidate_by_pattern()` 改用 cursor-based SCAN 迭代
