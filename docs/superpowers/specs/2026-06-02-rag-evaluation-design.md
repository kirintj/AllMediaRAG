---
title: RAG 评估框架设计文档
date: 2026-06-02
status: approved
---

# RAG 评估框架设计

## 背景

RAG 系统经过混合检索和语义切分优化后，需要量化评估框架来衡量优化效果。核心指标包括检索质量（Recall@K、MRR）和生成质量（Faithfulness、Answer Relevancy）。

## 架构

```
评估数据集 (eval_dataset.json)
        │
        ▼
评估运行器 (RAGEvaluator)
        │
        ├── 检索评估：Recall@K, MRR, Context Precision
        │      └── 对比 expected_sources vs 实际召回
        │
        └── 生成评估：Faithfulness, Answer Relevancy
               └── LLM-as-Judge (MiMo API)
        │
        ▼
评估报告 (JSON + 终端表格输出)
```

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/eval/eval_dataset.json` | 评估数据集 |
| `backend/eval/evaluator.py` | 评估运行器，计算所有指标 |
| `backend/eval/run_eval.py` | 入口脚本 |

## 评估数据集格式

```json
[
  {
    "question": "Python 怎么读取 CSV 文件？",
    "expected_sources": ["csv-module.html"],
    "expected_keywords": ["csv.reader", "open", "with"],
    "reference_answer": "使用 csv 模块的 csv.reader() 函数，配合 open() 打开文件..."
  }
]
```

## 指标定义

### 检索指标（纯代码）

- **Recall@K**：expected_sources 中有多少出现在 top-K 召回结果中。`命中数 / expected_sources 总数`
- **MRR**：expected_sources 中第一个出现的排名倒数。`1 / 第一个命中结果的排名`
- **Context Precision**：召回结果中与 expected_sources 匹配的比例。`匹配数 / 召回总数`

### 生成指标（LLM-as-Judge）

- **Faithfulness**：回答是否忠于检索到的上下文。LLM 打分 1-5
- **Answer Relevancy**：回答是否切题。LLM 打分 1-5

Judge Prompt 模板：

```
你是一个 RAG 系统评估专家。请根据以下信息评估回答质量。

---参考文档---
{context}

---用户问题---
{question}

---参考答案---
{reference_answer}

---系统回答---
{answer}

请评估以下两个维度，每个维度打 1-5 分：
1. Faithfulness（忠实度）：回答是否基于参考文档，没有编造信息
2. Answer Relevancy（相关性）：回答是否切题，是否完整回答了问题

输出 JSON 格式：
{"faithfulness": 分数, "relevancy": 分数, "reasoning": "简要理由"}
```

## 运行方式

```bash
cd backend && python eval/run_eval.py
```

## 输出示例

```
=== RAG 评估报告 ===
样本数: 20

检索指标:
  Recall@5:  0.85
  MRR:       0.72
  Precision: 0.68

生成指标 (LLM-as-Judge):
  Faithfulness:    4.2/5
  Answer Relevancy: 4.0/5

详细结果已保存到 eval/report.json
```

## 不改动的部分

- `core/` 下所有模块 — 评估框架只调用现有接口
- `api/` — 不涉及
- 前端 — 不涉及
