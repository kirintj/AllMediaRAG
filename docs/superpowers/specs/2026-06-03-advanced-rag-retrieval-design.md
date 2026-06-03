# 高级RAG检索系统设计文档

**项目名称**：Agent智能助手 - RAG检索系统模块化升级  
**设计版本**：v1.0  
**创建日期**：2026-06-03  
**状态**：已批准  

---

## 1. 概述

### 1.1 项目背景

当前RAG系统已实现基础功能（混合检索、语义分块、评估系统），但距离生产就绪仍有差距。本文档设计一个模块化升级方案，全面提升检索质量、性能和可观测性。

### 1.2 设计目标

**核心目标**：构建生产就绪的RAG检索系统

**具体目标**：
1. **检索质量**：融合策略优化、添加重排序、实现查询扩展
2. **性能**：低延迟（200-400ms），适合实时交互
3. **评估体系**：建立完整的评估系统和标注数据集
4. **可观测性**：全面的监控、日志和调试能力
5. **可扩展性**：支持未来功能升级

### 1.3 技术约束

- **知识库规模**：小规模（几千到几万条文档）
- **延迟要求**：P99延迟 < 500ms
- **技术栈**：FastAPI + ChromaDB + Vue 3（保持现有）
- **部署环境**：单机部署，可选Redis支持

---

## 2. 系统架构

### 2.1 整体架构

采用**多阶段检索管线**架构，将检索流程分为清晰的阶段：

```
用户查询
    ↓
┌─────────────────────────────────────────┐
│  Stage 1: 查询理解与扩展               │
│  - 查询意图分类                         │
│  - HyDE（假设性文档生成）               │
│  - 多查询生成                           │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 2: 多路召回                      │
│  - 向量检索（ChromaDB）                 │
│  - BM25检索                             │
│  - 可选：知识图谱查询                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 3: 结果融合与初筛                │
│  - 加权RRF融合                          │
│  - 相似度阈值过滤                       │
│  - 去重策略                             │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 4: 重排序                        │
│  - Cross-Encoder精排                    │
│  - 业务规则过滤                         │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Stage 5: 结果组装与缓存                │
│  - 上下文组装                           │
│  - 缓存更新                             │
│  - 元数据附加                           │
└─────────────────────────────────────────┘
    ↓
检索结果输出
```

### 2.2 核心技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 检索引擎 | ChromaDB + BM25 | 保持现有，优化配置 |
| 重排序 | Cohere Reranker（云端）/ BGE Reranker（本地） | 新增模块 |
| 查询扩展 | LLM驱动（MiMo） | 新增模块 |
| 缓存 | 内存LRU + Redis（可选） | 新增模块 |
| 监控 | 结构化日志 + Prometheus | 新增模块 |
| 评估 | LLM-as-Judge + 自动化流水线 | 扩展现有 |

### 2.3 架构优势

1. **模块解耦**：每个阶段独立，便于测试和优化
2. **策略灵活**：可根据查询类型动态调整各阶段行为
3. **可观测性**：在每个阶段都可插入监控点
4. **性能优化**：支持并行处理和缓存策略

---

## 3. 核心模块设计

### 3.1 查询理解与扩展模块

#### 3.1.1 查询意图分类

```python
class QueryClassifier:
    """查询意图分类器"""
    
    INTENT_TYPES = {
        "factoid": "事实型查询，寻求具体答案",
        "analytical": "分析型查询，需要推理或比较",
        "procedural": "步骤型查询，寻求操作指南",
        "exploratory": "探索型查询，需要综合信息"
    }
    
    def classify(self, query: str) -> dict:
        """
        返回: {
            "intent_type": str,
            "confidence": float,
            "complexity": str  # "simple", "medium", "complex"
        }
        """
```

**分类策略**：
- 使用LLM进行快速分类（1-2句话prompt）
- 缓存分类结果，相同查询直接复用
- 根据分类结果调整检索策略

#### 3.1.2 HyDE（假设性文档嵌入）

```python
class HyDEGenerator:
    """假设性文档生成器"""
    
    def generate_hypothetical_document(self, query: str) -> str:
        """
        生成假设性文档，用于改进向量检索
        
        流程：
        1. LLM生成一段"理想答案"
        2. 对该答案进行向量编码
        3. 用该向量进行检索（而非原始查询）
        """
```

**优化策略**：
- 根据查询意图决定是否使用HyDE
- 事实型查询：直接使用原始查询（效率更高）
- 复杂查询：使用HyDE（提升召回率）
- 并行执行HyDE生成和原始查询检索

#### 3.1.3 多查询生成

```python
class MultiQueryGenerator:
    """多查询生成器"""
    
    def generate_queries(self, original_query: str, num_queries: int = 3) -> list[str]:
        """
        生成多个查询变体
        
        策略：
        - 同义词替换
        - 句式改写
        - 细节补充
        - 抽象化/具体化
        """
```

#### 3.1.4 动态路由

```python
class QueryRouter:
    """查询路由器"""
    
    def route(self, query: str, intent: dict) -> dict:
        """
        根据查询特征选择检索策略
        
        返回: {
            "use_hyde": bool,
            "num_queries": int,
            "rerank_top_k": int,
            "weights": {"vector": float, "bm25": float}
        }
        """
```

**路由规则示例**：
- 事实型 + 简单 → 原始查询，top-10重排
- 分析型 + 复杂 → HyDE + 5个查询变体，top-20重排
- 步骤型 → 多查询扩展，top-15重排

### 3.2 重排序模块

#### 3.2.1 重排序器抽象层

```python
class RerankerProvider(ABC):
    """重排序器抽象基类"""
    
    @abstractmethod
    def rerank(self, query: str, documents: list[dict], top_k: int) -> list[dict]:
        """
        对文档进行重排序
        
        Args:
            query: 用户查询
            documents: [{"text": str, "metadata": dict, "score": float}, ...]
            top_k: 返回数量
            
        Returns:
            重排序后的文档列表，添加 "rerank_score" 字段
        """
```

#### 3.2.2 Cohere Reranker（云端）

```python
class CohereReranker(RerankerProvider):
    """Cohere Reranker API 集成"""
    
    def __init__(self, api_key: str, model: str = "rerank-multilingual-v3.0"):
        self.client = cohere.Client(api_key)
        self.model = model
```

**优势**：
- 多语言支持优秀
- 无需本地GPU
- 延迟稳定（100-200ms）

**API调用优化**：
- 批量处理：每批100条限制
- 结果缓存：相同query-doc对缓存
- 超时处理：250ms超时回退

#### 3.2.3 BGE Reranker（本地）

```python
class BGEReranker(RerankerProvider):
    """BGE Reranker 本地推理"""
    
    def __init__(self, model_path: str = "BAAI/bge-reranker-base"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_path, max_length=512)
```

**本地推理优化**：
- 批量编码：一次处理多个query-doc对
- 半精度推理：使用FP16减少内存和计算
- 模型预加载：服务启动时加载模型

#### 3.2.4 重排序策略管理器

```python
class RerankManager:
    """重排序管理器"""
    
    def __init__(self, config):
        self.cohere_reranker = CohereReranker(config.COHERE_API_KEY)
        self.bge_reranker = BGEReranker(config.BGE_RERANKER_PATH)
        self.strategy = config.RERANK_STRATEGY  # "cohere", "bge", "hybrid"
```

**策略选择逻辑**：
- "cohere": 优先使用Cohere，失败时回退到BGE
- "bge": 仅使用本地BGE
- "hybrid": 结合两者分数（加权平均）

#### 3.2.5 业务规则过滤

```python
class BusinessRuleFilter:
    """业务规则过滤器"""
    
    def apply_filters(self, documents: list[dict], rules: dict) -> list[dict]:
        """
        应用业务规则过滤
        
        规则示例：
        - 文档时效性：优先返回最近更新的文档
        - 来源可信度：官方文档 > 社区博客
        - 内容类型：代码示例 > 纯文字描述
        - 语言偏好：中文 > 英文
        """
```

### 3.3 评估体系模块

#### 3.3.1 评估数据集管理

```python
class EvaluationDataset:
    """评估数据集管理器"""
    
    def load_dataset(self, path: str) -> list[dict]:
        """
        数据格式：
        {
            "query": str,
            "expected_answer": str,
            "expected_sources": list[str],
            "difficulty": str,
            "intent_type": str,
            "metadata": dict
        }
        """
```

**数据集构建策略**：
- 种子数据：从现有对话日志中提取高质量问答对
- 数据增强：通过LLM生成查询变体
- 人工审核：确保标注质量
- 版本管理：支持数据集版本控制

#### 3.3.2 离线评估指标

```python
class RetrievalMetrics:
    """检索质量指标计算器"""
    
    def calculate_metrics(self, results: list[dict], expected: list[dict]) -> dict:
        """
        计算全面的检索指标
        
        返回：{
            "recall@k": float,
            "mrr": float,
            "ndcg@k": float,
            "map": float,
            "precision@k": float,
            "hit_rate": float,
            "diversity": float,
            "coverage": float,
        }
        """
```

#### 3.3.3 LLM-as-Judge评估

```python
class LLMJudge:
    """LLM自动评估器"""
    
    def evaluate_retrieval_quality(self, query: str, retrieved_docs: list[str],
                                    expected_answer: str) -> dict:
        """
        评估维度：
        - 相关性：检索文档与查询的相关程度
        - 覆盖度：检索文档对答案的支持程度
        - 信息密度：关键信息的集中度
        """
    
    def evaluate_generation_quality(self, query: str, generated_answer: str,
                                     source_docs: list[str]) -> dict:
        """
        评估维度：
        - 忠实度：答案是否基于源文档，无幻觉
        - 相关性：答案是否切题
        - 完整性：答案是否完整覆盖问题
        - 连贯性：答案是否逻辑清晰
        """
```

#### 3.3.4 自动化评估流水线

```python
class EvaluationPipeline:
    """评估流水线"""
    
    def run_offline_evaluation(self, dataset_path: str, config: dict) -> dict:
        """
        流程：
        1. 加载评估数据集
        2. 执行批量检索
        3. 计算各项指标
        4. 生成评估报告
        5. 对比历史版本
        """
    
    def run_ab_test(self, variant_a: dict, variant_b: dict,
                    test_queries: list[str]) -> dict:
        """A/B测试框架"""
```

#### 3.3.5 评估数据闭环

```python
class FeedbackLoop:
    """反馈闭环系统"""
    
    def collect_hard_cases(self, query: str, results: list[dict],
                           user_feedback: dict) -> None:
        """收集困难案例"""
    
    def update_dataset(self, new_cases: list[dict]) -> None:
        """将新案例加入评估数据集"""
    
    def retrain_models(self, updated_dataset: dict) -> None:
        """基于新数据优化模型"""
```

**闭环流程**：
1. **收集**：在线收集用户反馈和困难案例
2. **分析**：定期分析失败模式和改进机会
3. **标注**：人工审核和标注新案例
4. **优化**：基于新数据调整模型和参数
5. **验证**：离线评估改进效果
6. **部署**：灰度发布改进版本

### 3.4 系统可观测性模块

#### 3.4.1 结构化日志系统

```python
class StructuredLogger:
    """结构化日志器"""
    
    def log_retrieval_event(self, event_data: dict) -> None:
        """
        日志结构：
        {
            "timestamp": "2026-06-03T10:15:30Z",
            "event_type": "retrieval",
            "query_id": "uuid",
            "query": "用户查询内容",
            "query_intent": {"type": "factoid", "confidence": 0.95},
            "stages": {
                "query_expansion": {"duration_ms": 50, ...},
                "retrieval": {"duration_ms": 80, ...},
                "reranking": {"duration_ms": 120, ...}
            },
            "results": {"total_duration_ms": 250, ...},
            "metadata": {...}
        }
        """
```

**日志级别策略**：
- **DEBUG**：详细的检索过程（开发环境）
- **INFO**：关键事件和统计（生产环境默认）
- **WARN**：性能下降或降级情况
- **ERROR**：错误和异常

#### 3.4.2 性能指标追踪

```python
class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self):
        from prometheus_client import Counter, Histogram, Gauge
        
        # 检索延迟分布
        self.retrieval_latency = Histogram(
            'retrieval_latency_seconds',
            '检索延迟分布',
            buckets=[0.1, 0.2, 0.3, 0.5, 1.0, 2.0]
        )
        
        # 各阶段延迟
        self.stage_latency = Histogram(
            'stage_latency_seconds',
            '各阶段延迟',
            ['stage_name'],
            buckets=[0.05, 0.1, 0.2, 0.5, 1.0]
        )
        
        # 缓存命中率
        self.cache_hits = Counter(
            'cache_hits_total',
            '缓存命中次数',
            ['cache_type']
        )
```

**关键指标**：
- **延迟指标**：P50、P95、P99延迟
- **吞吐指标**：QPS（每秒查询数）
- **质量指标**：结果数量、相似度分布
- **资源指标**：CPU、内存、GPU使用率

#### 3.4.3 查询链路追踪

```python
class TraceCollector:
    """链路追踪收集器"""
    
    def export_trace(self, query_id: str) -> dict:
        """
        导出完整追踪信息
        
        格式：
        {
            "trace_id": "uuid",
            "query": "用户查询",
            "total_duration_ms": 250,
            "spans": [
                {"name": "query_expansion", "start_ms": 0, "duration_ms": 50, ...},
                {"name": "vector_retrieval", "start_ms": 50, "duration_ms": 40, ...},
                ...
            ],
            "critical_path": ["query_expansion", "reranking"],
            "bottleneck": "reranking"
        }
        """
```

**追踪功能**：
- 自动识别瓶颈阶段
- 可视化查询执行路径
- 对比不同配置的性能
- 错误根因分析

#### 3.4.4 实时监控仪表板

```python
class MonitoringDashboard:
    """监控仪表板数据提供器"""
    
    def get_realtime_metrics(self) -> dict:
        """
        返回：
        {
            "current_qps": 15.5,
            "avg_latency_ms": 230,
            "p99_latency_ms": 450,
            "active_requests": 8,
            "cache_hit_rate": 0.75,
            "error_rate": 0.001
        }
        """
```

**仪表板视图**：
- **概览页**：关键指标一目了然
- **查询详情**：单次查询的完整追踪
- **趋势分析**：指标随时间变化趋势
- **告警历史**：历史告警记录

#### 3.4.5 智能告警系统

```python
class AlertManager:
    """告警管理器"""
    
    ALERT_RULES = {
        "high_latency": {
            "condition": "p99_latency > 1.0s",
            "severity": "warning",
            "cooldown": "5m"
        },
        "error_spike": {
            "condition": "error_rate > 0.05",
            "severity": "critical",
            "cooldown": "1m"
        },
        "quality_degradation": {
            "condition": "avg_similarity < 0.6",
            "severity": "warning",
            "cooldown": "15m"
        }
    }
```

**告警策略**：
- **多级告警**：Info、Warning、Critical
- **智能降噪**：告警聚合和去重
- **自动恢复**：状态恢复时自动关闭告警

#### 3.4.6 调试工具集

```python
class DebugToolkit:
    """调试工具集"""
    
    def explain_retrieval(self, query: str) -> dict:
        """
        解释检索结果
        
        详细展示：
        - 查询扩展过程
        - 各路召回结果
        - RRF融合分数
        - 重排序变化
        - 最终排序原因
        """
    
    def compare_configurations(self, query: str, config_a: dict, config_b: dict) -> dict:
        """对比不同配置的效果"""
    
    def replay_query(self, query_id: str) -> dict:
        """重放历史查询"""
```

### 3.5 性能优化与缓存模块

#### 3.5.1 多级缓存架构

```python
class MultiLevelCache:
    """多级缓存系统"""
    
    def __init__(self, config):
        # L1: 内存缓存（进程内，最快）
        self.l1_cache = LRUCache(max_size=1000, ttl=300)
        
        # L2: 分布式缓存（Redis，可选）
        self.l2_cache = RedisCache(host=config.REDIS_HOST, ttl=3600)
        
        # L3: 语义缓存（相似查询复用）
        self.semantic_cache = SemanticCache(similarity_threshold=0.95)
```

**缓存键设计**：
- 精确匹配：query哈希 + 配置哈希
- 语义匹配：query embedding相似度
- 版本控制：配置变更时自动失效

#### 3.5.2 语义缓存系统

```python
class SemanticCache:
    """语义缓存：相似查询复用结果"""
    
    def __init__(self, similarity_threshold: float = 0.95):
        self.threshold = similarity_threshold
    
    def find_similar(self, query_embedding: list[float]) -> Optional[dict]:
        """
        查找相似查询
        
        使用向量索引（如Annoy或FAISS）加速相似度搜索
        """
```

**语义缓存策略**：
- **相似度阈值**：0.95以上视为相同意图
- **缓存淘汰**：LRU + 访问频率混合策略
- **质量保证**：缓存结果附带置信度

#### 3.5.3 批处理优化

```python
class BatchProcessor:
    """批处理器"""
    
    def __init__(self, batch_size: int = 32, max_wait_ms: int = 10):
        self.batch_size = batch_size
        self.max_wait_ms = max_wait_ms
    
    async def process_batch(self) -> None:
        """
        批量处理请求
        
        优化场景：
        - Embedding批量编码
        - 重排序批量推理
        - 数据库批量查询
        """
```

**批处理场景**：
- **Embedding编码**：批量编码多个查询（3-5x加速）
- **重排序**：批量Cross-Encoder推理（2-3x加速）
- **向量检索**：批量查询ChromaDB

#### 3.5.4 并行处理优化

```python
class ParallelExecutor:
    """并行执行器"""
    
    async def parallel_retrieval(self, queries: list[str]) -> list[dict]:
        """
        并行执行多路检索
        
        同时执行：
        - 向量检索
        - BM25检索
        - 知识图谱查询（可选）
        """
```

**并行策略**：
- **多路召回并行**：向量和BM25同时执行
- **流水线重叠**：查询扩展与检索并行
- **异步I/O**：避免阻塞主线程

#### 3.5.5 预计算与预热

```python
class PrecomputationManager:
    """预计算管理器"""
    
    def precompute_embeddings(self, documents: list[str]) -> None:
        """预计算文档Embedding"""
    
    def warmup_cache(self, popular_queries: list[str]) -> None:
        """缓存预热"""
    
    def build_index_cache(self) -> None:
        """索引缓存构建"""
```

**预热策略**：
- **启动预热**：服务启动时加载热门查询
- **后台更新**：定期更新预计算结果
- **智能预测**：基于历史模式预测热门查询

#### 3.5.6 性能基准与调优

```python
class PerformanceBenchmark:
    """性能基准测试"""
    
    def run_latency_benchmark(self, test_queries: list[str]) -> dict:
        """
        输出：
        {
            "p50_ms": 180,
            "p95_ms": 320,
            "p99_ms": 450,
            "max_ms": 520,
            "min_ms": 95
        }
        """
    
    def run_throughput_benchmark(self, concurrency_levels: list[int]) -> dict:
        """吞吐量基准测试"""
    
    def identify_bottlenecks(self) -> list[dict]:
        """识别性能瓶颈"""
```

---

## 4. 数据流设计

### 4.1 完整查询流程

```python
async def retrieve_with_pipeline(query: str) -> dict:
    """
    完整检索流程
    
    流程：
    1. 查询意图分类
    2. 动态路由决策
    3. 查询扩展（可选）
    4. 多路并行召回
    5. 结果融合
    6. 重排序
    7. 缓存更新
    8. 结果返回
    """
    
    # Stage 1: 查询理解
    intent = query_classifier.classify(query)
    route_config = query_router.route(query, intent)
    
    # Stage 2: 查询扩展（可选）
    queries = [query]
    if route_config["use_hyde"]:
        hyde_doc = hyde_generator.generate_hypothetical_document(query)
        queries.append(hyde_doc)
    if route_config["num_queries"] > 1:
        expanded = multi_query_generator.generate_queries(query, route_config["num_queries"])
        queries.extend(expanded)
    
    # Stage 3: 多路并行召回
    vector_results, bm25_results = await asyncio.gather(
        vector_retrieval(queries),
        bm25_retrieval(queries)
    )
    
    # Stage 4: 结果融合
    fused_results = reciprocal_rank_fusion(
        [vector_results, bm25_results],
        weights=route_config["weights"],
        k=config.RRF_K
    )
    
    # Stage 5: 初筛
    filtered_results = filter_by_similarity(fused_results, config.SIMILARITY_THRESHOLD)
    deduplicated = deduplicate_by_source(filtered_results)
    
    # Stage 6: 重排序
    reranked = rerank_manager.rerank(
        query, 
        deduplicated[:route_config["rerank_top_k"]],
        intent
    )
    
    # Stage 7: 业务规则过滤
    final_results = business_rule_filter.apply_filters(reranked, config.BUSINESS_RULES)
    
    # Stage 8: 缓存更新
    cache.set(query, final_results)
    
    return final_results[:config.TOP_K]
```

### 4.2 数据流向图

```
┌─────────────────────────────────────────────────────────────────┐
│                        查询输入                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    查询理解与扩展                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ 意图分类器   │  │ HyDE生成器   │  │ 多查询生成器 │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      多路召回                                    │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ 向量检索         │      │ BM25检索         │                 │
│  │ (ChromaDB)       │      │ (rank_bm25)      │                 │
│  └──────────────────┘      └──────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    结果融合                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ RRF融合 → 相似度过滤 → 去重                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      重排序                                      │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ Cross-Encoder    │      │ 业务规则过滤     │                 │
│  │ (Cohere/BGE)     │      │                  │                 │
│  └──────────────────┘      └──────────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   结果输出                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 缓存更新 → 上下文组装 → 返回结果                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. 配置管理

### 5.1 配置参数

```python
class AdvancedRAGConfig(Config):
    """高级RAG配置"""
    
    # 查询扩展配置
    USE_HYDE: bool = True
    HYDE_ENABLED_INTENTS: list = ["analytical", "exploratory"]
    MULTI_QUERY_ENABLED: bool = True
    MULTI_QUERY_COUNT: int = 3
    
    # 重排序配置
    RERANK_STRATEGY: str = "cohere"  # "cohere", "bge", "hybrid"
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "")
    BGE_RERANKER_PATH: str = "BAAI/bge-reranker-base"
    RERANK_TOP_K: int = 20
    RERANK_TIMEOUT_MS: int = 250
    
    # 缓存配置
    USE_CACHE: bool = True
    CACHE_L1_MAX_SIZE: int = 1000
    CACHE_L1_TTL: int = 300
    USE_REDIS: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    SEMANTIC_CACHE_ENABLED: bool = True
    SEMANTIC_CACHE_THRESHOLD: float = 0.95
    
    # 性能配置
    BATCH_SIZE: int = 32
    MAX_WAIT_MS: int = 10
    PARALLEL_RETRIEVAL: bool = True
    
    # 评估配置
    EVAL_DATASET_PATH: str = "./data/eval_dataset.json"
    ENABLE_LLM_JUDGE: bool = True
    LLM_JUDGE_MODEL: str = "mimo-v2.5"
    
    # 监控配置
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    ENABLE_TRACING: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # 告警配置
    ALERT_LATENCY_THRESHOLD_MS: int = 1000
    ALERT_ERROR_RATE_THRESHOLD: float = 0.05
    ALERT_QUALITY_THRESHOLD: float = 0.6
```

### 5.2 动态配置

```python
class DynamicConfigManager:
    """动态配置管理器"""
    
    def update_config(self, key: str, value: any) -> None:
        """
        动态更新配置
        
        支持热更新，无需重启服务
        """
    
    def get_config_hash(self) -> str:
        """
        获取配置哈希
        
        用于缓存键生成
        """
```

---

## 6. API设计

### 6.1 检索API

```python
# POST /api/retrieve
{
    "query": "Python装饰器怎么用？",
    "options": {
        "use_hyde": true,
        "num_queries": 3,
        "rerank_strategy": "cohere",
        "top_k": 5
    }
}

# Response
{
    "query_id": "uuid",
    "results": [
        {
            "text": "文档内容...",
            "metadata": {"source": "python-docs", "section": "装饰器"},
            "score": 0.85,
            "rerank_score": 0.92
        }
    ],
    "trace": {
        "total_duration_ms": 230,
        "stages": {...}
    }
}
```

### 6.2 评估API

```python
# POST /api/evaluate
{
    "dataset_path": "./data/eval_dataset.json",
    "config": {
        "use_new_pipeline": true,
        "rerank_strategy": "cohere"
    }
}

# Response
{
    "evaluation_id": "uuid",
    "metrics": {
        "recall@5": 0.85,
        "mrr": 0.78,
        "ndcg@5": 0.82,
        "avg_latency_ms": 250
    },
    "report_url": "/api/reports/uuid"
}
```

### 6.3 监控API

```python
# GET /api/metrics/realtime
{
    "current_qps": 15.5,
    "avg_latency_ms": 230,
    "p99_latency_ms": 450,
    "cache_hit_rate": 0.75,
    "error_rate": 0.001
}

# GET /api/traces/{query_id}
{
    "trace_id": "uuid",
    "query": "...",
    "total_duration_ms": 230,
    "spans": [...]
}
```

---

## 7. 错误处理

### 7.1 降级策略

```python
class DegradationManager:
    """降级管理器"""
    
    def should_degrade(self, metrics: dict) -> str:
        """
        判断是否需要降级
        
        降级条件：
        - 延迟超过阈值
        - 错误率过高
        - 外部服务不可用
        
        降级级别：
        - level_0: 正常运行
        - level_1: 禁用HyDE和多查询
        - level_2: 使用本地重排序替代云端
        - level_3: 跳过重排序
        - level_4: 禁用缓存，直接检索
        """
```

### 7.2 错误恢复

```python
class ErrorRecovery:
    """错误恢复机制"""
    
    def retry_with_backoff(self, func, max_retries: int = 3) -> any:
        """
        指数退避重试
        
        用于外部API调用
        """
    
    def fallback_to_default(self, func, default_value) -> any:
        """
        失败时返回默认值
        
        用于非关键功能
        """
```

---

## 8. 测试策略

### 8.1 单元测试

```python
class TestQueryClassifier:
    """查询分类器测试"""
    
    def test_factoid_query_classification(self):
        """测试事实型查询分类"""
    
    def test_complex_query_classification(self):
        """测试复杂查询分类"""
    
    def test_classification_caching(self):
        """测试分类结果缓存"""
```

### 8.2 集成测试

```python
class TestRetrievalPipeline:
    """检索管线集成测试"""
    
    def test_full_pipeline_flow(self):
        """测试完整检索流程"""
    
    def test_fallback_mechanisms(self):
        """测试降级机制"""
    
    def test_cache_integration(self):
        """测试缓存集成"""
```

### 8.3 性能测试

```python
class TestPerformance:
    """性能测试"""
    
    def test_latency_under_load(self):
        """测试负载下的延迟"""
    
    def test_concurrent_requests(self):
        """测试并发请求"""
    
    def test_cache_performance(self):
        """测试缓存性能"""
```

---

## 9. 部署方案

### 9.1 单机部署

```yaml
# docker-compose.yml
services:
  rag-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - COHERE_API_KEY=${COHERE_API_KEY}
      - REDIS_HOST=redis
    depends_on:
      - redis
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

### 9.2 部署检查清单

- [ ] 配置环境变量
- [ ] 加载Embedding模型
- [ ] 构建向量索引
- [ ] 预热缓存
- [ ] 运行健康检查
- [ ] 启动监控服务

---

## 10. 实施计划

### Phase 1：基础架构（1-2周）
- [ ] 重构检索管线
- [ ] 实现查询分类器
- [ ] 添加结构化日志
- [ ] 集成Prometheus指标

### Phase 2：核心功能（2-3周）
- [ ] 实现HyDE和多查询生成
- [ ] 集成重排序模块
- [ ] 实现多级缓存
- [ ] 建立评估数据集

### Phase 3：优化与完善（1-2周）
- [ ] 性能优化和基准测试
- [ ] 完善监控仪表板
- [ ] 实现告警系统
- [ ] 编写调试工具

### Phase 4：测试与部署（1周）
- [ ] 完整测试套件
- [ ] 文档编写
- [ ] 部署脚本
- [ ] 上线灰度发布

**总预计时间**：5-8周

---

## 附录

### A. 参考资料

1. RAG Fusion论文
2. HyDE论文
3. Cohere Reranker文档
4. BGE模型文档
5. Prometheus最佳实践

### B. 术语表

- **RAG**：Retrieval-Augmented Generation
- **HyDE**：Hypothetical Document Embeddings
- **RRF**：Reciprocal Rank Fusion
- **Cross-Encoder**：交叉编码器
- **QPS**：Queries Per Second
- **P99**：99th percentile latency

### C. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-06-03 | v1.0 | 初始设计文档 |

---

**文档状态**：已批准  
**批准人**：[待填写]  
**批准日期**：2026-06-03
