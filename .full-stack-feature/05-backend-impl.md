# Backend Implementation Summary (Complete)

## 已创建的文件（新增）

| 文件 | 行数 | 内容 |
|------|------|------|
| `backend/core/services/__init__.py` | 334 | InfraBundle dataclass + create_infra() |
| `backend/core/services/retrieval_pipeline.py` | 575 | 检索管线服务 |
| `backend/core/services/ingestion_service.py` | ~200 | 文档摄入服务 |
| `backend/core/services/generation_service.py` | ~200 | LLM 生成服务 |

## 已修改的文件

| 文件 | 变更 |
|------|------|
| `backend/core/config.py` | 重写为 Pydantic Settings，合并 advanced_config |
| `backend/core/rag_engine.py` | 从 1300 行缩减为 ~200 行 facade，委托给三大服务 |
| `backend/main.py` | lifespan + Depends DI，消除 set_engine() 全局变量 |
| `backend/api/chat.py` | 通过 Depends 获取 retrieval/generation 服务 |
| `backend/api/documents.py` | 通过 Depends 获取 ingestion 服务 |
| `backend/core/vector_store.py` | 直接实现 VectorStoreProvider ABC |
| `backend/core/embedding_service.py` | 直接实现 EmbeddingProvider ABC，修复 O(n²) |
| `backend/core/llm_client.py` | 直接实现 LLMProvider ABC |
| `backend/core/providers/__init__.py` | 移除 adapter 导出 |
| `backend/core/performance/cache/manager.py` | 修复 get_stats() Bug |
| `backend/core/performance/cache/l1_cache.py` | 新增 size() 方法 |
| `backend/core/performance/cache/l2_cache.py` | KEYS → SCAN |
| `backend/core/reranking/manager.py` | 修复 HybridReranker 索引错配 |
| `backend/requirements.txt` | 新增 pydantic-settings |
| `tests/unit/test_advanced_config.py` | 适配新配置 |
| `backend/tests/conftest.py` | 适配新 DI 模式 |

## 已删除的文件

| 文件 | 原因 |
|------|------|
| `backend/core/advanced_config.py` | 合并到 config.py |
| `backend/core/providers/adapters.py` | 核心类直接实现 ABC，无需包装 |

## 关键架构变更

- RAGEngine 从 ~1300 行 → ~200 行 facade
- 模块级 `_engine` 全局变量 → `app.state.*` + `Depends()`
- 双配置系统 → 单一 Pydantic Settings
- 3 个已确认 Bug 已修复
