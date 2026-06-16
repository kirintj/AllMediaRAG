# RAG 质量全面优化设计

**日期**: 2026-06-16
**状态**: 待审批
**目标**: 全面均衡提升检索精度、检索召回和生成质量

## 背景与现状

### 当前评估指标

| 指标 | 原始数据集 (5题) | 扩展数据集 (5题) | 目标 |
|------|-----------------|-----------------|------|
| Recall@K | 1.0 | 0.50 | ≥0.80 |
| MRR | 0.667 | 0.467 | ≥0.70 |
| Precision | 0.25 | 0.30 | ≥0.50 |
| Faithfulness | 4.8/5 | 4.6/5 | ≥4.5/5 |
| Relevancy | 4.2/5 | 3.6/5 | ≥4.5/5 |
| Keyword Coverage | 0.55 | 0.25 | ≥0.60 |

### 核心瓶颈

1. **检索精度低**（0.25-0.30）：RRF 融合后缺乏过滤，噪音文档进入生成阶段
2. **检索召回不足**（0.50）：单一检索路径覆盖面有限
3. **生成相关性中等**（3.6/5）：上下文噪音影响回答质量
4. **评估数据集太小**：5-20 题不具统计意义

### 资源约束

- GPU 可用，外部 API 可用（Cohere、Cohere rerank 等）
- 知识库为多语言多格式（中文 Markdown、PDF、图片、DOCX 等）

---

## 设计方案：四端均衡优化

### 1. 分块优化：Parent-Child 分层分块

#### 问题

当前单一语义分块（512 tokens）存在矛盾：检索需要小块（精确匹配），生成需要大块（完整上下文）。

#### 方案

引入 **Parent-Child 分层分块**：

```
┌─────────────────────────────────────┐
│  Parent Chunk (1024-2048 chars)     │  ← 送给 LLM 生成回答
│  ┌──────────┐  ┌──────────┐        │
│  │ Child 1  │  │ Child 2  │ ...    │  ← 用于检索匹配
│  └──────────┘  └──────────┘        │
└─────────────────────────────────────┘
```

- **Child chunks**（256-512 chars）：小块用于向量检索和 BM25，提高匹配精度
- **Parent chunks**（1024-2048 chars）：大块包含完整上下文，送给 LLM 生成
- **关联机制**：每个 child 记录 `parent_id`，检索到 child 后自动替换为 parent 送入生成阶段
- **Parent 生成规则**：按固定段落数（3-5 个 child）合并为一个 parent

#### 滑动窗口重叠优化

- 当前 `CHUNK_OVERLAP = 50`（字符），相对于 512 字符的 chunk 仅 ~10%
- 改为 chunk_size 的 20%，即 ~100-200 字符
- 减少分块边界处的信息断裂

#### 存储设计

向量库中的 chunk 元数据新增：

```json
{
  "chunk_id": "child_001",
  "parent_id": "parent_001",
  "chunk_type": "child",
  "source": "file.md",
  "position": 2
}
```

Parent chunk 单独存储，不在检索阶段使用，仅在生成阶段替换。

#### 需要改动的文件

- `backend/core/chunking/semantic_strategy.py` — 增加 parent 生成逻辑
- `backend/core/vector_store.py` / `pgvector_adapter.py` — 元数据支持 parent_id
- `backend/core/rag_engine.py` — 检索后替换 child → parent

---

### 2. 检索优化：多路召回 + 门控 + 多样性

#### 改进 1：增大 Rerank 候选池 + 相关性门控

```
当前流程:  RRF 融合 → Rerank(top 20) → 取 top 5
改进流程:  RRF 融合 → Rerank(top 40) → 相关性门控(≥0.3) → 取 top 5
```

- `RERANK_TOP_K`：20 → 40（让重排序器看到更多候选）
- 新增 **相关性门控**：Rerank 归一化分数 < 0.3 的结果直接丢弃（阈值依据：Cohere rerank-multilingual-v3.0 的归一化分数中，<0.3 通常表示与查询不相关；实际值需通过小规模实验微调确定）
- 如果门控后结果不足 3 条，触发 ConfidenceEvaluator 的二次检索
- 二次检索参数：扩展 top_k、加重 BM25 权重（现有逻辑）

#### 改进 2：引入 ColBERT 延迟交互检索

当前只有 Bi-Encoder（BGE-M3）做向量检索。增加一路 ColBERT v2：

- ColBERT 对 query 和 document 做 token 级别交互，精度高于 Bi-Encoder
- 三路召回：Bi-Encoder 向量 + BM25 + ColBERT → 加权 RRF 融合
- 权重配置：Bi-Encoder 0.4、BM25 0.3、ColBERT 0.3
- ColBERT 模型：`colbert-xm`（多语言版本，适配中英文混合知识库）
- 实现方式：独立的 `ColBERTRetriever` 类，与现有 `BM25Retriever` 并列

RRF 融合公式扩展：

```
score(doc) = Σ weight_i / (k + rank_i + 1)
# i ∈ {bi_encoder, bm25, colbert}
```

#### 改进 3：Multi-Query 去重与多样性增强

当前 multi-query 生成的变体可能过于相似，导致检索结果高度重叠。

- 生成后用 embedding 相似度去重（阈值 0.9）
- 如果去重后变体不足，重新生成补充
- HyDE 文档与 query 变体分开处理，避免语义重复

```
改进前: Q1, Q2(≈Q1), Q3(≈Q1), HyDE(≈Q1)  → 检索结果高度重叠
改进后: Q1, Q2(多样化), Q3(多样化), HyDE    → 检索结果覆盖面广
```

#### 需要改动的文件

- `backend/core/config.py` — 新增 ColBERT 配置项、门控阈值
- `backend/core/rag_engine.py` — 三路召回融合、门控过滤
- `backend/core/retrieval/` — 新增 `colbert_retriever.py`
- `backend/core/query_understanding/multi_query.py` — 去重逻辑
- `backend/core/reranking/manager.py` — 门控逻辑

---

### 3. 生成优化：结构化 Prompt + Self-RAG

#### 改进 1：结构化 Prompt 模板

当前 prompt 直接拼接上下文。改为结构化分段，引导 LLM 更好利用检索结果：

```
## 检索到的参考文档

[来源 1] file_a.md（相关度: 0.92）
内容...

[来源 2] file_b.md（相关度: 0.85）
内容...

[来源 3] file_c.md（相关度: 0.73）
内容...

## 回答要求

1. 优先引用高相关度的来源，使用 [来源 N] 格式标注
2. 如果参考文档不足以完整回答，明确说明哪些部分是推测
3. 对于多部分问题，逐点结构化回答
4. 不要编造文档中不存在的信息
```

关键改动：
- 按 Rerank 分数降序排列上下文，并在 prompt 中标注相关度
- 明确区分"文档支持的回答"和"推测"
- 强化引用格式指令

#### 改进 2：Self-RAG 反思机制

在生成后增加自我反思步骤，检查回答质量：

```
生成回答 → Self-RAG 反思 → 修正/补充 → 最终输出
```

反思 prompt：

```
请检查以下回答：
1. 是否遗漏了检索文档中的关键信息？
2. 是否有未被引用支撑的重要断言？
3. 回答是否完整覆盖了问题的所有方面？

如果发现问题，请生成修正后的完整回答。
如果回答已经足够好，直接返回原回答。
```

**延迟控制策略**：
- 仅对**复杂查询**（analytical / exploratory）启用 Self-RAG
- 简单事实型（factoid）和流程型（procedural）查询跳过反思
- 将 Self-RAG 与现有 CitationVerifier 合并为统一的"后处理阶段"
- 共享 LLM 调用，减少额外延迟

#### 需要改动的文件

- `backend/core/rag_engine.py` — prompt 模板重构、Self-RAG 流程
- `backend/core/verification/citation_verifier.py` — 与 Self-RAG 整合
- `backend/core/query_understanding/classifier.py` — 确保 intent_type 可用于控制反思开关

---

### 4. 评估体系优化

#### 改进 1：扩展评估数据集

从 20 题扩展到 **100+ 题**，覆盖完整的查询类型 × 难度矩阵：

| 查询类型 | Easy | Medium | Hard | 合计 |
|----------|------|--------|------|------|
| Factoid | 10 | 10 | 10 | 30 |
| Analytical | 10 | 10 | 10 | 30 |
| Procedural | 8 | 9 | 8 | 25 |
| Exploratory | 5 | 5 | 5 | 15 |
| **合计** | **33** | **34** | **33** | **100** |

数据来源策略：
- 从知识库文档中用 LLM 自动生成问题（利用 `dataset_tools.py` 的 `generate` 功能）
- 人工审核和修正问题质量
- 确保 `expected_sources` 准确对应实际文档

#### 改进 2：接入 RAGAS 双轨评估

项目已有 `ragas_evaluator.py`，正式接入：

- 每次评估同时运行自定义指标和 RAGAS 指标
- 自定义：Recall@K, MRR, Precision, Hit Rate, Keyword Coverage
- RAGAS：Faithfulness, Answer Relevancy, Context Precision, Context Recall
- 合并到同一份报告中

运行命令：

```bash
cd backend && python eval/run_eval.py --dataset extended --framework both
```

#### 改进 3：实验版本化追踪

在评估报告中自动记录版本信息：

```json
{
  "experiment_id": "exp-2026-06-16-001",
  "timestamp": "2026-06-16T14:30:00+08:00",
  "git_commit": "abc1234",
  "config_snapshot": {
    "chunk_size": 512,
    "chunk_overlap": 100,
    "top_k": 5,
    "rerank_top_k": 40,
    "rerank_strategy": "cohere",
    "rrf_k": 60,
    "use_colbert": true,
    "gate_threshold": 0.3
  },
  "metrics": { ... },
  "dimensional_breakdown": { ... }
}
```

- 存储路径：`backend/eval/experiments/exp-{date}-{seq}.json`
- 用 ConfigComparator 对比不同版本效果

#### 改进 4：回归测试

- 将当前指标作为 **baseline** 固化
- 核心指标回归阈值：Recall@K / MRR / Faithfulness 下降 >5% 触发告警
- 用 `dimensional_eval.py` 按维度监控，避免整体掩盖局部退化
- 可集成到 CI 流程中自动运行

#### 需要改动的文件

- `backend/eval/eval_dataset_extended.json` — 扩展到 100+ 题
- `backend/eval/run_eval.py` — 支持 `--framework both`、自动记录实验信息
- `backend/eval/evaluator.py` — 报告格式增加版本字段
- 新增 `backend/eval/experiments/` 目录存储实验结果

---

## 实施优先级

| 阶段 | 内容 | 预期效果 | 工作量 |
|------|------|---------|--------|
| **Phase 1** | 评估扩展 + Baseline 建立 | 有可靠数据驱动后续优化 | 1 周 |
| **Phase 2** | 相关性门控 + Rerank 扩大 + Multi-Query 去重 | Precision +15-20% | 1 周 |
| **Phase 3** | Parent-Child 分块 + 结构化 Prompt | Recall +10%, Relevancy +0.5 | 1-1.5 周 |
| **Phase 4** | ColBERT 三路召回 + Self-RAG | 全面提升 | 1-1.5 周 |

**建议 Phase 1 → Phase 2 → Phase 3 → Phase 4 顺序执行**，每阶段完成后运行评估验证效果，再决定下一步。

---

## 预期效果

| 指标 | 当前 | Phase 2 后 | Phase 3 后 | Phase 4 后 |
|------|------|-----------|-----------|-----------|
| Recall@K | 0.50 | 0.60 | 0.75 | 0.80+ |
| MRR | 0.467 | 0.55 | 0.65 | 0.70+ |
| Precision | 0.30 | 0.45 | 0.50 | 0.50+ |
| Faithfulness | 4.6/5 | 4.7/5 | 4.8/5 | 4.8/5 |
| Relevancy | 3.6/5 | 4.0/5 | 4.3/5 | 4.5+ |
| Keyword Coverage | 0.25 | 0.40 | 0.55 | 0.60+ |

---

## 不做的事情（YAGNI）

- **不引入 Knowledge Graph**：当前文档规模不需要，复杂度过高
- **不重写向量数据库**：ChromaDB 和 pgvector 双后端已足够
- **不替换 LLM**：MiMo-v2.5 在忠实度上表现优秀
- **不做全自动数据集生成**：人工审核确保质量
