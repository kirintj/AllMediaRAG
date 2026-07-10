# RAG 系统量化评估方案

## 目标

为简历提供可量化的成果数据，包括：
- 检索效果提升（MRR、Hit Rate、Recall）
- 响应时间优化
- 缓存命中率
- RAGAS 评分对比

---

## 评估维度与指标

### 1. 检索效果指标
| 指标 | 说明 | 目标提升 |
|------|------|----------|
| **MRR@10** | 平均倒数排名 | +20% |
| **Hit Rate** | 命中率 | +15% |
| **Recall@K** | 召回率 | +15% |
| **Precision** | 精确率 | +10% |

### 2. 生成质量指标 (RAGAS)
| 指标 | 说明 | 目标 |
|------|------|------|
| **Faithfulness** | 忠实度（0-1） | >0.8 |
| **Answer Relevancy** | 相关性（0-1） | >0.75 |
| **Context Precision** | 上下文精确度 | >0.7 |
| **Context Recall** | 上下文召回率 | >0.75 |

### 3. 工程性能指标
| 指标 | 说明 | 目标 |
|------|------|------|
| **平均响应时间** | 端到端耗时 | <3秒 |
| **缓存命中率** | QA缓存命中 | >30% |
| **索引构建时间** | 文档入库耗时 | - |
| **增量更新时间** | 单文档增量更新 | <5秒 |

---

## 使用方法

### Step 1: 运行 Baseline 评估（优化前配置）

```bash
cd backend

# 1. 临时禁用优化特性（修改 config 或使用简化引擎）
# 2. 运行评估
python eval/run_eval.py --dataset extended --framework both --output eval/baseline_report.json
```

### Step 2: 运行优化后评估

```bash
python eval/run_eval.py --dataset extended --framework both --output eval/optimized_report.json
```

### Step 3: 运行 A/B 对比脚本

```bash
python eval/ab_comparison.py \
  --baseline eval/baseline_report.json \
  --optimized eval/optimized_report.json \
  --output eval/ab_comparison.md
```

### Step 4: 运行性能基准测试

```bash
python eval/performance_benchmark.py --output eval/performance_report.json
```

### Step 5: 生成简历数据

```bash
python eval/generate_resume_data.py \
  --eval-report eval/ab_comparison.md \
  --perf-report eval/performance_report.json \
  --output eval/resume_metrics.md
```

---

## 评估数据集说明

### extended 数据集（推荐）
- **样本数**: 20+ 题
- **覆盖场景**:
  - 简单事实问答（40%）
  - 复杂推理问答（30%）
  - 多文档综合（20%）
  - 模糊/开放问题（10%）
- **难度分布**: 简单 40%、中等 40%、困难 20%

### 问题类型
1. **单文档精确问答**: 测试精确检索能力
2. **跨文档推理**: 测试多路召回和融合能力
3. **模糊问题**: 测试查询改写能力
4. **长尾问题**: 测试覆盖率

---

## 简历成果呈现模板

### 方案 A: 对比数据（最推荐）

```
多模态 RAG 知问系统 | 核心开发者

• 优化检索链路（多路召回 + Rerank + 二次检索），MRR@10 从 0.45 提升至 0.62（+37%），
  Hit Rate 从 68% 提升至 82%（+14%）

• 基于 RAGAS 框架搭建自动化评估，Faithfulness 达到 0.82，Answer Relevancy 达到 0.78

• 实现分层缓存 + 增量索引机制，平均响应时间从 4.2s 降至 2.1s（-50%），
  缓存命中率 35%，支持 100+ 文档热更新
```

### 方案 B: 绝对值（如果没跑 baseline）

```
多模态 RAG 知问系统 | 核心开发者

• 设计多路召回 + Rerank + 引用核查机制，MRR@10 达到 0.62，Hit Rate 达到 82%

• RAGAS 评估：Faithfulness 0.82，Answer Relevancy 0.78，Context Precision 0.72

• 分层缓存机制使重复查询响应 < 100ms，增量索引支持 100+ 文档实时同步
```

---

## 注意事项

1. **Baseline 建立**: 如果没有历史数据，可以先用"简化配置"作为 baseline
   - 禁用 Rerank
   - 禁用查询改写
   - 禁用二次检索

2. **数据一致性**: baseline 和 optimized 必须使用相同的数据集

3. **多次运行**: 建议每个配置运行 3 次取平均值，减少随机性

4. **记录配置**: 保存每次运行的配置参数，便于复现
