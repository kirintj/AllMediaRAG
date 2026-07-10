# 简历量化数据汇总

---

## 1. 检索效果优化

### 可写入简历的指标

#### 响应时间
- 平均端到端响应时间: **7.52s**
- P95 响应时间: **9.57s**
- 纯检索延迟: **4541ms**

#### 缓存性能
- 缓存命中率: **20.0%**
- 缓存加速比: **3.6x**


# RAG 系统 A/B 对比报告

**样本数**: 50

## 检索效果对比

| 指标 | Baseline | Optimized | 提升 |
|------|----------|-----------|------|
| MRR@10 | 0.9800 | 0.9800 | **0.0%** |
| Hit Rate | 0.9800 | 0.9800 | **0.0%** |
| Recall@K | 0.8800 | 0.9233 | **+4.9%** |
| Precision | 0.8717 | 0.7263 | **-16.7%** |

## 生成质量对比

| 指标 | Baseline | Optimized | 提升 |
|------|----------|-----------|------|
| Faithfulness | 4.78/5 | 4.88/5 | **+2.1%** |
| Answer Relevancy | 4.68/5 | 4.68/5 | **0.0%** |

**关键词覆盖率**: 0.67 → 0.73 (+8.7%)

## 简历可用数据

- **MRR@10**: 0.98 → 0.98 (0.0%)
- **Hit Rate**: 98% → 98% (0.0%)
- **Faithfulness**: 4.88/5
- **Answer Relevancy**: 4.68/5

### 推荐简历写法

```
• 优化检索链路（多路召回 + Rerank + 二次检索），MRR@10 提升 0.0%，Hit Rate 提升 0.0%
```

---

## 2. 简历写法模板

### 模板 A: 有 Baseline 对比（最推荐）

```markdown
多模态 RAG 知问系统 | 核心开发者

• 设计离线-在线全链路 RAG 系统，支持 PDF/MD/图文等多模态文档解析与索引

• 优化检索链路（多路召回 + Rerank + 引用核查 + 低置信度二次检索），
  MRR@10 提升 X%，Hit Rate 提升 Y%

• 基于 RAGAS 搭建自动化评估框架，Faithfulness 达到 X.XX，
  Answer Relevancy 达到 X.XX

• 实现分层缓存 + 增量索引机制，平均响应时间 X.Xs，
  缓存命中率 XX%，支持 N+ 文档热更新
```

### 模板 B: 仅绝对值

```markdown
多模态 RAG 知问系统 | 核心开发者

• 实现多路召回（向量 + BM25）+ Rerank 精排 + 引用核查机制，
  MRR@10 达到 0.XX，Hit Rate 达到 XX%

• RAGAS 评估：Faithfulness 0.XX，Answer Relevancy 0.XX，
  Context Precision 0.XX

• 分层缓存机制：重复查询响应 <100ms，缓存命中率 XX%
• 增量索引：支持 N+ 文档实时同步，单文档更新 <5s
```

### 模板 C: 技术关键词版本（适合 ATS 筛选）

```markdown
• RAG / Retrieval-Augmented Generation 全链路优化
• 多路召回（Dense Retrieval + BM25）、Cross-Encoder Reranking
• ChromaDB 向量数据库、FAISS 索引优化
• OCR + VLM 多模态文档解析
• RAGAS 评估框架、自动化 A/B 测试
• 分布式缓存、增量索引、流式响应
```

---

## 3. 数据填写指南

运行以下命令获取填入数据：

```bash
# 1. 运行 baseline 评估
python eval/run_eval.py --dataset extended --framework both --output eval/baseline.json

# 2. 运行优化后评估
python eval/run_eval.py --dataset extended --framework both --output eval/optimized.json

# 3. 生成对比数据
python eval/ab_comparison.py --baseline eval/baseline.json --optimized eval/optimized.json

# 4. 运行性能测试
python eval/performance_benchmark.py --dataset eval/eval_dataset_extended.json
```
