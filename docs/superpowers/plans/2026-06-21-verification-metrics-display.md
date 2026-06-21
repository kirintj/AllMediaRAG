# Verification Metrics Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 扩展前端「引用核查」卡片，显示全部RAG评估指标，包括检索质量、忠实度、上下文覆盖率等。

**Architecture:** 在现有verification数据结构基础上，新增retrieval_metrics、faithfulness_metrics、context_coverage字段。后端计算所有指标，前端扩展UI显示。

**Tech Stack:** Python (FastAPI), Vue 3, Pinia

---

## 文件结构

### 后端文件
- `backend/core/verification/citation_verifier.py` - 主要修改，添加指标计算方法
- `backend/api/chat.py` - 传递retrieval_results参数
- `backend/tests/test_citation_verifier.py` - 单元测试

### 前端文件
- `frontend/src/features/chat/ChatMessage.vue` - 扩展UI显示

---

## Task 1: 后端 - 添加检索指标计算方法

**Files:**
- Modify: `backend/core/verification/citation_verifier.py`
- Create: `backend/tests/test_citation_verifier.py`

- [ ] **Step 1: 编写失败的测试**

```python
# backend/tests/test_citation_verifier.py
import pytest
from core.verification.citation_verifier import CitationVerifier

class MockLLMClient:
    def generate(self, prompt):
        return '{"claims": [{"text": "test", "supported": true, "source_index": 1}], "unsupported_claims": [], "support_ratio": 1.0}'

def test_compute_retrieval_metrics():
    verifier = CitationVerifier(MockLLMClient())
    
    # 测试正常情况
    retrieval_results = {
        "documents": ["doc1", "doc2", "doc3"],
        "distances": [0.1, 0.2, 0.3]
    }
    metrics = verifier._compute_retrieval_metrics(retrieval_results)
    
    assert metrics["doc_count"] == 3
    assert metrics["max_similarity"] == 0.9  # 1 - 0.1
    assert metrics["avg_similarity"] == 0.8  # 1 - 0.2
    assert "stability" in metrics

def test_compute_retrieval_metrics_empty():
    verifier = CitationVerifier(MockLLMClient())
    
    # 测试空结果
    metrics = verifier._compute_retrieval_metrics(None)
    assert metrics == {}
    
    metrics = verifier._compute_retrieval_metrics({"documents": [], "distances": []})
    assert metrics == {"doc_count": 0}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_compute_retrieval_metrics -v`
Expected: FAIL with "AttributeError: 'CitationVerifier' object has no attribute '_compute_retrieval_metrics'"

- [ ] **Step 3: 编写最小实现**

```python
# backend/core/verification/citation_verifier.py

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
    avg_similarity = sum(similarities) / len(similarities)
    
    # 计算稳定性（方差越小越稳定）
    variance = sum((s - avg_similarity) ** 2 for s in similarities) / len(similarities)
    stability = max(0, 1 - variance * 10)  # 归一化
    
    return {
        "doc_count": doc_count,
        "max_similarity": round(max(similarities), 3),
        "avg_similarity": round(avg_similarity, 3),
        "stability": round(stability, 3),
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_compute_retrieval_metrics -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/verification/citation_verifier.py backend/tests/test_citation_verifier.py
git commit -m "feat: add retrieval metrics calculation to CitationVerifier"
```

---

## Task 2: 后端 - 添加忠实度指标提取方法

**Files:**
- Modify: `backend/core/verification/citation_verifier.py`
- Modify: `backend/tests/test_citation_verifier.py`

- [ ] **Step 1: 编写失败的测试**

```python
# backend/tests/test_citation_verifier.py

def test_extract_faithfulness_metrics():
    verifier = CitationVerifier(MockLLMClient())
    
    # 测试正常情况
    faithfulness = {
        "claims": [
            {"text": "claim1", "supported": True, "source_index": 1},
            {"text": "claim2", "supported": False, "source_index": None},
            {"text": "claim3", "supported": True, "source_index": 2},
        ],
        "unsupported_claims": ["claim2"],
        "support_ratio": 0.667
    }
    metrics = verifier._extract_faithfulness_metrics(faithfulness)
    
    assert metrics["support_ratio"] == 0.667
    assert metrics["claim_count"] == 3
    assert metrics["supported_count"] == 2

def test_extract_faithfulness_metrics_empty():
    verifier = CitationVerifier(MockLLMClient())
    
    # 测试空结果
    metrics = verifier._extract_faithfulness_metrics(None)
    assert metrics == {}
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_extract_faithfulness_metrics -v`
Expected: FAIL with "AttributeError: 'CitationVerifier' object has no attribute '_extract_faithfulness_metrics'"

- [ ] **Step 3: 编写最小实现**

```python
# backend/core/verification/citation_verifier.py

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
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_extract_faithfulness_metrics -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/verification/citation_verifier.py backend/tests/test_citation_verifier.py
git commit -m "feat: add faithfulness metrics extraction to CitationVerifier"
```

---

## Task 3: 后端 - 添加上下文覆盖率计算方法

**Files:**
- Modify: `backend/core/verification/citation_verifier.py`
- Modify: `backend/tests/test_citation_verifier.py`

- [ ] **Step 1: 编写失败的测试**

```python
# backend/tests/test_citation_verifier.py

def test_compute_context_coverage():
    verifier = CitationVerifier(MockLLMClient())
    
    # 测试正常情况
    answer = "这是一个测试回答，长度约为20个字符。"
    contexts = [
        {"text": "这是一个很长的上下文文档，包含了很多内容。" * 10, "metadata": {}},
        {"text": "另一个上下文文档。" * 5, "metadata": {}},
    ]
    coverage = verifier._compute_context_coverage(answer, contexts)
    
    assert isinstance(coverage, float)
    assert 0 <= coverage <= 1

def test_compute_context_coverage_empty():
    verifier = CitationVerifier(MockLLMClient())
    
    # 测试空结果
    coverage = verifier._compute_context_coverage("test", [])
    assert coverage == 0.0
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_compute_context_coverage -v`
Expected: FAIL with "AttributeError: 'CitationVerifier' object has no attribute '_compute_context_coverage'"

- [ ] **Step 3: 编写最小实现**

```python
# backend/core/verification/citation_verifier.py

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

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_compute_context_coverage -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/verification/citation_verifier.py backend/tests/test_citation_verifier.py
git commit -m "feat: add context coverage calculation to CitationVerifier"
```

---

## Task 4: 后端 - 修改verify()方法整合新指标

**Files:**
- Modify: `backend/core/verification/citation_verifier.py`
- Modify: `backend/tests/test_citation_verifier.py`

- [ ] **Step 1: 编写失败的测试**

```python
# backend/tests/test_citation_verifier.py

def test_verify_with_retrieval_results():
    verifier = CitationVerifier(MockLLMClient())
    
    query = "测试问题"
    answer = "测试回答"
    contexts = [{"text": "测试上下文", "metadata": {}}]
    retrieval_results = {
        "documents": ["doc1"],
        "distances": [0.2],
        "metadatas": [{"source": "test.md"}]
    }
    
    result = verifier.verify(query, answer, contexts, retrieval_results=retrieval_results)
    
    assert "retrieval_metrics" in result
    assert "faithfulness_metrics" in result
    assert "context_coverage" in result
    assert result["retrieval_metrics"]["doc_count"] == 1
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_verify_with_retrieval_results -v`
Expected: FAIL with "TypeError: verify() got an unexpected keyword argument 'retrieval_results'"

- [ ] **Step 3: 编写最小实现**

```python
# backend/core/verification/citation_verifier.py

def verify(self, query: str, answer: str, contexts: list[dict], retrieval_results: dict = None) -> dict:
    """核查回答的引用质量

    Args:
        query: 用户查询
        answer: LLM 生成的回答
        contexts: 检索到的上下文 [{"text": str, "metadata": dict}, ...]
        retrieval_results: 检索结果（包含distances等），用于计算检索指标

    Returns:
        {
            "verified": bool,
            "confidence": float,
            "citations": list,
            "hallucination_risk": str,
            "unsupported_claims": list,
            "suggested_disclaimer": str,
            "retrieval_metrics": dict,
            "faithfulness_metrics": dict,
            "context_coverage": float,
        }
    """
    if not answer.strip():
        return self._empty_result()

    # 1. 提取引用标记
    citations = self._extract_citations(answer)

    # 2. 验证忠实度（使用 LLM）
    faithfulness = self._verify_faithfulness(answer, contexts)

    # 3. 计算置信度
    confidence = self._compute_confidence(citations, faithfulness, contexts)

    # 4. 确定风险等级
    hallucination_risk = self._assess_risk(confidence, faithfulness)

    # 5. 生成免责声明
    disclaimer = self._generate_disclaimer(hallucination_risk, faithfulness)

    # 6. 计算新增指标
    retrieval_metrics = self._compute_retrieval_metrics(retrieval_results)
    faithfulness_metrics = self._extract_faithfulness_metrics(faithfulness)
    context_coverage = self._compute_context_coverage(answer, contexts)

    return {
        "verified": confidence >= self.threshold,
        "confidence": round(confidence, 3),
        "citations": citations,
        "hallucination_risk": hallucination_risk,
        "unsupported_claims": faithfulness.get("unsupported_claims", []),
        "suggested_disclaimer": disclaimer,
        "retrieval_metrics": retrieval_metrics,
        "faithfulness_metrics": faithfulness_metrics,
        "context_coverage": context_coverage,
    }
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_verify_with_retrieval_results -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/verification/citation_verifier.py backend/tests/test_citation_verifier.py
git commit -m "feat: integrate new metrics into verify() method"
```

---

## Task 5: 后端 - 修改chat.py传递retrieval_results

**Files:**
- Modify: `backend/api/chat.py`

- [ ] **Step 1: 查看当前代码**

读取`backend/api/chat.py`第140-150行，了解当前verification计算逻辑。

- [ ] **Step 2: 修改代码传递retrieval_results**

```python
# backend/api/chat.py 第140-150行

# 引用核查（仅 RAG 模式且有上下文）
citation_verify_enabled = infra.settings.CITATION_VERIFY_ENABLED
if body.mode == "rag" and citation_verify_enabled and contexts and full_answer.strip():
    try:
        verification = infra.citation_verifier.verify(
            body.message, full_answer, contexts,
            retrieval_results=contexts_data  # 新增参数
        )
        logger.info("Citation verification: confidence=%.2f, risk=%s",
                   verification["confidence"], verification["hallucination_risk"])
    except Exception as e:
        logger.warning("Citation verification failed: %s", e)
```

- [ ] **Step 3: 运行后端服务验证无错误**

Run: `cd backend && python -c "from api.chat import router; print('Import OK')"`
Expected: Import OK

- [ ] **Step 4: 提交**

```bash
git add backend/api/chat.py
git commit -m "feat: pass retrieval_results to citation verifier"
```

---

## Task 6: 前端 - 扩展verification UI显示

**Files:**
- Modify: `frontend/src/features/chat/ChatMessage.vue`

- [ ] **Step 1: 查看当前verification UI**

读取`frontend/src/features/chat/ChatMessage.vue`第48-76行，了解当前verification显示逻辑。

- [ ] **Step 2: 添加新指标显示**

```vue
<!-- frontend/src/features/chat/ChatMessage.vue 第63-76行 -->

<div v-if="showVerification" class="verification-details">
  <!-- 置信度 -->
  <div class="verification-item">
    <span class="label">置信度:</span>
    <span class="value">{{ (message.verification.confidence * 100).toFixed(0) }}%</span>
  </div>
  
  <!-- 检索质量指标 -->
  <div v-if="message.verification.retrieval_metrics" class="metrics-section">
    <div class="metrics-title">检索质量</div>
    <div class="verification-item">
      <span class="label">文档数量:</span>
      <span class="value">{{ message.verification.retrieval_metrics.doc_count }}</span>
    </div>
    <div v-if="message.verification.retrieval_metrics.max_similarity != null" class="verification-item">
      <span class="label">最高相似度:</span>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: (message.verification.retrieval_metrics.max_similarity * 100) + '%' }"></div>
      </div>
      <span class="value">{{ (message.verification.retrieval_metrics.max_similarity * 100).toFixed(0) }}%</span>
    </div>
    <div v-if="message.verification.retrieval_metrics.avg_similarity != null" class="verification-item">
      <span class="label">平均相似度:</span>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: (message.verification.retrieval_metrics.avg_similarity * 100) + '%' }"></div>
      </div>
      <span class="value">{{ (message.verification.retrieval_metrics.avg_similarity * 100).toFixed(0) }}%</span>
    </div>
    <div v-if="message.verification.retrieval_metrics.stability != null" class="verification-item">
      <span class="label">稳定性:</span>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: (message.verification.retrieval_metrics.stability * 100) + '%' }"></div>
      </div>
      <span class="value">{{ (message.verification.retrieval_metrics.stability * 100).toFixed(0) }}%</span>
    </div>
  </div>
  
  <!-- 忠实度指标 -->
  <div v-if="message.verification.faithfulness_metrics" class="metrics-section">
    <div class="metrics-title">忠实度</div>
    <div v-if="message.verification.faithfulness_metrics.support_ratio != null" class="verification-item">
      <span class="label">支撑比例:</span>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: (message.verification.faithfulness_metrics.support_ratio * 100) + '%' }"></div>
      </div>
      <span class="value">{{ (message.verification.faithfulness_metrics.support_ratio * 100).toFixed(0) }}%</span>
    </div>
    <div v-if="message.verification.faithfulness_metrics.claim_count != null" class="verification-item">
      <span class="label">有支撑断言:</span>
      <span class="value">{{ message.verification.faithfulness_metrics.supported_count }}/{{ message.verification.faithfulness_metrics.claim_count }}</span>
    </div>
  </div>
  
  <!-- 上下文覆盖率 -->
  <div v-if="message.verification.context_coverage != null" class="metrics-section">
    <div class="metrics-title">上下文覆盖</div>
    <div class="verification-item">
      <span class="label">覆盖率:</span>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: (message.verification.context_coverage * 100) + '%' }"></div>
      </div>
      <span class="value">{{ (message.verification.context_coverage * 100).toFixed(0) }}%</span>
    </div>
  </div>
  
  <!-- 无支撑断言 -->
  <div v-if="message.verification.unsupported_claims && message.verification.unsupported_claims.length > 0" class="verification-item">
    <span class="label">无支撑断言:</span>
    <span class="value warning">{{ message.verification.unsupported_claims.length }} 条</span>
  </div>
  
  <!-- 免责声明 -->
  <div v-if="message.verification.suggested_disclaimer" class="verification-disclaimer">
    {{ message.verification.suggested_disclaimer }}
  </div>
</div>
```

- [ ] **Step 3: 添加进度条样式**

```vue
<!-- frontend/src/features/chat/ChatMessage.vue style部分 -->

.metrics-section {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--hm-border);
}

.metrics-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--hm-font-secondary);
  margin-bottom: 6px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: var(--hm-bg-container-secondary);
  border-radius: 3px;
  margin: 0 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--hm-brand);
  border-radius: 3px;
  transition: width 0.3s ease;
}
```

- [ ] **Step 4: 启动前端服务验证显示**

Run: `cd frontend && npm run dev`
Expected: 前端服务启动，verification卡片显示新指标

- [ ] **Step 5: 提交**

```bash
git add frontend/src/features/chat/ChatMessage.vue
git commit -m "feat: expand verification UI with retrieval, faithfulness, and coverage metrics"
```

---

## Task 7: 集成测试

**Files:**
- Modify: `backend/tests/test_citation_verifier.py`

- [ ] **Step 1: 编写集成测试**

```python
# backend/tests/test_citation_verifier.py

def test_verify_integration():
    """完整的集成测试"""
    verifier = CitationVerifier(MockLLMClient())
    
    query = "什么是RAG？"
    answer = "RAG是检索增强生成的缩写，它结合了检索和生成两种技术。"
    contexts = [
        {"text": "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的技术。", "metadata": {}},
        {"text": "RAG通过检索相关文档来增强生成质量。", "metadata": {}},
    ]
    retrieval_results = {
        "documents": ["doc1", "doc2"],
        "distances": [0.15, 0.25],
        "metadatas": [{"source": "test1.md"}, {"source": "test2.md"}]
    }
    
    result = verifier.verify(query, answer, contexts, retrieval_results=retrieval_results)
    
    # 验证所有字段都存在
    assert "verified" in result
    assert "confidence" in result
    assert "citations" in result
    assert "hallucination_risk" in result
    assert "unsupported_claims" in result
    assert "suggested_disclaimer" in result
    assert "retrieval_metrics" in result
    assert "faithfulness_metrics" in result
    assert "context_coverage" in result
    
    # 验证检索指标
    assert result["retrieval_metrics"]["doc_count"] == 2
    assert result["retrieval_metrics"]["max_similarity"] == 0.85  # 1 - 0.15
    assert result["retrieval_metrics"]["avg_similarity"] == 0.8   # 1 - 0.2
    
    # 验证忠实度指标
    assert result["faithfulness_metrics"]["claim_count"] > 0
    
    # 验证上下文覆盖率
    assert 0 <= result["context_coverage"] <= 1
```

- [ ] **Step 2: 运行集成测试**

Run: `cd backend && python -m pytest tests/test_citation_verifier.py::test_verify_integration -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_citation_verifier.py
git commit -m "test: add integration test for verification metrics"
```

---

## 完成

所有任务完成。运行完整测试套件验证：

```bash
cd backend && python -m pytest tests/test_citation_verifier.py -v
```

Expected: 所有测试通过
