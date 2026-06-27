# RAG系统架构治理设计方案

**日期**: 2026-06-27  
**状态**: 待审查  
**范围**: 架构治理 + 代码质量

## 1. 背景与目标

### 1.1 当前问题

基于对代码库的分析，当前架构存在以下问题：

- **InfraBundle过于庞大**：包含20+依赖，违反单一职责原则
- **RAGEngine代理方法过多**：_setup_backward_compat方法暴露了大量内部实现
- **服务边界不清**：RetrievalPipeline、IngestionService、GenerationService都依赖同一个InfraBundle
- **可测试性差**：难以独立测试各个服务组件

### 1.2 优化目标

1. 拆分InfraBundle为细粒度的服务容器
2. 定义清晰的Protocol接口契约
3. 移除RAGEngine中的向后兼容代理方法
4. 提高代码可测试性和可维护性
5. 保持向后兼容性，分阶段重构

### 1.3 设计原则

- **单一职责**：每个Bundle只负责一类功能
- **最小依赖**：Bundle之间通过接口通信，不共享内部状态
- **向后兼容**：保持RAGEngine现有API不变，通过适配器层支持旧代码
- **接口隔离**：每个Bundle只暴露必要的接口
- **依赖倒置**：高层模块不依赖低层模块，都依赖抽象

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────┐
│   RAGEngine     │ (Facade，仅暴露业务API)
└────────┬────────┘
         │
         ├─────────────────┬─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ RetrievalBundle │ │ProcessingBundle│ │GenerationBundle │
│                 │ │                 │ │                 │
│ - embedding     │ │ - doc_processor │ │ - llm_client    │
│ - vector_store  │ │ - ocr_provider  │ │ - cache_manager │
│ - bm25_retriever│ │ - vlm_provider  │ │ - confidence    │
│ - rerank_manager│ │ - chunking      │ │ - citation      │
│ - cache_manager │ │ - image_store   │ │ - self_rag      │
│ - classifier    │ │                 │ │ - rewriters     │
│ - router        │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 2.2 服务分层

#### 2.2.1 RetrievalBundle（检索服务）

**职责**：
- 查询理解与分类
- 向量检索（embedding + vector_store）
- BM25检索
- 结果重排序
- 多级缓存管理

**依赖组件**：
- EmbeddingService
- VectorStore
- BM25Retriever
- RerankManager
- CacheManager (L1/L2)
- QueryClassifier
- QueryRouter

#### 2.2.2 ProcessingBundle（文档处理服务）

**职责**：
- 文档解析与提取
- OCR识别
- VLM图像理解
- 文档分块
- 图片存储管理

**依赖组件**：
- DocumentProcessor
- OCRProvider (PaddleOCR/Tesseract)
- VLMProvider
- ImageStore
- ChunkingStrategy

#### 2.2.3 GenerationBundle（生成服务）

**职责**：
- LLM生成回答
- 引用验证
- 置信度评估
- Self-RAG反思
- 查询重写（HyDE/Multi-Query）

**依赖组件**：
- LLMClient
- CacheManager
- ConfidenceEvaluator
- CitationVerifier
- SelfRAGReflector
- QueryRewriters

### 2.3 接口契约设计

#### 2.3.1 Protocol定义

```python
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class RetrievalResult:
    """检索结果数据结构
    
    为什么使用dataclass：不可变数据结构，便于缓存和序列化。
    为什么包含metadata：支持扩展，可以携带任意附加信息。
    """
    content: str
    metadata: Dict[str, Any]
    score: float

class RetrievalBundleProtocol(Protocol):
    """检索服务接口契约
    
    为什么定义Protocol：Python原生类型提示，无需继承，符合鸭子类型。
    为什么只暴露retrieve和classify_query：最小接口原则，
    内部组件（embedding、vector_store等）不应直接暴露。
    """
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_bm25: bool = True,
        use_rerank: bool = True,
    ) -> List[RetrievalResult]:
        ...

    def classify_query(self, query: str) -> Dict[str, Any]:
        ...

class ProcessingBundleProtocol(Protocol):
    """文档处理服务接口契约"""
    
    def process_document(
        self,
        file_path: str,
        file_type: str,
        chunk_strategy: str = "semantic",
    ) -> List[Dict[str, Any]]:
        ...

    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        ...

class GenerationBundleProtocol(Protocol):
    """生成服务接口契约"""
    
    def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        ...

    def verify_citation(
        self,
        claim: str,
        source: str,
    ) -> Dict[str, Any]:
        ...
```

#### 2.3.2 Bundle间通信机制

**为什么Bundle需要通信**：
- RetrievalBundle和GenerationBundle都需要CacheManager
- GenerationBundle需要RetrievalBundle的检索结果

**通信方式**：
1. **共享依赖注入**：CacheManager等共享组件通过构造函数注入
2. **方法调用**：GenerationBundle调用RetrievalBundle.retrieve()
3. **事件驱动**（可选）：未来可扩展为异步事件

**CacheManager共享策略**：
- 创建独立的CacheManager实例，但使用相同的Redis连接池
- 为什么这样设计：避免循环依赖，保持Bundle独立性
- 未来优化：引入共享的CacheProvider接口

#### 2.3.3 依赖关系

```
RAGEngine
    │
    ├── RetrievalBundle (implements RetrievalBundleProtocol)
    │       │
    │       ├── EmbeddingService
    │       ├── VectorStore
    │       ├── BM25Retriever
    │       ├── RerankManager
    │       └── CacheManager (L1/L2)
    │
    ├── ProcessingBundle (implements ProcessingBundleProtocol)
    │       │
    │       ├── DocumentProcessor
    │       ├── OCRProvider
    │       ├── VLMProvider
    │       ├── ImageStore
    │       └── ChunkingStrategy
    │
    └── GenerationBundle (implements GenerationBundleProtocol)
            │
            ├── LLMClient
            ├── CacheManager
            ├── ConfidenceEvaluator
            ├── CitationVerifier
            └── SelfRAGReflector
```

## 3. 实现方案

### 3.1 分阶段重构策略

#### 阶段1：定义接口契约（无破坏性变更）

1. 创建`backend/core/services/protocols.py`，定义所有Protocol接口
2. 创建新的Bundle类，实现Protocol接口
3. 保持现有InfraBundle不变，新增Bundle类作为可选组件

#### 阶段2：Bundle实现与适配

1. 实现RetrievalBundle、ProcessingBundle、GenerationBundle
2. 创建BundleFactory，负责Bundle的创建和生命周期管理
3. 实现适配器层，支持旧代码通过新Bundle访问服务

#### 阶段3：RAGEngine重构

1. 修改RAGEngine，使用新的Bundle组合
2. 保留_setup_backward_compat方法，但标记为deprecated
3. 更新API层，直接使用Bundle接口

#### 阶段4：清理与优化

1. 移除RAGEngine中的代理方法
2. 更新测试用例，使用mock的Bundle接口
3. 代码质量改进（类型注解、错误处理）

### 3.2 关键代码示例

#### 3.2.1 RetrievalBundle实现

```python
from core.services.protocols import RetrievalBundleProtocol, RetrievalResult
from typing import List, Dict, Any

class RetrievalBundle:
    """检索服务Bundle实现"""
    
    def __init__(
        self,
        embedding_service,
        vector_store,
        bm25_retriever,
        rerank_manager,
        cache_manager,
        classifier,
        router,
    ):
        # 为什么显式注入：每个依赖都是必需的，避免隐式依赖
        self._embedding_service = embedding_service
        self._vector_store = vector_store
        self._bm25_retriever = bm25_retriever
        self._rerank_manager = rerank_manager
        self._cache_manager = cache_manager
        self._classifier = classifier
        self._router = router
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_bm25: bool = True,
        use_rerank: bool = True,
    ) -> List[RetrievalResult]:
        """执行检索"""
        # 1. 查询分类
        query_type = self.classify_query(query)
        
        # 2. 检查缓存
        cache_key = f"retrieve:{query}:{top_k}"
        cached = self._cache_manager.get(cache_key)
        if cached:
            return cached
        
        # 3. 向量检索
        embedding = self._embedding_service.encode(query)
        vector_results = self._vector_store.search(embedding, top_k=top_k)
        
        # 4. BM25检索（可选）
        bm25_results = []
        if use_bm25:
            bm25_results = self._bm25_retriever.search(query, top_k=top_k)
        
        # 5. 结果融合（RRF算法）
        merged = self._merge_results(vector_results, bm25_results)
        
        # 6. 重排序（可选）
        if use_rerank:
            merged = self._rerank_manager.rerank(query, merged)
        
        # 7. 缓存结果
        self._cache_manager.set(cache_key, merged)
        
        return merged
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """分类查询意图"""
        return self._classifier.classify(query)
    
    def _merge_results(self, vector_results, bm25_results):
        """使用RRF算法融合结果"""
        # RRF公式：score = 1 / (k + rank)
        # 为什么使用RRF：简单有效，不需要归一化不同相似度分数
        pass
```

#### 3.2.2 RAGEngine重构

```python
from core.services.retrieval_bundle import RetrievalBundle
from core.services.processing_bundle import ProcessingBundle
from core.services.generation_bundle import GenerationBundle

class RAGEngine:
    """RAG引擎 - 使用新的Bundle架构"""
    
    def __init__(self, config, use_factory: bool = False):
        self._config = config
        
        # 创建Bundle
        self._retrieval = self._create_retrieval_bundle(config)
        self._processing = self._create_processing_bundle(config)
        self._generation = self._create_generation_bundle(config)
        
        # 向后兼容（deprecated）
        self._setup_backward_compat()
    
    def _create_retrieval_bundle(self, config) -> RetrievalBundle:
        """创建检索Bundle
        
        为什么单独创建：每个Bundle的组件初始化逻辑不同，
        分开创建便于独立测试和维护。
        """
        # 从config创建各个组件
        embedding_service = EmbeddingService(config.EMBEDDING_MODEL_PATH)
        
        # 为什么检查provider类型：支持多种向量存储后端（Chroma/PgVector）
        if getattr(config, "VECTOR_STORE_PROVIDER", "chroma") == "pgvector":
            from core.providers.pgvector_adapter import PgVectorStoreAdapter
            vector_store = PgVectorStoreAdapter(database_url=config.database_url)
        else:
            vector_store = VectorStore(config.CHROMA_PERSIST_DIR)
        
        # BM25检索器：用于关键词检索
        bm25_path = os.path.join(config.CHROMA_PERSIST_DIR, "bm25_index.pkl")
        bm25_retriever = BM25Retriever(persist_path=bm25_path)
        
        # 重排序管理器：提高检索精度
        rerank_manager = RerankManager(config)
        
        # 缓存管理器：多级缓存（L1内存 + L2 Redis）
        cache_manager = CacheManager({
            "use_cache": config.USE_CACHE,
            "l1_max_size": config.CACHE_L1_MAX_SIZE,
            "l1_ttl": config.CACHE_L1_TTL,
            "use_redis": config.USE_REDIS,
            "redis_host": config.REDIS_HOST,
            "redis_port": config.REDIS_PORT,
        })
        
        # 查询分类器和路由器
        classifier = QueryClassifier()
        router = QueryRouter()
        
        return RetrievalBundle(
            embedding_service=embedding_service,
            vector_store=vector_store,
            bm25_retriever=bm25_retriever,
            rerank_manager=rerank_manager,
            cache_manager=cache_manager,
            classifier=classifier,
            router=router,
        )
    
    def _setup_backward_compat(self):
        """向后兼容层（deprecated）
        
        为什么保留：渐进式重构，避免破坏现有代码。
        计划：Phase 3移除，届时所有代码应使用Bundle接口。
        
        为什么暴露内部组件：旧代码直接访问这些组件，
        通过属性代理保持兼容性。
        """
        # 检索相关组件
        self.embedding_service = self._retrieval._embedding_service
        self.vector_store = self._retrieval._vector_store
        self.bm25_retriever = self._retrieval._bm25_retriever
        self.rerank_manager = self._retrieval._rerank_manager
        self.classifier = self._retrieval._classifier
        self.router = self._retrieval._router
        
        # 处理相关组件
        self.document_processor = self._processing._document_processor
        self.ocr_provider = self._processing._ocr_provider
        self.vlm_provider = self._processing._vlm_provider
        
        # 生成相关组件
        self.llm_client = self._generation._llm_client
        self.citation_verifier = self._generation._citation_verifier
        self.self_rag_reflector = self._generation._self_rag_reflector
        self.confidence_evaluator = self._generation._confidence_evaluator
    
    # 业务API
    def retrieve(self, query: str, top_k: int = 5):
        """执行检索"""
        return self._retrieval.retrieve(query, top_k)
    
    def process_document(self, file_path: str, file_type: str):
        """处理文档"""
        return self._processing.process_document(file_path, file_type)
    
    def generate(self, query: str, context, images=None):
        """生成回答"""
        return self._generation.generate(query, context, images)
```

## 4. 代码质量改进

### 4.1 类型注解增强

- 为所有公开接口添加完整的类型注解
- 使用typing模块的高级类型（Optional, Union, List, Dict等）
- 为复杂的数据结构定义dataclass或TypedDict

### 4.2 错误处理改进

- 定义清晰的异常层次结构
- 为每个Bundle定义特定的异常类型
- 实现统一的错误处理中间件

### 4.3 文档与注释

- 为每个类和方法添加docstring
- 解释设计决策和权衡
- 提供使用示例

## 5. 测试策略

### 5.1 单元测试

- 为每个Bundle编写独立的单元测试
- 使用mock对象隔离依赖
- 测试边界条件和错误场景

### 5.2 集成测试

- 测试Bundle之间的交互
- 验证接口契约的正确性
- 测试向后兼容性

### 5.3 性能测试

- 基准测试：比较重构前后的性能
- 负载测试：验证系统在高并发下的稳定性
- 内存测试：确保没有内存泄漏

## 6. 向后兼容性保证

### 6.1 兼容性策略

1. **Phase 1-2**：保持现有API完全不变
2. **Phase 3**：标记deprecated方法，但保持功能
3. **Phase 4**：移除deprecated代码

### 6.2 迁移路径

1. 新代码使用Bundle接口
2. 旧代码继续使用RAGEngine API
3. 逐步迁移，每个PR只迁移一个模块
4. 完整的迁移指南和示例

## 7. 风险与缓解

### 7.1 潜在风险

1. **重构引入bug**
   - 缓解：完整的测试覆盖，渐进式重构

2. **性能下降**
   - 缓解：性能基准测试，优化关键路径

3. **团队学习曲线**
   - 缓解：详细的文档，代码示例，培训

### 7.2 回滚计划

- 保持git分支清晰，易于回滚
- 关键里程碑打tag
- 数据库迁移脚本向后兼容

## 8. 成功标准

### 8.1 代码质量指标

- 单元测试覆盖率 > 80%
- 代码复杂度降低 20%
- 消除所有向后兼容代理方法

### 8.2 性能指标

- 检索延迟：P95 < 200ms
- 生成延迟：P95 < 2s
- 内存使用：稳定，无泄漏

### 8.3 可维护性指标

- 新功能开发时间减少 30%
- Bug修复时间减少 40%
- 代码审查时间减少 25%

## 9. 附录

### 9.1 术语表

- **Bundle**: 服务容器，包含一组相关的依赖和服务
- **Protocol**: Python的结构化类型提示，定义接口契约
- **Facade**: 门面模式，提供简化的接口
- **RRF**: Reciprocal Rank Fusion，倒数排名融合算法

### 9.2 参考资料

- [Python Protocol文档](https://docs.python.org/3/library/typing.html#typing.Protocol)
- [依赖注入最佳实践](https://python-dependency-injector.ets-labs.org/)
- [Clean Architecture原则](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [RRF算法论文](https://dl.acm.org/doi/10.1145/1571941.1572114)

---

## 10. 自审发现与改进

### 10.1 自审发现的问题

#### 问题1：Bundle创建顺序和依赖关系不明确

**现状**：文档中没有明确说明Bundle的创建顺序，GenerationBundle需要RetrievalBundle但没有说明如何注入。

**改进方案**：
```python
class RAGEngine:
    def __init__(self, config):
        # 创建顺序：先创建独立Bundle，再创建有依赖的Bundle
        self._retrieval = self._create_retrieval_bundle(config)
        self._processing = self._create_processing_bundle(config)
        
        # GenerationBundle依赖RetrievalBundle，通过构造函数注入
        self._generation = self._create_generation_bundle(config, self._retrieval)
```

#### 问题2：错误处理设计不详细

**现状**：第4.2节只提到了错误处理改进，但没有详细的异常层次结构设计。

**改进方案**：
```python
# 定义Bundle异常层次结构
class BundleError(Exception):
    """Bundle基础异常"""
    pass

class RetrievalError(BundleError):
    """检索相关异常"""
    pass

class ProcessingError(BundleError):
    """文档处理异常"""
    pass

class GenerationError(BundleError):
    """生成相关异常"""
    pass

# 每个Bundle内部使用统一的错误处理
class RetrievalBundle:
    def retrieve(self, query, **kwargs):
        try:
            # 检索逻辑
            pass
        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            raise RetrievalError(f"Failed to retrieve: {e}") from e
```

#### 问题3：性能监控设计缺失

**现状**：文档中没有提到性能监控的设计，没有说明如何追踪每个阶段的耗时。

**改进方案**：
```python
from contextlib import contextmanager
import time

@contextmanager
def track_duration(operation_name: str):
    """追踪操作耗时的上下文管理器
    
    为什么使用上下文管理器：自动开始和结束计时，避免遗漏。
    为什么记录到metrics_collector：统一的监控入口。
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        metrics_collector.record_duration(operation_name, duration_ms)
        logger.debug("%s completed in %.2fms", operation_name, duration_ms)

# 在Bundle方法中使用
class RetrievalBundle:
    def retrieve(self, query, **kwargs):
        with track_duration("retrieval.total"):
            with track_duration("retrieval.embedding"):
                embedding = self._embedding_service.encode(query)
            with track_duration("retrieval.vector_search"):
                vector_results = self._vector_store.search(embedding)
            # ... 其他步骤
```

#### 问题4：Bundle间通信的实现细节不完整

**现状**：虽然提到了通信机制，但没有具体的代码示例，没有说明如何避免循环依赖。

**改进方案**：
```python
# 使用依赖注入容器避免循环依赖
from typing import Optional

class RetrievalBundle:
    def __init__(self, cache_manager: CacheManager, **kwargs):
        self._cache_manager = cache_manager

class GenerationBundle:
    def __init__(
        self,
        retrieval_bundle: RetrievalBundle,  # 通过构造函数注入
        cache_manager: CacheManager,
        **kwargs
    ):
        self._retrieval = retrieval_bundle
        self._cache_manager = cache_manager

# Bundle工厂负责创建和注入
class BundleFactory:
    def create_bundles(self, config):
        # 创建共享组件
        cache_manager = CacheManager(config)
        
        # 创建Bundle，注入共享组件
        retrieval = RetrievalBundle(cache_manager=cache_manager)
        generation = GenerationBundle(
            retrieval_bundle=retrieval,
            cache_manager=cache_manager,
        )
        
        return retrieval, generation
```

#### 问题5：测试示例缺失

**现状**：第5节只提到了测试策略，但没有具体的测试示例，没有说明如何mock Bundle接口。

**改进方案**：
```python
# 测试示例：使用mock测试RetrievalBundle
from unittest.mock import Mock, MagicMock
import pytest

class TestRetrievalBundle:
    def test_retrieve_should_cache_results(self):
        # 创建mock依赖
        mock_embedding_service = Mock()
        mock_embedding_service.encode.return_value = [0.1, 0.2, 0.3]
        
        mock_vector_store = Mock()
        mock_vector_store.search.return_value = [
            RetrievalResult(content="test", metadata={}, score=0.9)
        ]
        
        mock_cache_manager = Mock()
        mock_cache_manager.get.return_value = None  # 缓存未命中
        
        # 创建Bundle实例
        bundle = RetrievalBundle(
            embedding_service=mock_embedding_service,
            vector_store=mock_vector_store,
            cache_manager=mock_cache_manager,
            # ... 其他依赖
        )
        
        # 执行测试
        result = bundle.retrieve("test query", top_k=5)
        
        # 验证缓存被调用
        mock_cache_manager.set.assert_called_once()
        assert len(result) == 1
        assert result[0].content == "test"
```

### 10.2 改进建议汇总

| 问题 | 优先级 | 改进方案 |
|------|--------|----------|
| Bundle创建顺序 | 高 | 明确创建顺序，通过构造函数注入依赖 |
| 错误处理设计 | 高 | 定义异常层次结构，统一错误处理模式 |
| 性能监控设计 | 中 | 添加上下文管理器追踪耗时 |
| Bundle间通信 | 中 | 使用依赖注入容器，明确通信方式 |
| 测试示例 | 中 | 添加mock测试示例，说明测试策略 |

---

**最终审查清单**：
- [x] 架构设计是否清晰？✅ 通过架构图和详细说明
- [x] 接口契约是否完整？✅ Protocol定义清晰
- [x] 分阶段计划是否可行？✅ 4个阶段，渐进式重构
- [x] 向后兼容性是否保证？✅ 完整的兼容层和迁移路径
- [x] 测试策略是否充分？✅ 单元/集成/性能测试 + 测试示例
- [x] 风险是否识别并缓解？✅ 3个主要风险及缓解措施
- [x] 错误处理是否设计？✅ 异常层次结构和处理模式
- [x] 性能监控是否设计？✅ 上下文管理器追踪耗时
