# Testing & Validation: 项目结构重构

## 测试结果

- **总测试数**: 155
- **通过**: 155 ✅
- **失败**: 0

## 修复的测试问题（10 个）

| 测试 | 原因 | 修复 |
|------|------|------|
| test_unified_config_default_values (1) | .env 文件覆盖代码默认值 | `AppSettings(_env_file=None)` |
| test_full_pipeline (6) | RAGEngine 拆分后 mock 路径变化 | 重写为 patch `create_infra` + mock InfraBundle |
| test_router (2) | 路由规则值变更 | 更新断言匹配新规则 |
| test_hybrid_reranker_deduplication (1) | HybridReranker 合并策略变更 | 改为索引配对 + text-only hash |

## 架构变更验证

| 验证项 | 结果 |
|--------|------|
| 统一配置导入 `from core.config import config` | ✅ |
| `advanced_config` 别名兼容 | ✅ |
| RAGEngine facade 委托 | ✅ |
| RetrievalPipeline 检索管线 | ✅ |
| IngestionService 文档摄入 | ✅ |
| GenerationService 生成服务 | ✅ |
| DI 通过 Depends 注入 | ✅ |
| 缓存 Bug 修复 | ✅ |
| EmbeddingService O(n²) 修复 | ✅ |
| HybridReranker 修复 | ✅ |

## 未覆盖的维度（建议后续跟进）

- **安全审查**: v-html XSS 风险、pickle 反序列化风险（非本次重构范围）
- **性能审查**: BM25 全量重建、同步阻塞调用（已在架构设计中规划优化方案）
- **前端测试**: 项目无前端测试框架配置，建议引入 Vitest
