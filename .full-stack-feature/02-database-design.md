# Database & Data Layer Design: 项目结构重构

## Current State Summary

| 数据层 | 当前实现 | 问题 |
|--------|----------|------|
| 会话存储 | JSON 文件（无锁、无分页） | 并发写入损坏、全目录扫描 |
| 向量存储 | ChromaDB（硬编码 collection "python_docs"） | 不可配置 |
| BM25 索引 | pickle 持久化，每次 add 全量重建 | O(N) 性能 |
| 缓存 | L1 内存 + L2 Redis | get_stats() 属性名 Bug、KEYS 命令阻塞 |
| 配置 | 双文件冲突（RERANK_TOP_K: 40 vs 20） | 行为不确定 |

## 1. Repository 接口层

新模块化架构（RetrievalPipeline、IngestionService、GenerationService）需要干净的数据访问边界：

```
backend/core/repositories/
├── __init__.py
├── document_repo.py      # DocumentRepository ABC
├── search_repo.py         # SearchRepository ABC
├── conversation_repo.py   # ConversationRepository ABC
└── cache_repo.py          # CacheRepository ABC
```

核心接口：
- **DocumentRepository**: add_chunks, delete_by_source, get_all_sources, get_document_count
- **SearchRepository**: vector_search, bm25_search, hybrid_search
- **ConversationRepository**: list_conversations(offset, limit), get_conversation, save_conversation, delete_conversation
- **CacheRepository**: get, set, delete, invalidate_by_source, get_stats

## 2. 会话存储改进

**短期**：JSON 文件 + 文件锁 + 侧车索引文件 `_index.json`
**中期：PostgreSQL（pg_conversations.py 已实现 ORM，未接入路由）

## 3. 缓存层修复

- **get_stats()** Bug：`_cache` → `cache`
- **KEYS → SCAN**：L2Cache.clear() 和 invalidate_by_pattern() 改用 SCAN 迭代
- **一致性**：invalidate_by_source() 同时清除 L1 匹配条目

## 4. BM25 优化：批量延迟重建

- 新增 `_pending` 缓冲区和 `_dirty` 标记
- 超过阈值或搜索时才触发重建
- 后台线程异步持久化

## 5. 配置统一

合并为单一 Pydantic Settings 类，删除 advanced_config.py：
- 使用大写字段名 + alias 映射环境变量，保持 `config.RERANK_TOP_K` 向后兼容
- Pydantic 自动类型校验

## 6. Collection 名称可配置

- 新增 `COLLECTION_NAME` 配置项，默认 `"documents"`
- 通过 VectorStore → Adapter → Factory 传递
