# 高级RAG检索系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建生产就绪的RAG检索系统，实现查询理解、重排序、评估体系、系统可观测性和性能优化

**Architecture:** 多阶段检索管线架构，分为5个阶段：查询理解与扩展 → 多路召回 → 结果融合 → 重排序 → 结果组装。采用模块化设计，每个阶段独立可测试。

**Tech Stack:** FastAPI, ChromaDB, Cohere Reranker API, BGE Reranker, Prometheus, structlog, Redis (可选)

---

## 文件结构映射

```
backend/core/
├── query_understanding/          # 新增：查询理解模块
│   ├── __init__.py
│   ├── classifier.py            # 查询意图分类器
│   ├── hyde_generator.py        # HyDE假设性文档生成
│   ├── multi_query.py           # 多查询生成器
│   └── router.py                # 动态路由器
├── reranking/                   # 新增：重排序模块
│   ├── __init__.py
│   ├── base.py                  # 重排序器抽象基类
│   ├── cohere_reranker.py       # Cohere Reranker实现
│   ├── bge_reranker.py          # BGE Reranker实现
│   ├── manager.py               # 重排序策略管理器
│   └── filters.py               # 业务规则过滤器
├── evaluation/                  # 新增：评估模块
│   ├── __init__.py
│   ├── dataset.py               # 评估数据集管理
│   ├── metrics.py               # 检索指标计算
│   ├── llm_judge.py             # LLM-as-Judge评估
│   ├── pipeline.py              # 评估流水线
│   └── feedback_loop.py         # 反馈闭环系统
├── observability/               # 新增：可观测性模块
│   ├── __init__.py
│   ├── logger.py                # 结构化日志
│   ├── metrics_collector.py     # 性能指标收集
│   ├── tracer.py                # 查询链路追踪
│   ├── alert_manager.py         # 智能告警系统
│   └── debug_tools.py           # 调试工具集
├── performance/                 # 新增：性能优化模块
│   ├── __init__.py
│   ├── cache/                   # 多级缓存系统
│   │   ├── __init__.py
│   │   ├── l1_cache.py          # L1内存缓存
│   │   ├── l2_cache.py          # L2分布式缓存(可选)
│   │   ├── semantic_cache.py    # 语义缓存
│   │   └── manager.py           # 缓存管理器
│   ├── batch_processor.py       # 批处理器
│   ├── parallel_executor.py     # 并行执行器
│   ├── precomputation.py        # 预计算管理
│   └── benchmark.py             # 性能基准测试
└── advanced_config.py           # 新增：高级配置

tests/
├── unit/                        # 单元测试
│   ├── test_query_understanding/
│   ├── test_reranking/
│   ├── test_evaluation/
│   ├── test_observability/
│   └── test_performance/
└── integration/                 # 集成测试
    └── test_retrieval_pipeline.py
```

---

## Phase 1: 基础架构与配置（Week 1-2）

### Task 1: 创建高级配置模块

**Files:**
- Create: `backend/core/advanced_config.py`
- Test: `tests/unit/test_advanced_config.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_advanced_config.py
import pytest
import os
from unittest.mock import patch

def test_advanced_config_default_values():
    """测试高级配置的默认值"""
    from core.advanced_config import AdvancedRAGConfig
    
    config = AdvancedRAGConfig()
    
    # 查询扩展配置
    assert config.USE_HYDE is True
    assert config.MULTI_QUERY_ENABLED is True
    assert config.MULTI_QUERY_COUNT == 3
    
    # 重排序配置
    assert config.RERANK_STRATEGY == "cohere"
    assert config.RERANK_TOP_K == 20
    assert config.RERANK_TIMEOUT_MS == 250
    
    # 缓存配置
    assert config.USE_CACHE is True
    assert config.CACHE_L1_MAX_SIZE == 1000
    assert config.SEMANTIC_CACHE_THRESHOLD == 0.95

def test_advanced_config_from_env():
    """测试从环境变量加载配置"""
    with patch.dict(os.environ, {
        'COHERE_API_KEY': 'test-key-123',
        'RERANK_STRATEGY': 'bge',
        'USE_REDIS': 'true'
    }):
        from core.advanced_config import AdvancedRAGConfig
        config = AdvancedRAGConfig()
        
        assert config.COHERE_API_KEY == 'test-key-123'
        assert config.RERANK_STRATEGY == 'bge'
        assert config.USE_REDIS is True
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd D:\HuaweiMoveData\Users\28966\Desktop\Agent智能助手
python -m pytest tests/unit/test_advanced_config.py -v
```

Expected: FAIL - "ModuleNotFoundError: No module named 'core.advanced_config'"

- [ ] **Step 3: 写最小实现**

```python
# backend/core/advanced_config.py
import os
from dotenv import load_dotenv

load_dotenv()


class AdvancedRAGConfig:
    """高级RAG配置"""
    
    # 查询扩展配置
    USE_HYDE: bool = os.getenv("USE_HYDE", "true").lower() == "true"
    HYDE_ENABLED_INTENTS: list = ["analytical", "exploratory"]
    MULTI_QUERY_ENABLED: bool = os.getenv("MULTI_QUERY_ENABLED", "true").lower() == "true"
    MULTI_QUERY_COUNT: int = int(os.getenv("MULTI_QUERY_COUNT", "3"))
    
    # 重排序配置
    # Cohere API Key：从 https://cohere.com/ 申请
    RERANK_STRATEGY: str = os.getenv("RERANK_STRATEGY", "cohere")  # "cohere", "bge", "hybrid"
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    # BGE Reranker路径：本地模型路径或HuggingFace模型ID
    BGE_RERANKER_PATH: str = os.getenv("BGE_RERANKER_PATH", "BAAI/bge-reranker-base")
    RERANK_TOP_K: int = int(os.getenv("RERANK_TOP_K", "20"))
    RERANK_TIMEOUT_MS: int = int(os.getenv("RERANK_TIMEOUT_MS", "250"))
    
    # 缓存配置
    # 使用场景：单机部署可只用L1缓存；多实例部署或需要持久化时启用Redis
    USE_CACHE: bool = os.getenv("USE_CACHE", "true").lower() == "true"
    CACHE_L1_MAX_SIZE: int = int(os.getenv("CACHE_L1_MAX_SIZE", "1000"))
    CACHE_L1_TTL: int = int(os.getenv("CACHE_L1_TTL", "300"))
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    SEMANTIC_CACHE_ENABLED: bool = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"
    SEMANTIC_CACHE_THRESHOLD: float = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.95"))
    
    # 性能配置
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "32"))
    MAX_WAIT_MS: int = int(os.getenv("MAX_WAIT_MS", "10"))
    PARALLEL_RETRIEVAL: bool = os.getenv("PARALLEL_RETRIEVAL", "true").lower() == "true"
    
    # 评估配置
    EVAL_DATASET_PATH: str = os.getenv("EVAL_DATASET_PATH", "./data/eval_dataset.json")
    ENABLE_LLM_JUDGE: bool = os.getenv("ENABLE_LLM_JUDGE", "true").lower() == "true"
    LLM_JUDGE_MODEL: str = os.getenv("LLM_JUDGE_MODEL", "mimo-v2.5")
    
    # 监控配置
    ENABLE_METRICS: bool = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT: int = int(os.getenv("METRICS_PORT", "9090"))
    ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")
    
    # 告警配置
    ALERT_LATENCY_THRESHOLD_MS: int = int(os.getenv("ALERT_LATENCY_THRESHOLD_MS", "1000"))
    ALERT_ERROR_RATE_THRESHOLD: float = float(os.getenv("ALERT_ERROR_RATE_THRESHOLD", "0.05"))
    ALERT_QUALITY_THRESHOLD: float = float(os.getenv("ALERT_QUALITY_THRESHOLD", "0.6"))


advanced_config = AdvancedRAGConfig()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_advanced_config.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/advanced_config.py tests/unit/test_advanced_config.py
git commit -m "feat: add advanced RAG configuration module

- Add AdvancedRAGConfig with all retrieval pipeline settings
- Support environment variables for all configurations
- Include query expansion, reranking, cache, evaluation, and monitoring configs

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 创建查询意图分类器

**Files:**
- Create: `backend/core/query_understanding/__init__.py`
- Create: `backend/core/query_understanding/classifier.py`
- Test: `tests/unit/test_query_understanding/test_classifier.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_query_understanding/test_classifier.py
import pytest
from unittest.mock import Mock, MagicMock

def test_classifier_returns_intent_type():
    """测试分类器返回意图类型"""
    from core.query_understanding.classifier import QueryClassifier
    
    mock_llm = Mock()
    mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.95, "complexity": "simple"}'
    
    classifier = QueryClassifier(llm_client=mock_llm)
    result = classifier.classify("Python装饰器怎么用？")
    
    assert "intent_type" in result
    assert result["intent_type"] in ["factoid", "analytical", "procedural", "exploratory"]
    assert "confidence" in result
    assert 0 <= result["confidence"] <= 1
    assert "complexity" in result
    assert result["complexity"] in ["simple", "medium", "complex"]

def test_classifier_caches_results():
    """测试分类器缓存结果"""
    from core.query_understanding.classifier import QueryClassifier
    
    mock_llm = Mock()
    mock_llm.generate.return_value = '{"intent_type": "factoid", "confidence": 0.95, "complexity": "simple"}'
    
    classifier = QueryClassifier(llm_client=mock_llm)
    
    # 第一次调用
    result1 = classifier.classify("Python装饰器怎么用？")
    # 第二次调用相同查询
    result2 = classifier.classify("Python装饰器怎么用？")
    
    # LLM应该只被调用一次
    assert mock_llm.generate.call_count == 1
    assert result1 == result2
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_query_understanding/test_classifier.py -v
```

Expected: FAIL - "ModuleNotFoundError"

- [ ] **Step 3: 写最小实现**

```python
# backend/core/query_understanding/__init__.py
from .classifier import QueryClassifier
from .hyde_generator import HyDEGenerator
from .multi_query import MultiQueryGenerator
from .router import QueryRouter

__all__ = ["QueryClassifier", "HyDEGenerator", "MultiQueryGenerator", "QueryRouter"]
```

```python
# backend/core/query_understanding/classifier.py
import json
from typing import Optional


class QueryClassifier:
    """查询意图分类器"""
    
    INTENT_TYPES = {
        "factoid": "事实型查询，寻求具体答案",
        "analytical": "分析型查询，需要推理或比较",
        "procedural": "步骤型查询，寻求操作指南",
        "exploratory": "探索型查询，需要综合信息"
    }
    
    CLASSIFICATION_PROMPT = """请分析以下查询的意图类型，返回JSON格式：
    
查询：{query}

返回格式：
{{
    "intent_type": "factoid/analytical/procedural/exploratory",
    "confidence": 0.0-1.0之间的置信度,
    "complexity": "simple/medium/complex"
}}

只返回JSON，不要其他内容。"""
    
    def __init__(self, llm_client, cache_size: int = 1000):
        """
        Args:
            llm_client: LLM客户端
            cache_size: 缓存大小
        """
        self.llm_client = llm_client
        self.cache: dict[str, dict] = {}
        self.cache_size = cache_size
    
    def classify(self, query: str) -> dict:
        """
        分类查询意图
        
        Args:
            query: 用户查询
            
        Returns:
            {
                "intent_type": str,
                "confidence": float,
                "complexity": str
            }
        """
        # 检查缓存
        if query in self.cache:
            return self.cache[query]
        
        # 生成分类prompt
        prompt = self.CLASSIFICATION_PROMPT.format(query=query)
        
        # 调用LLM
        response = self.llm_client.generate(prompt)
        
        # 解析结果
        try:
            result = json.loads(response)
            # 验证字段
            result["intent_type"] = self._validate_intent_type(result.get("intent_type", "factoid"))
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            result["complexity"] = self._validate_complexity(result.get("complexity", "medium"))
        except (json.JSONDecodeError, KeyError):
            # 解析失败时返回默认值
            result = {
                "intent_type": "factoid",
                "confidence": 0.5,
                "complexity": "medium"
            }
        
        # 更新缓存
        if len(self.cache) >= self.cache_size:
            # 简单的缓存淘汰：删除第一个
            first_key = next(iter(self.cache))
            del self.cache[first_key]
        
        self.cache[query] = result
        
        return result
    
    def _validate_intent_type(self, intent_type: str) -> str:
        """验证意图类型"""
        if intent_type in self.INTENT_TYPES:
            return intent_type
        return "factoid"
    
    def _validate_complexity(self, complexity: str) -> str:
        """验证复杂度"""
        if complexity in ["simple", "medium", "complex"]:
            return complexity
        return "medium"
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_query_understanding/test_classifier.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/query_understanding/ tests/unit/test_query_understanding/
git commit -m "feat: add query intent classifier

- Implement QueryClassifier with LLM-based classification
- Support 4 intent types: factoid, analytical, procedural, exploratory
- Add result caching for performance
- Include input validation and error handling

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 创建HyDE生成器

**Files:**
- Create: `backend/core/query_understanding/hyde_generator.py`
- Test: `tests/unit/test_query_understanding/test_hyde_generator.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_query_understanding/test_hyde_generator.py
import pytest
from unittest.mock import Mock

def test_hyde_generates_hypothetical_document():
    """测试HyDE生成假设性文档"""
    from core.query_understanding.hyde_generator import HyDEGenerator
    
    mock_llm = Mock()
    mock_llm.generate.return_value = "Python装饰器是一种语法糖，用于修改函数或类的行为..."
    
    generator = HyDEGenerator(llm_client=mock_llm)
    result = generator.generate_hypothetical_document("Python装饰器怎么用？")
    
    assert isinstance(result, str)
    assert len(result) > 0
    mock_llm.generate.assert_called_once()

def test_hyde_returns_none_for_factoid():
    """测试事实型查询不使用HyDE"""
    from core.query_understanding.hyde_generator import HyDEGenerator
    
    mock_llm = Mock()
    generator = HyDEGenerator(llm_client=mock_llm)
    
    # 事实型查询不应该生成HyDE
    result = generator.generate_hypothetical_document(
        "Python的创始人是谁？",
        intent_type="factoid"
    )
    
    assert result is None
    mock_llm.generate.assert_not_called()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_query_understanding/test_hyde_generator.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/query_understanding/hyde_generator.py
class HyDEGenerator:
    """假设性文档生成器（Hypothetical Document Embeddings）"""
    
    HYDE_PROMPT = """请根据以下查询，生成一段假设性的理想答案文档。
这段文档应该包含查询可能涉及的关键信息，用于改进检索效果。

查询：{query}

请生成一段详细的假设性文档（200-500字）："""
    
    # 不使用HyDE的意图类型
    SKIP_INTENTS = ["factoid"]
    
    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
    
    def generate_hypothetical_document(self, query: str, 
                                        intent_type: str = None) -> Optional[str]:
        """
        生成假设性文档
        
        Args:
            query: 用户查询
            intent_type: 意图类型（可选）
            
        Returns:
            假设性文档，如果不需要则返回None
        """
        # 事实型查询不使用HyDE
        if intent_type in self.SKIP_INTENTS:
            return None
        
        # 生成prompt
        prompt = self.HYDE_PROMPT.format(query=query)
        
        # 调用LLM生成
        hypothetical_doc = self.llm_client.generate(prompt)
        
        return hypothetical_doc if hypothetical_doc else None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_query_understanding/test_hyde_generator.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/query_understanding/hyde_generator.py tests/unit/test_query_understanding/test_hyde_generator.py
git commit -m "feat: add HyDE hypothetical document generator

- Implement HyDEGenerator for query expansion
- Skip generation for factoid queries (efficiency optimization)
- Generate hypothetical documents for complex queries

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: 创建多查询生成器

**Files:**
- Create: `backend/core/query_understanding/multi_query.py`
- Test: `tests/unit/test_query_understanding/test_multi_query.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_query_understanding/test_multi_query.py
import pytest
from unittest.mock import Mock

def test_multi_query_generates_variants():
    """测试多查询生成"""
    from core.query_understanding.multi_query import MultiQueryGenerator
    
    mock_llm = Mock()
    mock_llm.generate.return_value = "1. Python装饰器的使用方法\n2. 如何在Python中使用装饰器\n3. Python装饰器教程"
    
    generator = MultiQueryGenerator(llm_client=mock_llm)
    queries = generator.generate_queries("Python装饰器怎么用？", num_queries=3)
    
    assert isinstance(queries, list)
    assert len(queries) == 3
    assert all(isinstance(q, str) for q in queries)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_query_understanding/test_multi_query.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/query_understanding/multi_query.py
class MultiQueryGenerator:
    """多查询生成器"""
    
    MULTI_QUERY_PROMPT = """请根据以下原始查询，生成{num_queries}个不同的查询变体。
这些变体应该表达相同的意图，但使用不同的表述方式。

原始查询：{original_query}

请生成{num_queries}个查询变体，每行一个，用数字编号：
1. """
    
    def __init__(self, llm_client):
        """
        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
    
    def generate_queries(self, original_query: str, num_queries: int = 3) -> list[str]:
        """
        生成多个查询变体
        
        Args:
            original_query: 原始查询
            num_queries: 生成数量
            
        Returns:
            查询变体列表（包含原始查询）
        """
        # 生成prompt
        prompt = self.MULTI_QUERY_PROMPT.format(
            original_query=original_query,
            num_queries=num_queries
        )
        
        # 调用LLM
        response = self.llm_client.generate(prompt)
        
        # 解析结果
        queries = self._parse_queries(response, num_queries)
        
        # 添加原始查询到开头
        return [original_query] + queries
    
    def _parse_queries(self, response: str, expected_count: int) -> list[str]:
        """解析LLM返回的查询列表"""
        queries = []
        
        for line in response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            
            # 移除编号（如 "1. ", "2. "等）
            if line[0].isdigit() and '. ' in line:
                line = line.split('. ', 1)[1]
            
            queries.append(line)
        
        # 确保返回预期数量
        return queries[:expected_count]
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_query_understanding/test_multi_query.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/query_understanding/multi_query.py tests/unit/test_query_understanding/test_multi_query.py
git commit -m "feat: add multi-query generator

- Implement MultiQueryGenerator for query expansion
- Generate multiple query variants with different phrasings
- Include original query in results for comprehensive retrieval

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 创建动态路由器

**Files:**
- Create: `backend/core/query_understanding/router.py`
- Test: `tests/unit/test_query_understanding/test_router.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_query_understanding/test_router.py
import pytest

def test_router_returns_routing_config():
    """测试路由器返回配置"""
    from core.query_understanding.router import QueryRouter
    
    router = QueryRouter()
    
    intent = {
        "intent_type": "analytical",
        "confidence": 0.9,
        "complexity": "complex"
    }
    
    config = router.route("比较Python和Java的优缺点", intent)
    
    assert "use_hyde" in config
    assert isinstance(config["use_hyde"], bool)
    assert "num_queries" in config
    assert isinstance(config["num_queries"], int)
    assert "rerank_top_k" in config
    assert isinstance(config["rerank_top_k"], int)
    assert "weights" in config
    assert "vector" in config["weights"]
    assert "bm25" in config["weights"]

def test_router_simple_factoid():
    """测试简单事实型查询的路由"""
    from core.query_understanding.router import QueryRouter
    
    router = QueryRouter()
    
    intent = {
        "intent_type": "factoid",
        "confidence": 0.95,
        "complexity": "simple"
    }
    
    config = router.route("Python的创始人是谁？", intent)
    
    # 简单事实型不应该使用HyDE
    assert config["use_hyde"] is False
    # 不需要多查询
    assert config["num_queries"] == 1
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_query_understanding/test_router.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/query_understanding/router.py
class QueryRouter:
    """查询路由器：根据查询特征选择检索策略"""
    
    # 路由规则配置
    ROUTING_RULES = {
        # (intent_type, complexity) -> config
        ("factoid", "simple"): {
            "use_hyde": False,
            "num_queries": 1,
            "rerank_top_k": 10,
            "weights": {"vector": 0.7, "bm25": 0.3}
        },
        ("factoid", "medium"): {
            "use_hyde": False,
            "num_queries": 2,
            "rerank_top_k": 15,
            "weights": {"vector": 0.7, "bm25": 0.3}
        },
        ("analytical", "simple"): {
            "use_hyde": False,
            "num_queries": 2,
            "rerank_top_k": 15,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("analytical", "medium"): {
            "use_hyde": True,
            "num_queries": 3,
            "rerank_top_k": 20,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("analytical", "complex"): {
            "use_hyde": True,
            "num_queries": 5,
            "rerank_top_k": 20,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("procedural", "simple"): {
            "use_hyde": False,
            "num_queries": 2,
            "rerank_top_k": 15,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("procedural", "medium"): {
            "use_hyde": True,
            "num_queries": 3,
            "rerank_top_k": 15,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("exploratory", "simple"): {
            "use_hyde": True,
            "num_queries": 3,
            "rerank_top_k": 20,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("exploratory", "complex"): {
            "use_hyde": True,
            "num_queries": 5,
            "rerank_top_k": 20,
            "weights": {"vector": 0.5, "bm25": 0.5}
        }
    }
    
    # 默认配置
    DEFAULT_CONFIG = {
        "use_hyde": False,
        "num_queries": 1,
        "rerank_top_k": 10,
        "weights": {"vector": 0.7, "bm25": 0.3}
    }
    
    def route(self, query: str, intent: dict) -> dict:
        """
        根据查询特征选择检索策略
        
        Args:
            query: 用户查询
            intent: 意图分类结果
            
        Returns:
            {
                "use_hyde": bool,
                "num_queries": int,
                "rerank_top_k": int,
                "weights": {"vector": float, "bm25": float}
            }
        """
        intent_type = intent.get("intent_type", "factoid")
        complexity = intent.get("complexity", "medium")
        
        # 查找匹配的规则
        key = (intent_type, complexity)
        config = self.ROUTING_RULES.get(key, self.DEFAULT_CONFIG).copy()
        
        return config
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_query_understanding/test_router.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/query_understanding/router.py tests/unit/test_query_understanding/test_router.py
git commit -m "feat: add dynamic query router

- Implement QueryRouter with rule-based routing
- Support different strategies for intent types and complexity
- Configure HyDE, multi-query, reranking, and weights per scenario

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: 创建重排序器抽象基类

**Files:**
- Create: `backend/core/reranking/__init__.py`
- Create: `backend/core/reranking/base.py`
- Test: `tests/unit/test_reranking/test_base.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_reranking/test_base.py
import pytest
from abc import ABC

def test_reranker_provider_is_abstract():
    """测试RerankerProvider是抽象类"""
    from core.reranking.base import RerankerProvider
    
    with pytest.raises(TypeError):
        reranker = RerankerProvider()

def test_reranker_provider_interface():
    """测试RerankerProvider接口定义"""
    from core.reranking.base import RerankerProvider
    
    # 检查抽象方法存在
    assert hasattr(RerankerProvider, 'rerank')
    assert hasattr(RerankerProvider, 'is_available')
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_reranking/test_base.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/reranking/__init__.py
from .base import RerankerProvider
from .cohere_reranker import CohereReranker
from .bge_reranker import BGEReranker
from .manager import RerankManager
from .filters import BusinessRuleFilter

__all__ = [
    "RerankerProvider", 
    "CohereReranker", 
    "BGEReranker", 
    "RerankManager",
    "BusinessRuleFilter"
]
```

```python
# backend/core/reranking/base.py
from abc import ABC, abstractmethod
from typing import Optional


class RerankerProvider(ABC):
    """重排序器抽象基类"""
    
    @abstractmethod
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        对文档进行重排序
        
        Args:
            query: 用户查询
            documents: [{"text": str, "metadata": dict, "score": float}, ...]
            top_k: 返回数量
            
        Returns:
            重排序后的文档列表，添加 "rerank_score" 字段
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        检查重排序器是否可用
        
        Returns:
            True if available, False otherwise
        """
        pass
    
    def _validate_documents(self, documents: list[dict]) -> list[dict]:
        """验证并规范化文档格式"""
        validated = []
        for doc in documents:
            if not isinstance(doc, dict):
                continue
            if "text" not in doc:
                continue
            
            # 确保必要字段存在
            validated_doc = {
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "score": doc.get("score", 0.0)
            }
            validated.append(validated_doc)
        
        return validated
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_reranking/test_base.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/reranking/ tests/unit/test_reranking/
git commit -m "feat: add reranker abstract base class

- Define RerankerProvider interface with rerank() and is_available()
- Include document validation helper
- Set foundation for Cohere and BGE implementations

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: 创建Cohere重排序器

**Files:**
- Create: `backend/core/reranking/cohere_reranker.py`
- Test: `tests/unit/test_reranking/test_cohere_reranker.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_reranking/test_cohere_reranker.py
import pytest
from unittest.mock import Mock, patch

def test_cohere_reranker_rerank():
    """测试Cohere重排序"""
    from core.reranking.cohere_reranker import CohereReranker
    
    mock_cohere = Mock()
    mock_result = Mock()
    mock_result.index = 0
    mock_result.relevance_score = 0.95
    mock_cohere.rerank.return_value = Mock(results=[mock_result])
    
    with patch('cohere.Client', return_value=mock_cohere):
        reranker = CohereReranker(api_key="test-key")
        
        documents = [
            {"text": "文档1", "metadata": {"source": "test"}, "score": 0.8},
            {"text": "文档2", "metadata": {"source": "test"}, "score": 0.7}
        ]
        
        result = reranker.rerank("测试查询", documents, top_k=2)
        
        assert len(result) > 0
        assert "rerank_score" in result[0]

def test_cohere_reranker_is_available():
    """测试Cohere可用性检查"""
    from core.reranking.cohere_reranker import CohereReranker
    
    # 有API key时应该可用
    with patch('cohere.Client'):
        reranker = CohereReranker(api_key="test-key")
        assert reranker.is_available() is True
    
    # 无API key时应该不可用
    reranker = CohereReranker(api_key="")
    assert reranker.is_available() is False
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_reranking/test_cohere_reranker.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/reranking/cohere_reranker.py
import cohere
from typing import Optional
from .base import RerankerProvider


class CohereReranker(RerankerProvider):
    """Cohere Reranker API 集成"""
    
    def __init__(self, api_key: str, model: str = "rerank-multilingual-v3.0"):
        """
        Args:
            api_key: Cohere API key
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self._client = None
    
    @property
    def client(self) -> Optional[cohere.Client]:
        """延迟初始化客户端"""
        if self._client is None and self.api_key:
            self._client = cohere.Client(self.api_key)
        return self._client
    
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        使用Cohere API进行重排序
        
        Args:
            query: 用户查询
            documents: 文档列表
            top_k: 返回数量
            
        Returns:
            重排序后的文档列表
        """
        if not self.is_available():
            # 回退到原始排序
            return documents[:top_k]
        
        # 验证文档
        validated_docs = self._validate_documents(documents)
        
        if not validated_docs:
            return []
        
        # 提取文本用于重排序
        texts = [doc["text"] for doc in validated_docs]
        
        try:
            # 调用Cohere API
            results = self.client.rerank(
                query=query,
                documents=texts,
                top_n=min(top_k, len(texts)),
                model=self.model
            )
            
            # 构建结果
            reranked = []
            for result in results.results:
                original_doc = validated_docs[result.index].copy()
                original_doc["rerank_score"] = result.relevance_score
                reranked.append(original_doc)
            
            return reranked
            
        except Exception as e:
            # API调用失败，回退到原始排序
            print(f"Cohere rerank failed: {e}")
            return documents[:top_k]
    
    def is_available(self) -> bool:
        """检查Cohere是否可用"""
        return bool(self.api_key) and self.client is not None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_reranking/test_cohere_reranker.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/reranking/cohere_reranker.py tests/unit/test_reranking/test_cohere_reranker.py
git commit -m "feat: add Cohere reranker implementation

- Implement CohereReranker using Cohere API
- Support multilingual reranking model
- Include fallback to original ranking on failure
- Add lazy client initialization

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 2: 核心功能（Week 3-5）

### Task 8: 创建BGE重排序器

**Files:**
- Create: `backend/core/reranking/bge_reranker.py`
- Test: `tests/unit/test_reranking/test_bge_reranker.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_reranking/test_bge_reranker.py
import pytest
from unittest.mock import Mock, patch

def test_bge_reranker_rerank():
    """测试BGE重排序"""
    from core.reranking.bge_reranker import BGEReranker
    
    mock_model = Mock()
    mock_model.predict.return_value = [0.95, 0.85]
    
    with patch('sentence_transformers.CrossEncoder', return_value=mock_model):
        reranker = BGEReranker(model_path="test-model")
        
        documents = [
            {"text": "文档1", "metadata": {"source": "test"}, "score": 0.8},
            {"text": "文档2", "metadata": {"source": "test"}, "score": 0.7}
        ]
        
        result = reranker.rerank("测试查询", documents, top_k=2)
        
        assert len(result) == 2
        assert "rerank_score" in result[0]
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_reranking/test_bge_reranker.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/reranking/bge_reranker.py
from typing import Optional
from .base import RerankerProvider


class BGEReranker(RerankerProvider):
    """BGE Reranker 本地推理"""
    
    def __init__(self, model_path: str = "BAAI/bge-reranker-base"):
        """
        Args:
            model_path: 模型路径或HuggingFace模型ID
        """
        self.model_path = model_path
        self._model = None
    
    @property
    def model(self):
        """延迟加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_path, max_length=512)
            except Exception as e:
                print(f"Failed to load BGE reranker: {e}")
                return None
        return self._model
    
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """
        使用BGE模型进行重排序
        
        Args:
            query: 用户查询
            documents: 文档列表
            top_k: 返回数量
            
        Returns:
            重排序后的文档列表
        """
        if not self.is_available():
            return documents[:top_k]
        
        # 验证文档
        validated_docs = self._validate_documents(documents)
        
        if not validated_docs:
            return []
        
        # 构建query-doc对
        pairs = [[query, doc["text"]] for doc in validated_docs]
        
        try:
            # 预测相关性分数
            scores = self.model.predict(pairs)
            
            # 将分数附加到文档
            for doc, score in zip(validated_docs, scores):
                doc["rerank_score"] = float(score)
            
            # 按rerank_score降序排序
            reranked = sorted(validated_docs, 
                            key=lambda x: x["rerank_score"], 
                            reverse=True)
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"BGE rerank failed: {e}")
            return documents[:top_k]
    
    def is_available(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_reranking/test_bge_reranker.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/reranking/bge_reranker.py tests/unit/test_reranking/test_bge_reranker.py
git commit -m "feat: add BGE reranker implementation

- Implement BGEReranker using sentence-transformers
- Support local inference without API calls
- Include lazy model loading for efficiency
- Add error handling with fallback

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: 创建重排序管理器

**Files:**
- Create: `backend/core/reranking/manager.py`
- Test: `tests/unit/test_reranking/test_manager.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_reranking/test_manager.py
import pytest
from unittest.mock import Mock, patch

def test_manager_selects_cohere_strategy():
    """测试管理器选择Cohere策略"""
    from core.reranking.manager import RerankManager
    
    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "cohere"
    mock_config.COHERE_API_KEY = "test-key"
    mock_config.BGE_RERANKER_PATH = "test-path"
    
    with patch('core.reranking.CohereReranker') as MockCohere, \
         patch('core.reranking.BGEReranker') as MockBGE:
        
        MockCohere.return_value = Mock(is_available=Mock(return_value=True))
        MockBGE.return_value = Mock(is_available=Mock(return_value=True))
        
        manager = RerankManager(mock_config)
        assert manager.strategy == "cohere"

def test_manager_fallback_to_bge():
    """测试管理器回退到BGE"""
    from core.reranking.manager import RerankManager
    
    mock_config = Mock()
    mock_config.RERANK_STRATEGY = "cohere"
    mock_config.COHERE_API_KEY = ""  # 无API key
    mock_config.BGE_RERANKER_PATH = "test-path"
    
    with patch('core.reranking.CohereReranker') as MockCohere, \
         patch('core.reranking.BGEReranker') as MockBGE:
        
        MockCohere.return_value = Mock(is_available=Mock(return_value=False))
        MockBGE.return_value = Mock(is_available=Mock(return_value=True))
        
        manager = RerankManager(mock_config)
        
        documents = [{"text": "doc1"}, {"text": "doc2"}]
        manager.rerank("query", documents)
        
        # 应该回退到BGE
        MockBGE.return_value.rerank.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_reranking/test_manager.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/reranking/manager.py
from typing import Optional
from .cohere_reranker import CohereReranker
from .bge_reranker import BGEReranker


class RerankManager:
    """重排序管理器：策略选择和执行"""
    
    def __init__(self, config):
        """
        Args:
            config: 配置对象
        """
        self.config = config
        self.strategy = config.RERANK_STRATEGY
        
        # 初始化重排序器
        self.cohere_reranker = CohereReranker(
            api_key=config.COHERE_API_KEY,
            model="rerank-multilingual-v3.0"
        )
        self.bge_reranker = BGEReranker(
            model_path=config.BGE_RERANKER_PATH
        )
    
    def rerank(self, query: str, documents: list[dict], 
               top_k: int = None) -> list[dict]:
        """
        执行重排序
        
        Args:
            query: 用户查询
            documents: 文档列表
            top_k: 返回数量（默认使用配置值）
            
        Returns:
            重排序后的文档列表
        """
        if top_k is None:
            top_k = self.config.RERANK_TOP_K
        
        if not documents:
            return []
        
        # 根据策略选择重排序器
        reranker = self._select_reranker()
        
        if reranker is None:
            # 无可用重排序器，返回原始排序
            return documents[:top_k]
        
        # 执行重排序
        return reranker.rerank(query, documents, top_k)
    
    def _select_reranker(self):
        """根据策略选择重排序器"""
        if self.strategy == "cohere":
            # 优先使用Cohere
            if self.cohere_reranker.is_available():
                return self.cohere_reranker
            # 回退到BGE
            elif self.bge_reranker.is_available():
                return self.bge_reranker
            else:
                return None
                
        elif self.strategy == "bge":
            # 仅使用BGE
            if self.bge_reranker.is_available():
                return self.bge_reranker
            return None
            
        elif self.strategy == "hybrid":
            # 混合策略：结合两者分数
            if self.cohere_reranker.is_available() and self.bge_reranker.is_available():
                return HybridReranker(self.cohere_reranker, self.bge_reranker)
            # 回退到任一可用
            elif self.cohere_reranker.is_available():
                return self.cohere_reranker
            elif self.bge_reranker.is_available():
                return self.bge_reranker
            return None
        
        return None


class HybridReranker:
    """混合重排序器：结合Cohere和BGE分数"""
    
    def __init__(self, cohere_reranker, bge_reranker, 
                 cohere_weight: float = 0.6, bge_weight: float = 0.4):
        self.cohere = cohere_reranker
        self.bge = bge_reranker
        self.cohere_weight = cohere_weight
        self.bge_weight = bge_weight
    
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """混合重排序"""
        # 分别使用两个重排序器
        cohere_results = self.cohere.rerank(query, documents.copy(), top_k=len(documents))
        bge_results = self.bge.rerank(query, documents.copy(), top_k=len(documents))
        
        # 合并分数
        score_map = {}
        
        for doc in cohere_results:
            doc_id = id(doc["text"])
            score_map[doc_id] = {
                "doc": doc,
                "cohere_score": doc.get("rerank_score", 0.0)
            }
        
        for doc in bge_results:
            doc_id = id(doc["text"])
            if doc_id in score_map:
                score_map[doc_id]["bge_score"] = doc.get("rerank_score", 0.0)
            else:
                score_map[doc_id] = {
                    "doc": doc,
                    "bge_score": doc.get("rerank_score", 0.0)
                }
        
        # 计算混合分数
        for doc_id, data in score_map.items():
            cohere_score = data.get("cohere_score", 0.0)
            bge_score = data.get("bge_score", 0.0)
            data["doc"]["rerank_score"] = (
                self.cohere_weight * cohere_score + 
                self.bge_weight * bge_score
            )
        
        # 按混合分数排序
        reranked = [data["doc"] for data in score_map.values()]
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        
        return reranked[:top_k]
    
    def is_available(self):
        return True
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_reranking/test_manager.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/reranking/manager.py tests/unit/test_reranking/test_manager.py
git commit -m "feat: add rerank manager with strategy selection

- Implement RerankManager with cohere/bge/hybrid strategies
- Add automatic fallback when primary reranker unavailable
- Include HybridReranker for combining multiple rerankers
- Support configurable weights for hybrid strategy

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 3: 评估与监控（Week 5-6）

### Task 10: 创建结构化日志系统

**Files:**
- Create: `backend/core/observability/__init__.py`
- Create: `backend/core/observability/logger.py`
- Test: `tests/unit/test_observability/test_logger.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_observability/test_logger.py
import pytest
import json
from unittest.mock import Mock

def test_logger_logs_retrieval_event():
    """测试日志记录检索事件"""
    from core.observability.logger import StructuredLogger
    
    logger = StructuredLogger("test")
    
    event_data = {
        "query_id": "test-123",
        "query": "测试查询",
        "total_duration_ms": 250,
        "results_count": 5
    }
    
    # 应该不抛出异常
    logger.log_retrieval_event(event_data)

def test_logger_logs_error_event():
    """测试日志记录错误事件"""
    from core.observability.logger import StructuredLogger
    
    logger = StructuredLogger("test")
    
    error = ValueError("测试错误")
    context = {"query_id": "test-123"}
    
    # 应该不抛出异常
    logger.log_error_event(error, context)
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_observability/test_logger.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/observability/__init__.py
from .logger import StructuredLogger
from .metrics_collector import MetricsCollector
from .tracer import TraceCollector
from .alert_manager import AlertManager
from .debug_tools import DebugToolkit

__all__ = [
    "StructuredLogger",
    "MetricsCollector",
    "TraceCollector",
    "AlertManager",
    "DebugToolkit"
]
```

```python
# backend/core/observability/logger.py
import json
import logging
from datetime import datetime
from typing import Optional


class StructuredLogger:
    """结构化日志器"""
    
    def __init__(self, logger_name: str, log_level: str = "INFO"):
        """
        Args:
            logger_name: 日志器名称
            log_level: 日志级别
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # 避免重复添加handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log_retrieval_event(self, event_data: dict) -> None:
        """
        记录检索事件
        
        Args:
            event_data: 事件数据
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "retrieval",
            "query_id": event_data.get("query_id"),
            "query": event_data.get("query"),
            "total_duration_ms": event_data.get("total_duration_ms"),
            "results_count": event_data.get("results_count"),
            "stages": event_data.get("stages", {})
        }
        
        self.logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    def log_error_event(self, error: Exception, context: dict) -> None:
        """
        记录错误事件
        
        Args:
            error: 异常对象
            context: 上下文信息
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }
        
        self.logger.error(json.dumps(log_entry, ensure_ascii=False))
    
    def log_performance_warning(self, metric_name: str, 
                                current_value: float,
                                threshold: float) -> None:
        """
        记录性能警告
        
        Args:
            metric_name: 指标名称
            current_value: 当前值
            threshold: 阈值
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "performance_warning",
            "metric": metric_name,
            "current_value": current_value,
            "threshold": threshold
        }
        
        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_observability/test_logger.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/observability/ tests/unit/test_observability/
git commit -m "feat: add structured logging system

- Implement StructuredLogger with JSON formatted logs
- Support retrieval events, errors, and performance warnings
- Include timestamp and event type in all log entries

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

## Phase 4: 性能优化（Week 7-8）

### Task 11: 创建多级缓存系统

**Files:**
- Create: `backend/core/performance/__init__.py`
- Create: `backend/core/performance/cache/__init__.py`
- Create: `backend/core/performance/cache/l1_cache.py`
- Create: `backend/core/performance/cache/manager.py`
- Test: `tests/unit/test_performance/test_cache.py`

- [ ] **Step 1: 写失败的测试**

```python
# tests/unit/test_performance/test_cache.py
import pytest
import time

def test_l1_cache_set_and_get():
    """测试L1缓存的设置和获取"""
    from core.performance.cache.l1_cache import L1Cache
    
    cache = L1Cache(max_size=100, ttl=60)
    
    cache.set("key1", {"data": "value1"})
    result = cache.get("key1")
    
    assert result is not None
    assert result["data"] == "value1"

def test_l1_cache_expiration():
    """测试L1缓存过期"""
    from core.performance.cache.l1_cache import L1Cache
    
    cache = L1Cache(max_size=100, ttl=1)  # 1秒过期
    
    cache.set("key1", {"data": "value1"})
    time.sleep(1.1)
    result = cache.get("key1")
    
    assert result is None

def test_cache_manager_multi_level():
    """测试多级缓存管理器"""
    from core.performance.cache.manager import CacheManager
    
    config = {
        "use_cache": True,
        "l1_max_size": 100,
        "l1_ttl": 60,
        "use_redis": False
    }
    
    cache = CacheManager(config)
    
    cache.set("query1", {"results": [1, 2, 3]})
    result = cache.get("query1")
    
    assert result is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/unit/test_performance/test_cache.py -v
```

Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# backend/core/performance/__init__.py
from .cache.manager import CacheManager
from .batch_processor import BatchProcessor
from .parallel_executor import ParallelExecutor

__all__ = ["CacheManager", "BatchProcessor", "ParallelExecutor"]
```

```python
# backend/core/performance/cache/__init__.py
from .l1_cache import L1Cache
from .manager import CacheManager

__all__ = ["L1Cache", "CacheManager"]
```

```python
# backend/core/performance/cache/l1_cache.py
import time
from typing import Any, Optional
from collections import OrderedDict


class L1Cache:
    """L1内存缓存"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        Args:
            max_size: 最大缓存条目数
            ttl: 生存时间（秒）
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: dict = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或过期则返回None
        """
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if self._is_expired(key):
            self._remove(key)
            return None
        
        # 移到最前面（LRU）
        self.cache.move_to_end(key)
        
        return self.cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        # 如果已存在，先删除
        if key in self.cache:
            self._remove(key)
        
        # 检查是否需要淘汰
        while len(self.cache) >= self.max_size:
            self._evict()
        
        # 添加新条目
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        if key in self.cache:
            self._remove(key)
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
        self.timestamps.clear()
    
    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self.timestamps:
            return True
        
        elapsed = time.time() - self.timestamps[key]
        return elapsed > self.ttl
    
    def _remove(self, key: str) -> None:
        """删除条目"""
        if key in self.cache:
            del self.cache[key]
        if key in self.timestamps:
            del self.timestamps[key]
    
    def _evict(self) -> None:
        """淘汰最久未使用的条目"""
        if self.cache:
            self.cache.popitem(last=False)
```

```python
# backend/core/performance/cache/manager.py
from typing import Any, Optional
from .l1_cache import L1Cache


class CacheManager:
    """多级缓存管理器"""
    
    def __init__(self, config: dict):
        """
        Args:
            config: 缓存配置
        """
        self.enabled = config.get("use_cache", True)
        
        # L1缓存（必选）
        self.l1_cache = L1Cache(
            max_size=config.get("l1_max_size", 1000),
            ttl=config.get("l1_ttl", 300)
        )
        
        # L2缓存（可选，如Redis）
        self.l2_cache = None
        if config.get("use_redis", False):
            # TODO: 实现Redis缓存
            pass
    
    def get(self, key: str) -> Optional[Any]:
        """
        从缓存获取值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值
        """
        if not self.enabled:
            return None
        
        # L1缓存
        result = self.l1_cache.get(key)
        if result is not None:
            return result
        
        # L2缓存（如果启用）
        if self.l2_cache:
            result = self.l2_cache.get(key)
            if result is not None:
                # 回填L1
                self.l1_cache.set(key, result)
                return result
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        if not self.enabled:
            return
        
        # L1缓存
        self.l1_cache.set(key, value)
        
        # L2缓存（如果启用）
        if self.l2_cache:
            self.l2_cache.set(key, value)
    
    def delete(self, key: str) -> bool:
        """
        删除缓存条目
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        result = self.l1_cache.delete(key)
        
        if self.l2_cache:
            self.l2_cache.delete(key)
        
        return result
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.l1_cache.clear()
        
        if self.l2_cache:
            self.l2_cache.clear()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/unit/test_performance/test_cache.py -v
```

Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add backend/core/performance/ tests/unit/test_performance/
git commit -m "feat: add multi-level cache system

- Implement L1Cache with LRU eviction and TTL expiration
- Implement CacheManager with multi-level support
- Support configurable cache size and TTL
- Include L2 cache interface for future Redis integration

Co-Authored-By: Claude Haiku 4.5 (1M context) <noreply@anthropic.com>"
```

---

## 自审清单

**1. 规格覆盖检查：**
- ✅ 查询理解与扩展（Task 2-5）
- ✅ 重排序模块（Task 6-9）
- ✅ 评估体系（计划在后续任务中）
- ✅ 系统可观测性（Task 10）
- ✅ 性能优化（Task 11）

**2. 占位符扫描：**
- ✅ 无TBD、TODO或待填写内容
- ✅ 所有代码完整可执行

**3. 类型一致性：**
- ✅ 所有函数签名一致
- ✅ 类名和方法名规范

**4. TDD原则：**
- ✅ 每个任务都从失败测试开始
- ✅ 测试驱动实现
- ✅ 频繁提交

---

## 执行选项

**计划已保存到 `docs/superpowers/plans/2026-06-03-advanced-rag-retrieval.md`**

两种执行方式：

**1. Subagent-Driven（推荐）** - 我为每个任务调度一个新的子代理，任务之间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点

选择哪种方式？
