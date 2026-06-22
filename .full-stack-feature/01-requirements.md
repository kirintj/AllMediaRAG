# Requirements: 项目结构重构 — 企业规范化改造

## Problem Statement

当前多模态 RAG 项目存在严重的架构债务，影响开发效率和系统可靠性：

1. **RAGEngine 是 God Object**（~1300 行，15+ 依赖），同时承担检索、摄入、生成等所有职责，无法独立测试
2. **双配置系统冲突**（config.py vs advanced_config.py），默认值不同，router 又有自己的硬编码值
3. **模块级单例 + setter 注入**，测试必须 monkeypatch 全局变量
4. **同步/异步检索逻辑重复**（full_retrieve vs full_retrieve_async），修改一处易遗漏另一处
5. **前端单一 God Store** 管理所有状态，认证状态散落在 App.vue 本地 ref 中
6. **Adapter 过度抽象**，核心类未实现 ABC，额外的适配器层无实际价值
7. **多个已确认 Bug**：CacheManager 属性名错误、EmbeddingService O(n²) 缓存、HybridReranker 索引错配

用户是开发团队成员，痛点在于每次修改都需要理解整个 RAGEngine 才能动手，且无法对单个模块写单元测试。

## Acceptance Criteria

- [ ] RAGEngine 拆分为独立的 RetrievalPipeline、IngestionService、GenerationService
- [ ] 配置系统合并为单一源（Pydantic Settings），消除 config.py / advanced_config.py 冲突
- [ ] 使用 FastAPI `Depends` + `lifespan` 管理依赖注入，消除模块级 setter
- [ ] 同步/异步检索逻辑统一为单一实现
- [ ] 让核心类直接实现 ABC，删除无用的 adapter 包装层
- [ ] 前端 Pinia Store 拆分为 auth/chat/documents 三个独立 store
- [ ] 前端认证状态从 App.vue 本地 ref 迁移到 useAuthStore
- [ ] 修复 CacheManager.get_stats() 属性名 Bug
- [ ] 修复 EmbeddingService._cache_put O(n²) Bug
- [ ] 修复 HybridReranker 索引合并 Bug
- [ ] 现有 62+ 个单元测试全部通过
- [ ] API 接口路径和参数向后兼容
- [ ] 项目可以通过 Docker Compose 部署

## Scope

### In Scope

- 后端目录结构重组（按功能模块划分）
- 后端核心模块拆分（RAGEngine -> 3 个独立服务）
- 配置系统统一（Pydantic Settings）
- 依赖注入改造（FastAPI Depends + lifespan）
- 删除无用 adapter 层，让核心类直接实现 ABC
- 统一同步/异步实现
- 已确认 Bug 修复
- 前端 Store 拆分
- 前端认证状态管理规范化
- 前端目录按 feature 组织

### Out of Scope

- 新功能开发（OCR/VLM 增强、新检索算法等）
- TypeScript 迁移（可作为后续独立任务）
- 性能优化（缓存策略改进、批量处理优化等）
- 前端 UI/UX 重新设计
- 数据库 schema 变更（conversation 存储迁移到 PostgreSQL）
- CI/CD 流水线搭建

## Technical Constraints

1. 保持 FastAPI + Vue 3 + ChromaDB/pgvector 技术栈不变
2. 现有 62+ 个单元测试必须全部通过
3. API 接口路径和参数保持向后兼容
4. 保持 Docker Compose 部署能力
5. 渐进式重构，保留核心算法逻辑不变
6. Python 3.11+，Node.js 18+

## Technology Stack

| 层级 | 技术 | 变更 |
|------|------|------|
| 前端 | Vue 3 + Vite 8 + Pinia 3 | 不变 |
| 后端 | FastAPI + Pydantic v2 | 引入 Pydantic Settings |
| 数据库 | ChromaDB / pgvector | 不变 |
| 缓存 | Redis + 内存 LRU | 不变 |
| 测试 | pytest | 不变 |

## Dependencies

- **上游依赖**：无（纯内部重构）
- **下游影响**：API 接口保持兼容，前端和后端同时重构需要协调
- **外部服务**：MiMo API、Cohere API、SiliconFlow API 保持不变

## Configuration

- Stack: Python/FastAPI + Vue 3 (auto-detected)
- API Style: REST
- Complexity: Complex（涉及全栈重构，20+ 文件变更）
