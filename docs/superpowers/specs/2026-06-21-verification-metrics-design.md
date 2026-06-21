# 2026-06-21-verification-metrics-design.md

## 概述

扩展前端「引用核查」卡片，显示全部RAG评估指标，包括检索质量、忠实度、上下文覆盖率等。

## 目标

1. 在对话完成后显示完整的评估数据
2. 扩展现有verification数据结构
3. 异步计算，不阻塞回答显示
4. 保持UI简洁，默认折叠详细指标

## 数据结构

### 后端返回的verification数据

```python
{
    # 现有字段
    "verified": bool,
    "confidence": float,  # 0-1
    "citations": list,
    "hallucination_risk": str,  # "low" | "medium" | "high"
    "unsupported_claims": list,
    "suggested_disclaimer": str,
    
    # 新增字段
    "retrieval_metrics": {
        "doc_count": int,  # 检索到的文档数量
        "max_similarity": float,  # 最高相似度
        "avg_similarity": float,  # 平均相似度
        "stability": float,  # 稳定性分数
    },
    "faithfulness_metrics": {
        "support_ratio": float,  # 忠实度支撑比例
        "claim_count": int,  # 总断言数
        "supported_count": int,  # 有支撑的断言数
    },
    "context_coverage": float,  # 上下文覆盖率
}
```

## 后端实现

### 修改文件

- `backend/core/verification/citation_verifier.py`

### 主要改动

1. 在`verify()`方法中增加`retrieval_results`参数
2. 新增`_compute_retrieval_metrics()`方法计算检索指标
3. 新增`_extract_faithfulness_metrics()`方法提取忠实度指标
4. 新增`_compute_context_coverage()`方法计算上下文覆盖率

### 代码改动

```python
def verify(self, query, answer, contexts, retrieval_results=None):
    # ... 现有逻辑 ...
    
    # 新增：计算检索指标
    retrieval_metrics = self._compute_retrieval_metrics(retrieval_results)
    
    # 新增：提取忠实度指标
    faithfulness_metrics = self._extract_faithfulness_metrics(faithfulness)
    
    # 新增：计算上下文覆盖率
    context_coverage = self._compute_context_coverage(answer, contexts)
    
    return {
        # 现有字段...
        "retrieval_metrics": retrieval_metrics,
        "faithfulness_metrics": faithfulness_metrics,
        "context_coverage": context_coverage,
    }

def _compute_retrieval_metrics(self, retrieval_results):
    """计算检索质量指标"""
    if not retrieval_results:
        return {}
    
    distances = retrieval_results.get("distances", [])
    doc_count = len(retrieval_results.get("documents", []))
    
    if not distances:
        return {"doc_count": doc_count}
    
    # 计算相似度（距离越小越相似）
    similarities = [1 - d for d in distances]
    
    return {
        "doc_count": doc_count,
        "max_similarity": round(max(similarities), 3),
        "avg_similarity": round(sum(similarities) / len(similarities), 3),
        "stability": round(1 - (sum((s - sum(similarities)/len(similarities))**2 for s in similarities) / len(similarities)), 3),
    }

def _extract_faithfulness_metrics(self, faithfulness):
    """提取忠实度指标"""
    if not faithfulness:
        return {}
    
    claims = faithfulness.get("claims", [])
    supported_count = len([c for c in claims if c.get("supported")])
    
    return {
        "support_ratio": faithfulness.get("support_ratio", 0.0),
        "claim_count": len(claims),
        "supported_count": supported_count,
    }

def _compute_context_coverage(self, answer, contexts):
    """计算上下文覆盖率"""
    if not contexts:
        return 0.0
    
    answer_length = len(answer)
    context_length = sum(len(c.get("text", "")) for c in contexts)
    
    if context_length == 0:
        return 0.0
    
    return round(min(answer_length / context_length, 1.0), 3)
```

### 修改chat.py

```python
# 在verification计算时传递retrieval_results
verification = infra.citation_verifier.verify(
    body.message, full_answer, contexts,
    retrieval_results=contexts_data  # 新增参数
)
```

## 前端实现

### 修改文件

- `frontend/src/features/chat/ChatMessage.vue`

### UI设计

```
┌─────────────────────────────────────────┐
│ 🛡️ 引用核查                    [低风险] │
├─────────────────────────────────────────┤
│ 置信度: ████████████░░░░ 75%           │
├─────────────────────────────────────────┤
│ ▼ 详细指标                              │
│                                         │
│ 检索质量                                │
│   文档数量: 5                           │
│   最高相似度: ████████████░░ 82%        │
│   平均相似度: ████████░░░░░░ 65%        │
│   稳定性: ████████████░░░░ 78%          │
│                                         │
│ 忠实度                                  │
│   支撑比例: ████████████░░ 75%          │
│   有支撑断言: 3/4                        │
│                                         │
│ 上下文覆盖                              │
│   覆盖率: ████████░░░░░░ 60%            │
├─────────────────────────────────────────┤
│ ⚠️ 部分内容可能缺乏文档支撑，请谨慎参考。│
└─────────────────────────────────────────┘
```

### 代码改动

1. 添加指标显示组件
2. 添加进度条样式
3. 扩展verification-details区域

## 数据流

1. 用户发送消息
2. 后端开始流式返回回答
3. 流式完成后，后端异步计算verification（包括所有指标）
4. 后端发送done消息，包含完整verification数据
5. 前端接收数据，更新UI显示

## 性能考虑

- verification计算在流式完成后执行，不阻塞用户看到回答
- 计算时间约100-500ms（取决于LLM响应时间）
- 前端默认折叠详细指标，减少初始渲染负担

## 测试计划

1. 单元测试：测试新增的指标计算方法
2. 集成测试：测试完整的对话流程
3. UI测试：验证指标显示正确性

## 依赖

- 无新增依赖
- 复用现有的marked库（用于Markdown渲染）

## 风险和缓解

1. **风险**：计算时间过长影响用户体验
   **缓解**：异步计算，不阻塞回答显示

2. **风险**：指标计算不准确
   **缓解**：使用现有的成熟算法，添加单元测试

3. **风险**：UI过于复杂
   **缓解**：默认折叠，只显示关键指标
