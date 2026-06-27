# 架构治理实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 拆分InfraBundle为细粒度的服务容器，定义Protocol接口契约，提高代码可测试性和可维护性

**Architecture:** 将现有的单一InfraBundle拆分为3个独立的Bundle（RetrievalBundle、ProcessingBundle、GenerationBundle），每个Bundle实现对应的Protocol接口，通过依赖注入管理Bundle间通信

**Tech Stack:** Python 3.12+, typing.Protocol, dataclasses, pytest, unittest.mock

---

## 文件结构

### 新建文件
- `backend/core/services/protocols.py` - Protocol接口定义
- `backend/core/services/exceptions.py` - 异常层次结构
- `backend/core/services/retrieval_bundle.py` - 检索服务Bundle
- `backend/core/services/processing_bundle.py` - 文档处理Bundle
- `backend/core/services/generation_bundle.py` - 生成服务Bundle
- `backend/core/services/bundle_factory.py` - Bundle工厂
- `tests/unit/test_services/test_protocols.py` - Protocol测试
- `tests/unit/test_services/test_retrieval_bundle.py` - RetrievalBundle测试
- `tests/unit/test_services/test_processing_bundle.py` - ProcessingBundle测试
- `tests/unit/test_services/test_generation_bundle.py` - GenerationBundle测试
- `tests/unit/test_services/test_bundle_factory.py` - BundleFactory测试

### 修改文件
- `backend/core/services/__init__.py` - 更新导出
- `backend/core/rag_engine.py` - 重构为使用Bundle

---

## 任务列表

### Task 1: 定义异常层次结构

**Files:**
- Create: `backend/core/services/exceptions.py`
- Test: `tests/unit/test_services/test_exceptions.py`

- [ ] **Step 1: 编写异常类测试**

```python
# tests/unit/test_services/test_exceptions.py
import pytest
from backend.core.services.exceptions import (
    BundleError,
    RetrievalError,
    ProcessingError,
    GenerationError,
)

class TestBundleExceptions:
    """测试Bundle异常层次结构"""
    
    def test_retrieval_error_is_bundle_error(self):
        """验证RetrievalError继承自BundleError"""
        # 为什么测试继承关系：确保异常层次结构正确
        error = RetrievalError("test error")
        assert isinstance(error, BundleError)
        assert isinstance(error, Exception)
    
    def test_processing_error_is_bundle_error(self):
        """验证ProcessingError继承自BundleError"""
        error = ProcessingError("test error")
        assert isinstance(error, BundleError)
    
    def test_generation_error_is_bundle_error(self):
        """验证GenerationError继承自BundleError"""
        error = GenerationError("test error")
        assert isinstance(error, BundleError)
    
    def test_exception_message_preserved(self):
        """验证异常消息被正确保留"""
        message = "Something went wrong"
        error = RetrievalError(message)
        assert str(error) == message
    
    def test_exception_chaining(self):
        """验证异常链（exception chaining）"""
        # 为什么测试异常链：确保原始异常信息不丢失
        original = ValueError("original error")
        try:
            raise RetrievalError("retrieval failed") from original
        except RetrievalError as e:
            assert e.__cause__ is original
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_services/test_exceptions.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.core.services.exceptions'"

- [ ] **Step 3: 实现异常类**

```python
# backend/core/services/exceptions.py
"""Bundle异常层次结构

为什么定义独立的异常层次：
1. 便于调用方捕获特定类型的异常
2. 提供清晰的错误分类
3. 支持异常链，保留原始错误信息
"""


class BundleError(Exception):
    """Bundle基础异常
    
    为什么继承Exception：所有Bundle异常的基类，
    调用方可以捕获BundleError来处理所有Bundle相关错误。
    """
    pass


class RetrievalError(BundleError):
    """检索相关异常
    
    何时抛出：检索过程中的任何错误，包括：
    - Embedding编码失败
    - 向量检索失败
    - BM25检索失败
    - 结果融合失败
    """
    pass


class ProcessingError(BundleError):
    """文档处理异常
    
    何时抛出：文档处理过程中的任何错误，包括：
    - 文件读取失败
    - OCR识别失败
    - VLM提取失败
    - 分块失败
    """
    pass


class GenerationError(BundleError):
    """生成相关异常
    
    何时抛出：生成过程中的任何错误，包括：
    - LLM调用失败
    - 引用验证失败
    - 置信度评估失败
    """
    pass
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_services/test_exceptions.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 提交代码**

```bash
git add backend/core/services/exceptions.py tests/unit/test_services/test_exceptions.py
git commit -m "feat: add Bundle exception hierarchy"
```

---

### Task 2: 定义Protocol接口

**Files:**
- Create: `backend/core/services/protocols.py`
- Test: `tests/unit/test_services/test_protocols.py`

- [ ] **Step 1: 编写Protocol测试**

```python
# tests/unit/test_services/test_protocols.py
import pytest
from typing import get_type_hints
from backend.core.services.protocols import (
    RetrievalResult,
    RetrievalBundleProtocol,
    ProcessingBundleProtocol,
    GenerationBundleProtocol,
)

class TestRetrievalResult:
    """测试RetrievalResult数据结构"""
    
    def test_retrieval_result_fields(self):
        """验证RetrievalResult包含必要字段"""
        # 为什么测试字段：确保数据结构完整
        result = RetrievalResult(
            content="test content",
            metadata={"source": "test"},
            score=0.95,
        )
        assert result.content == "test content"
        assert result.metadata == {"source": "test"}
        assert result.score == 0.95
    
    def test_retrieval_result_is_dataclass(self):
        """验证RetrievalResult是dataclass"""
        # 为什么测试dataclass特性：确保不可变性和序列化支持
        import dataclasses
        assert dataclasses.is_dataclass(RetrievalResult)

class TestRetrievalBundleProtocol:
    """测试RetrievalBundleProtocol接口定义"""
    
    def test_protocol_has_retrieve_method(self):
        """验证Protocol定义了retrieve方法"""
        # 为什么测试方法存在：确保接口契约完整
        assert hasattr(RetrievalBundleProtocol, 'retrieve')
    
    def test_protocol_has_classify_query_method(self):
        """验证Protocol定义了classify_query方法"""
        assert hasattr(RetrievalBundleProtocol, 'classify_query')
    
    def test_retrieve_method_signature(self):
        """验证retrieve方法签名"""
        hints = get_type_hints(RetrievalBundleProtocol.retrieve)
        assert 'query' in hints
        assert 'top_k' in hints
        assert hints['return'] is list

class TestProcessingBundleProtocol:
    """测试ProcessingBundleProtocol接口定义"""
    
    def test_protocol_has_process_document_method(self):
        """验证Protocol定义了process_document方法"""
        assert hasattr(ProcessingBundleProtocol, 'process_document')
    
    def test_protocol_has_extract_images_method(self):
        """验证Protocol定义了extract_images方法"""
        assert hasattr(ProcessingBundleProtocol, 'extract_images')

class TestGenerationBundleProtocol:
    """测试GenerationBundleProtocol接口定义"""
    
    def test_protocol_has_generate_method(self):
        """验证Protocol定义了generate方法"""
        assert hasattr(GenerationBundleProtocol, 'generate')
    
    def test_protocol_has_verify_citation_method(self):
        """验证Protocol定义了verify_citation方法"""
        assert hasattr(GenerationBundleProtocol, 'verify_citation')
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_services/test_protocols.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.core.services.protocols'"

- [ ] **Step 3: 实现Protocol接口**

```python
# backend/core/services/protocols.py
"""Protocol接口定义

为什么使用Protocol：
1. Python原生类型提示，无需继承
2. 符合鸭子类型哲学
3. 类型检查时验证接口兼容性
4. 运行时无额外开销

为什么每个Bundle只暴露最小接口：
1. 接口隔离原则
2. 内部组件不应直接暴露
3. 便于测试和mock
"""

from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class RetrievalResult:
    """检索结果数据结构
    
    为什么使用dataclass：
    1. 不可变数据结构，便于缓存和序列化
    2. 自动生成__eq__和__hash__
    3. 类型提示支持
    
    为什么包含metadata：
    1. 支持扩展，可以携带任意附加信息
    2. 便于调试和日志记录
    """
    content: str
    metadata: Dict[str, Any]
    score: float


class RetrievalBundleProtocol(Protocol):
    """检索服务接口契约
    
    为什么只暴露retrieve和classify_query：
    1. 最小接口原则
    2. 内部组件（embedding、vector_store等）不应直接暴露
    3. 便于测试和mock
    """
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_bm25: bool = True,
        use_rerank: bool = True,
    ) -> List[RetrievalResult]:
        """执行检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            use_bm25: 是否启用BM25检索
            use_rerank: 是否启用重排序
            
        Returns:
            检索结果列表，按相关性排序
        """
        ...

    def classify_query(self, query: str) -> Dict[str, Any]:
        """分类查询意图
        
        Args:
            query: 查询文本
            
        Returns:
            分类结果字典，包含query_type、intent等字段
        """
        ...


class ProcessingBundleProtocol(Protocol):
    """文档处理服务接口契约"""
    
    def process_document(
        self,
        file_path: str,
        file_type: str,
        chunk_strategy: str = "semantic",
    ) -> List[Dict[str, Any]]:
        """处理文档
        
        Args:
            file_path: 文件路径
            file_type: 文件类型（pdf、docx、md等）
            chunk_strategy: 分块策略（semantic、fixed_size、recursive）
            
        Returns:
            文档块列表，每个块包含content和metadata
        """
        ...

    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """提取图片
        
        Args:
            file_path: 文件路径
            
        Returns:
            图片信息列表，每个图片包含path、page、bbox等
        """
        ...


class GenerationBundleProtocol(Protocol):
    """生成服务接口契约"""
    
    def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """生成回答
        
        Args:
            query: 用户查询
            context: 检索到的上下文
            images: 可选的图片列表
            
        Returns:
            生成结果字典，包含answer、citations、confidence等
        """
        ...

    def verify_citation(
        self,
        claim: str,
        source: str,
    ) -> Dict[str, Any]:
        """验证引用
        
        Args:
            claim: 声明内容
            source: 引用来源
            
        Returns:
            验证结果，包含verified、confidence、reason等
        """
        ...
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_services/test_protocols.py -v`
Expected: PASS (11 tests)

- [ ] **Step 5: 提交代码**

```bash
git add backend/core/services/protocols.py tests/unit/test_services/test_protocols.py
git commit -m "feat: define Protocol interfaces for Bundles"
```

---

### Task 3: 实现RetrievalBundle

**Files:**
- Create: `backend/core/services/retrieval_bundle.py`
- Test: `tests/unit/test_services/test_retrieval_bundle.py`

- [ ] **Step 1: 编写RetrievalBundle测试**

```python
# tests/unit/test_services/test_retrieval_bundle.py
import pytest
from unittest.mock import Mock, MagicMock
from backend.core.services.retrieval_bundle import RetrievalBundle
from backend.core.services.protocols import RetrievalResult
from backend.core.services.exceptions import RetrievalError

class TestRetrievalBundle:
    """测试RetrievalBundle实现"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """创建mock依赖"""
        # 为什么使用fixture：复用mock对象，减少重复代码
        return {
            'embedding_service': Mock(),
            'vector_store': Mock(),
            'bm25_retriever': Mock(),
            'rerank_manager': Mock(),
            'cache_manager': Mock(),
            'classifier': Mock(),
            'router': Mock(),
        }
    
    @pytest.fixture
    def retrieval_bundle(self, mock_dependencies):
        """创建RetrievalBundle实例"""
        return RetrievalBundle(**mock_dependencies)
    
    def test_retrieve_should_return_results(self, retrieval_bundle, mock_dependencies):
        """验证retrieve返回检索结果"""
        # 准备mock数据
        mock_dependencies['cache_manager'].get.return_value = None  # 缓存未命中
        mock_dependencies['embedding_service'].encode.return_value = [0.1, 0.2, 0.3]
        mock_dependencies['vector_store'].search.return_value = [
            RetrievalResult(content="test", metadata={}, score=0.9)
        ]
        mock_dependencies['bm25_retriever'].search.return_value = []
        mock_dependencies['rerank_manager'].rerank.return_value = [
            RetrievalResult(content="test", metadata={}, score=0.9)
        ]
        
        # 执行测试
        result = retrieval_bundle.retrieve("test query", top_k=5)
        
        # 验证结果
        assert len(result) == 1
        assert result[0].content == "test"
        assert result[0].score == 0.9
    
    def test_retrieve_should_use_cache(self, retrieval_bundle, mock_dependencies):
        """验证retrieve使用缓存"""
        # 准备缓存数据
        cached_results = [
            RetrievalResult(content="cached", metadata={}, score=0.95)
        ]
        mock_dependencies['cache_manager'].get.return_value = cached_results
        
        # 执行测试
        result = retrieval_bundle.retrieve("test query")
        
        # 验证缓存被使用
        assert result == cached_results
        mock_dependencies['embedding_service'].encode.assert_not_called()
    
    def test_retrieve_should_handle_errors(self, retrieval_bundle, mock_dependencies):
        """验证retrieve处理错误"""
        # 准备mock抛出异常
        mock_dependencies['cache_manager'].get.return_value = None
        mock_dependencies['embedding_service'].encode.side_effect = ValueError("encoding failed")
        
        # 执行测试并验证异常
        with pytest.raises(RetrievalError) as exc_info:
            retrieval_bundle.retrieve("test query")
        
        assert "encoding failed" in str(exc_info.value)
    
    def test_classify_query_should_delegate(self, retrieval_bundle, mock_dependencies):
        """验证classify_query委托给classifier"""
        # 准备mock数据
        mock_dependencies['classifier'].classify.return_value = {
            'query_type': 'factoid',
            'intent': 'search',
        }
        
        # 执行测试
        result = retrieval_bundle.classify_query("What is Python?")
        
        # 验证结果
        assert result['query_type'] == 'factoid'
        mock_dependencies['classifier'].classify.assert_called_once_with("What is Python?")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_services/test_retrieval_bundle.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.core.services.retrieval_bundle'"

- [ ] **Step 3: 实现RetrievalBundle**

```python
# backend/core/services/retrieval_bundle.py
"""检索服务Bundle实现

为什么独立实现：
1. 单一职责原则
2. 便于独立测试
3. 清晰的依赖边界
"""

import logging
from typing import List, Dict, Any
from core.services.protocols import RetrievalBundleProtocol, RetrievalResult
from core.services.exceptions import RetrievalError
from core.embedding_service import EmbeddingService
from core.vector_store import VectorStore
from core.bm25_retriever import BM25Retriever
from core.reranking.manager import RerankManager
from core.performance.cache.manager import CacheManager
from core.query_understanding.classifier import QueryClassifier
from core.query_understanding.router import QueryRouter

logger = logging.getLogger(__name__)


class RetrievalBundle:
    """检索服务Bundle实现
    
    为什么显式注入依赖：
    1. 每个依赖都是必需的，避免隐式依赖
    2. 便于测试时注入mock对象
    3. 依赖关系清晰可见
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
        bm25_retriever: BM25Retriever,
        rerank_manager: RerankManager,
        cache_manager: CacheManager,
        classifier: QueryClassifier,
        router: QueryRouter,
    ):
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
        """执行检索
        
        为什么按这个顺序执行：
        1. 查询分类：确定查询类型，指导后续策略
        2. 缓存检查：避免重复计算
        3. 向量检索：语义相似度
        4. BM25检索：关键词匹配（可选）
        5. 结果融合：结合两种检索结果
        6. 重排序：提高精度（可选）
        7. 缓存结果：供后续查询使用
        """
        try:
            # 1. 查询分类
            query_type = self.classify_query(query)
            logger.debug("Query type: %s", query_type)
            
            # 2. 检查缓存
            cache_key = f"retrieve:{query}:{top_k}"
            cached = self._cache_manager.get(cache_key)
            if cached:
                logger.debug("Cache hit for query: %s", query[:50])
                return cached
            
            # 3. 向量检索
            embedding = self._embedding_service.encode(query)
            vector_results = self._vector_store.search(embedding, top_k=top_k)
            logger.debug("Vector search returned %d results", len(vector_results))
            
            # 4. BM25检索（可选）
            bm25_results = []
            if use_bm25:
                bm25_results = self._bm25_retriever.search(query, top_k=top_k)
                logger.debug("BM25 search returned %d results", len(bm25_results))
            
            # 5. 结果融合（RRF算法）
            merged = self._merge_results(vector_results, bm25_results, k=60)
            
            # 6. 重排序（可选）
            if use_rerank:
                merged = self._rerank_manager.rerank(query, merged)
                logger.debug("Reranking completed")
            
            # 7. 缓存结果
            self._cache_manager.set(cache_key, merged)
            
            return merged
            
        except Exception as e:
            logger.error("Retrieval failed: %s", e)
            raise RetrievalError(f"Failed to retrieve: {e}") from e
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """分类查询意图"""
        return self._classifier.classify(query)
    
    def _merge_results(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        k: int = 60,
    ) -> List[RetrievalResult]:
        """使用RRF算法融合结果
        
        RRF公式：score = 1 / (k + rank)
        
        为什么使用RRF：
        1. 简单有效
        2. 不需要归一化不同相似度分数
        3. 学术论文验证有效
        """
        # 为每个结果分配rank
        scores = {}
        
        for rank, result in enumerate(vector_results):
            key = result.content
            if key not in scores:
                scores[key] = {'result': result, 'score': 0}
            scores[key]['score'] += 1 / (k + rank + 1)
        
        for rank, result in enumerate(bm25_results):
            key = result.content
            if key not in scores:
                scores[key] = {'result': result, 'score': 0}
            scores[key]['score'] += 1 / (k + rank + 1)
        
        # 按融合分数排序
        merged = sorted(
            scores.values(),
            key=lambda x: x['score'],
            reverse=True,
        )
        
        return [
            RetrievalResult(
                content=item['result'].content,
                metadata=item['result'].metadata,
                score=item['score'],
            )
            for item in merged
        ]
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_services/test_retrieval_bundle.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 提交代码**

```bash
git add backend/core/services/retrieval_bundle.py tests/unit/test_services/test_retrieval_bundle.py
git commit -m "feat: implement RetrievalBundle with RRF fusion"
```

---

### Task 4: 实现ProcessingBundle

**Files:**
- Create: `backend/core/services/processing_bundle.py`
- Test: `tests/unit/test_services/test_processing_bundle.py`

- [ ] **Step 1: 编写ProcessingBundle测试**

```python
# tests/unit/test_services/test_processing_bundle.py
import pytest
from unittest.mock import Mock, MagicMock
from backend.core.services.processing_bundle import ProcessingBundle
from backend.core.services.exceptions import ProcessingError

class TestProcessingBundle:
    """测试ProcessingBundle实现"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """创建mock依赖"""
        return {
            'document_processor': Mock(),
            'ocr_provider': Mock(),
            'vlm_provider': Mock(),
            'image_store': Mock(),
            'chunking_strategy': Mock(),
        }
    
    @pytest.fixture
    def processing_bundle(self, mock_dependencies):
        """创建ProcessingBundle实例"""
        return ProcessingBundle(**mock_dependencies)
    
    def test_process_document_should_return_chunks(self, processing_bundle, mock_dependencies):
        """验证process_document返回文档块"""
        # 准备mock数据
        mock_dependencies['document_processor'].process.return_value = [
            {'content': 'chunk1', 'metadata': {'page': 1}},
            {'content': 'chunk2', 'metadata': {'page': 2}},
        ]
        
        # 执行测试
        result = processing_bundle.process_document(
            file_path="test.pdf",
            file_type="pdf",
            chunk_strategy="semantic",
        )
        
        # 验证结果
        assert len(result) == 2
        assert result[0]['content'] == 'chunk1'
    
    def test_process_document_should_handle_errors(self, processing_bundle, mock_dependencies):
        """验证process_document处理错误"""
        # 准备mock抛出异常
        mock_dependencies['document_processor'].process.side_effect = ValueError("processing failed")
        
        # 执行测试并验证异常
        with pytest.raises(ProcessingError) as exc_info:
            processing_bundle.process_document("test.pdf", "pdf")
        
        assert "processing failed" in str(exc_info.value)
    
    def test_extract_images_should_delegate(self, processing_bundle, mock_dependencies):
        """验证extract_images委托给document_processor"""
        # 凄备mock数据
        mock_dependencies['document_processor'].extract_images.return_value = [
            {'path': '/tmp/img1.png', 'page': 1},
            {'path': '/tmp/img2.png', 'page': 2},
        ]
        
        # 执行测试
        result = processing_bundle.extract_images("test.pdf")
        
        # 验证结果
        assert len(result) == 2
        mock_dependencies['document_processor'].extract_images.assert_called_once_with("test.pdf")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_services/test_processing_bundle.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.core.services.processing_bundle'"

- [ ] **Step 3: 实现ProcessingBundle**

```python
# backend/core/services/processing_bundle.py
"""文档处理Bundle实现

为什么独立实现：
1. 单一职责原则
2. 文档处理逻辑独立于检索和生成
3. 便于独立测试和维护
"""

import logging
from typing import List, Dict, Any
from core.services.protocols import ProcessingBundleProtocol
from core.services.exceptions import ProcessingError
from core.document_processor import DocumentProcessor
from core.ocr.paddle_provider import PaddleOCRProvider
from core.ocr.tesseract_provider import TesseractOCRProvider
from core.ocr.vlm_provider import VLMProvider
from core.image_store import ImageStore
from core.chunking.base import ChunkingStrategy

logger = logging.getLogger(__name__)


class ProcessingBundle:
    """文档处理Bundle实现
    
    为什么显式注入依赖：
    1. 依赖关系清晰
    2. 便于测试时注入mock
    3. 支持不同的OCR/VLM实现
    """
    
    def __init__(
        self,
        document_processor: DocumentProcessor,
        ocr_provider: PaddleOCRProvider | TesseractOCRProvider | None,
        vlm_provider: VLMProvider | None,
        image_store: ImageStore | None,
        chunking_strategy: ChunkingStrategy,
    ):
        self._document_processor = document_processor
        self._ocr_provider = ocr_provider
        self._vlm_provider = vlm_provider
        self._image_store = image_store
        self._chunking_strategy = chunking_strategy
    
    def process_document(
        self,
        file_path: str,
        file_type: str,
        chunk_strategy: str = "semantic",
    ) -> List[Dict[str, Any]]:
        """处理文档
        
        为什么委托给document_processor：
        1. 复用现有的文档处理逻辑
        2. 避免代码重复
        3. 保持向后兼容
        """
        try:
            logger.info("Processing document: %s (type=%s)", file_path, file_type)
            
            # 委托给document_processor
            chunks = self._document_processor.process(
                file_path,
                file_type,
                chunk_strategy=chunk_strategy,
            )
            
            logger.info("Document processed: %d chunks", len(chunks))
            return chunks
            
        except Exception as e:
            logger.error("Document processing failed: %s", e)
            raise ProcessingError(f"Failed to process document: {e}") from e
    
    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """提取图片
        
        为什么委托给document_processor：
        1. 复用现有的图片提取逻辑
        2. 支持多种文件格式
        3. 保持向后兼容
        """
        try:
            logger.info("Extracting images from: %s", file_path)
            
            # 委托给document_processor
            images = self._document_processor.extract_images(file_path)
            
            # 如果有image_store，保存图片
            if self._image_store and images:
                for img in images:
                    self._image_store.save(img['path'], img)
            
            logger.info("Extracted %d images", len(images))
            return images
            
        except Exception as e:
            logger.error("Image extraction failed: %s", e)
            raise ProcessingError(f"Failed to extract images: {e}") from e
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_services/test_processing_bundle.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交代码**

```bash
git add backend/core/services/processing_bundle.py tests/unit/test_services/test_processing_bundle.py
git commit -m "feat: implement ProcessingBundle"
```

---

### Task 5: 实现GenerationBundle

**Files:**
- Create: `backend/core/services/generation_bundle.py`
- Test: `tests/unit/test_services/test_generation_bundle.py`

- [ ] **Step 1: 编写GenerationBundle测试**

```python
# tests/unit/test_services/test_generation_bundle.py
import pytest
from unittest.mock import Mock, MagicMock
from backend.core.services.generation_bundle import GenerationBundle
from backend.core.services.protocols import RetrievalResult
from backend.core.services.exceptions import GenerationError

class TestGenerationBundle:
    """测试GenerationBundle实现"""
    
    @pytest.fixture
    def mock_dependencies(self):
        """创建mock依赖"""
        return {
            'llm_client': Mock(),
            'cache_manager': Mock(),
            'confidence_evaluator': Mock(),
            'citation_verifier': Mock(),
            'self_rag_reflector': Mock(),
            'retrieval_bundle': Mock(),
        }
    
    @pytest.fixture
    def generation_bundle(self, mock_dependencies):
        """创建GenerationBundle实例"""
        return GenerationBundle(**mock_dependencies)
    
    def test_generate_should_return_answer(self, generation_bundle, mock_dependencies):
        """验证generate返回生成结果"""
        # 准备mock数据
        mock_dependencies['llm_client'].generate.return_value = {
            'answer': 'Python is a programming language',
            'citations': ['source1'],
        }
        mock_dependencies['confidence_evaluator'].evaluate.return_value = {
            'confidence': 0.85,
        }
        
        # 准备输入
        query = "What is Python?"
        context = [
            RetrievalResult(content="Python is a programming language", metadata={}, score=0.9),
        ]
        
        # 执行测试
        result = generation_bundle.generate(query, context)
        
        # 验证结果
        assert 'answer' in result
        assert result['answer'] == 'Python is a programming language'
        assert 'confidence' in result
    
    def test_generate_should_handle_errors(self, generation_bundle, mock_dependencies):
        """验证generate处理错误"""
        # 准备mock抛出异常
        mock_dependencies['llm_client'].generate.side_effect = ValueError("LLM failed")
        
        # 执行测试并验证异常
        with pytest.raises(GenerationError) as exc_info:
            generation_bundle.generate("test", [])
        
        assert "LLM failed" in str(exc_info.value)
    
    def test_verify_citation_should_delegate(self, generation_bundle, mock_dependencies):
        """验证verify_citation委托给citation_verifier"""
        # 准备mock数据
        mock_dependencies['citation_verifier'].verify.return_value = {
            'verified': True,
            'confidence': 0.9,
        }
        
        # 执行测试
        result = generation_bundle.verify_citation("claim", "source")
        
        # 验证结果
        assert result['verified'] is True
        mock_dependencies['citation_verifier'].verify.assert_called_once_with("claim", "source")
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_services/test_generation_bundle.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.core.services.generation_bundle'"

- [ ] **Step 3: 实现GenerationBundle**

```python
# backend/core/services/generation_bundle.py
"""生成服务Bundle实现

为什么独立实现：
1. 单一职责原则
2. 生成逻辑独立于检索和处理
3. 便于独立测试和维护
"""

import logging
from typing import List, Dict, Any, Optional
from core.services.protocols import GenerationBundleProtocol, RetrievalResult
from core.services.exceptions import GenerationError
from core.llm_client import LLMClient
from core.performance.cache.manager import CacheManager
from core.retrieval.confidence_evaluator import ConfidenceEvaluator
from core.verification.citation_verifier import CitationVerifier
from core.verification.self_rag_reflector import SelfRAGReflector
from core.services.retrieval_bundle import RetrievalBundle

logger = logging.getLogger(__name__)


class GenerationBundle:
    """生成服务Bundle实现
    
    为什么需要retrieval_bundle：
    1. GenerationBundle可能需要执行检索（如Self-RAG）
    2. 通过构造函数注入，避免循环依赖
    3. 便于测试时注入mock
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        cache_manager: CacheManager,
        confidence_evaluator: ConfidenceEvaluator,
        citation_verifier: CitationVerifier,
        self_rag_reflector: SelfRAGReflector,
        retrieval_bundle: RetrievalBundle,
    ):
        self._llm_client = llm_client
        self._cache_manager = cache_manager
        self._confidence_evaluator = confidence_evaluator
        self._citation_verifier = citation_verifier
        self._self_rag_reflector = self_rag_reflector
        self._retrieval = retrieval_bundle
    
    def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """生成回答
        
        为什么按这个顺序执行：
        1. LLM生成：基于query和context生成回答
        2. 置信度评估：评估生成结果的可信度
        3. 引用验证：验证生成结果中的引用
        4. Self-RAG反思：如果置信度低，重新生成
        """
        try:
            logger.info("Generating answer for query: %s", query[:50])
            
            # 1. 检查缓存
            cache_key = f"generate:{query}:{len(context)}"
            cached = self._cache_manager.get(cache_key)
            if cached:
                logger.debug("Cache hit for generation")
                return cached
            
            # 2. LLM生成
            llm_result = self._llm_client.generate(
                query=query,
                context=context,
                images=images,
            )
            
            # 3. 置信度评估
            confidence_result = self._confidence_evaluator.evaluate(
                query=query,
                answer=llm_result['answer'],
                context=context,
            )
            
            # 4. 引用验证
            citations = []
            if 'citations' in llm_result:
                for citation in llm_result['citations']:
                    verify_result = self._citation_verifier.verify(
                        claim=llm_result['answer'],
                        source=citation,
                    )
                    if verify_result['verified']:
                        citations.append(citation)
            
            # 5. 组装结果
            result = {
                'answer': llm_result['answer'],
                'citations': citations,
                'confidence': confidence_result['confidence'],
                'metadata': {
                    'model': self._llm_client.model,
                    'context_count': len(context),
                },
            }
            
            # 6. 缓存结果
            self._cache_manager.set(cache_key, result)
            
            logger.info("Generation completed with confidence: %.2f", result['confidence'])
            return result
            
        except Exception as e:
            logger.error("Generation failed: %s", e)
            raise GenerationError(f"Failed to generate: {e}") from e
    
    def verify_citation(
        self,
        claim: str,
        source: str,
    ) -> Dict[str, Any]:
        """验证引用"""
        try:
            return self._citation_verifier.verify(claim=claim, source=source)
        except Exception as e:
            logger.error("Citation verification failed: %s", e)
            raise GenerationError(f"Failed to verify citation: {e}") from e
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_services/test_generation_bundle.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交代码**

```bash
git add backend/core/services/generation_bundle.py tests/unit/test_services/test_generation_bundle.py
git commit -m "feat: implement GenerationBundle"
```

---

### Task 6: 实现BundleFactory

**Files:**
- Create: `backend/core/services/bundle_factory.py`
- Test: `tests/unit/test_services/test_bundle_factory.py`

- [ ] **Step 1: 编写BundleFactory测试**

```python
# tests/unit/test_services/test_bundle_factory.py
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.core.services.bundle_factory import BundleFactory
from backend.core.services.retrieval_bundle import RetrievalBundle
from backend.core.services.processing_bundle import ProcessingBundle
from backend.core.services.generation_bundle import GenerationBundle

class TestBundleFactory:
    """测试BundleFactory实现"""
    
    @pytest.fixture
    def mock_config(self):
        """创建mock配置"""
        config = Mock()
        config.EMBEDDING_MODEL_PATH = "/tmp/embedding"
        config.VECTOR_STORE_PROVIDER = "chroma"
        config.CHROMA_PERSIST_DIR = "/tmp/chroma"
        config.BM25_PERSIST_DIR = "/tmp/bm25"
        config.USE_CACHE = True
        config.CACHE_L1_MAX_SIZE = 1000
        config.CACHE_L1_TTL = 300
        config.USE_REDIS = False
        config.REDIS_HOST = "localhost"
        config.REDIS_PORT = 6379
        config.OCR_PROVIDER = "none"
        config.USE_VLM = False
        config.USE_VLM_EXTRACTOR = False
        config.IMAGE_STORE_ENABLED = False
        return config
    
    @patch('backend.core.services.bundle_factory.EmbeddingService')
    @patch('backend.core.services.bundle_factory.VectorStore')
    def test_create_retrieval_bundle(self, mock_vector_store, mock_embedding, mock_config):
        """验证create_retrieval_bundle创建RetrievalBundle"""
        # 执行测试
        factory = BundleFactory()
        bundle = factory.create_retrieval_bundle(mock_config)
        
        # 验证结果
        assert isinstance(bundle, RetrievalBundle)
    
    @patch('backend.core.services.bundle_factory.DocumentProcessor')
    def test_create_processing_bundle(self, mock_doc_processor, mock_config):
        """验证create_processing_bundle创建ProcessingBundle"""
        # 执行测试
        factory = BundleFactory()
        bundle = factory.create_processing_bundle(mock_config)
        
        # 验证结果
        assert isinstance(bundle, ProcessingBundle)
    
    @patch('backend.core.services.bundle_factory.LLMClient')
    def test_create_generation_bundle(self, mock_llm_client, mock_config):
        """验证create_generation_bundle创建GenerationBundle"""
        # 执行测试
        factory = BundleFactory()
        bundle = factory.create_generation_bundle(mock_config)
        
        # 验证结果
        assert isinstance(bundle, GenerationBundle)
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_services/test_bundle_factory.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'backend.core.services.bundle_factory'"

- [ ] **Step 3: 实现BundleFactory**

```python
# backend/core/services/bundle_factory.py
"""Bundle工厂实现

为什么需要工厂：
1. 封装Bundle的创建逻辑
2. 统一管理依赖注入
3. 便于测试和配置
"""

import os
import logging
from typing import Dict, Any
from core.services.retrieval_bundle import RetrievalBundle
from core.services.processing_bundle import ProcessingBundle
from core.services.generation_bundle import GenerationBundle
from core.embedding_service import EmbeddingService
from core.vector_store import VectorStore
from core.bm25_retriever import BM25Retriever
from core.reranking.manager import RerankManager
from core.performance.cache.manager import CacheManager
from core.query_understanding.classifier import QueryClassifier
from core.query_understanding.router import QueryRouter
from core.document_processor import DocumentProcessor
from core.chunking import SemanticChunking
from core.llm_client import LLMClient
from core.retrieval.confidence_evaluator import ConfidenceEvaluator
from core.verification.citation_verifier import CitationVerifier
from core.verification.self_rag_reflector import SelfRAGReflector

logger = logging.getLogger(__name__)


class BundleFactory:
    """Bundle工厂
    
    为什么单独创建每个Bundle：
    1. 每个Bundle的组件初始化逻辑不同
    2. 分开创建便于独立测试和维护
    3. 支持不同的配置选项
    """
    
    def create_retrieval_bundle(self, config) -> RetrievalBundle:
        """创建检索Bundle"""
        logger.info("Creating RetrievalBundle")
        
        # 创建各个组件
        embedding_service = EmbeddingService(config.EMBEDDING_MODEL_PATH)
        
        # 为什么检查provider类型：支持多种向量存储后端
        if getattr(config, "VECTOR_STORE_PROVIDER", "chroma") == "pgvector":
            from core.providers.pgvector_adapter import PgVectorStoreAdapter
            vector_store = PgVectorStoreAdapter(database_url=config.database_url)
        else:
            vector_store = VectorStore(config.CHROMA_PERSIST_DIR)
        
        # BM25检索器
        bm25_base_dir = getattr(config, "BM25_PERSIST_DIR", "") or config.CHROMA_PERSIST_DIR
        bm25_path = os.path.join(bm25_base_dir, "bm25_index.pkl")
        bm25_retriever = BM25Retriever(persist_path=bm25_path)
        
        # 重排序管理器
        rerank_manager = RerankManager(config)
        
        # 缓存管理器
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
    
    def create_processing_bundle(self, config) -> ProcessingBundle:
        """创建文档处理Bundle"""
        logger.info("Creating ProcessingBundle")
        
        # 初始化OCR provider
        ocr_provider = self._init_ocr_provider(config)
        
        # 初始化VLM provider
        vlm_provider = self._init_vlm_provider(config)
        
        # 创建文件读取器注册表
        file_reader_registry = self._build_file_reader_registry(ocr_provider, vlm_provider)
        
        # 创建分块策略
        chunking_strategy = SemanticChunking(
            percentile=config.SEMANTIC_CHUNK_PERCENTILE,
            min_sentences=config.SEMANTIC_CHUNK_MIN_SENTENCES,
            max_sentences=config.SEMANTIC_CHUNK_MAX_SENTENCES,
        )
        
        # 创建文档处理器
        document_processor = DocumentProcessor(
            config,
            ocr_provider,
            vlm_provider,
            file_reader_registry=file_reader_registry,
            chunking_strategy=chunking_strategy,
        )
        
        # 初始化VLM Extractor
        vlm_extractor = self._init_vlm_extractor(config)
        
        # 初始化ImageStore
        image_store = self._init_image_store(config)
        
        return ProcessingBundle(
            document_processor=document_processor,
            ocr_provider=ocr_provider,
            vlm_provider=vlm_provider,
            image_store=image_store,
            chunking_strategy=chunking_strategy,
        )
    
    def create_generation_bundle(self, config, retrieval_bundle: RetrievalBundle) -> GenerationBundle:
        """创建生成Bundle
        
        为什么需要retrieval_bundle：
        1. GenerationBundle依赖RetrievalBundle
        2. 通过构造函数注入，避免循环依赖
        """
        logger.info("Creating GenerationBundle")
        
        # 创建LLM客户端
        llm_client = LLMClient(
            config.MIMO_API_KEY,
            config.MIMO_API_BASE,
            config.MIMO_MODEL,
        )
        
        # 创建缓存管理器
        cache_manager = CacheManager({
            "use_cache": config.USE_CACHE,
            "l1_max_size": config.CACHE_L1_MAX_SIZE,
            "l1_ttl": config.CACHE_L1_TTL,
            "use_redis": config.USE_REDIS,
            "redis_host": config.REDIS_HOST,
            "redis_port": config.REDIS_PORT,
        })
        
        # 创建置信度评估器
        confidence_evaluator = ConfidenceEvaluator(
            threshold=config.SIMILARITY_THRESHOLD,
            min_docs=2,
        )
        
        # 创建引用验证器
        citation_verifier = CitationVerifier(
            llm_client=llm_client,
            threshold=getattr(config, "CITATION_CONFIDENCE_THRESHOLD", 0.5),
        )
        
        # 创建Self-RAG反思器
        self_rag_reflector = SelfRAGReflector(llm_client=llm_client)
        
        return GenerationBundle(
            llm_client=llm_client,
            cache_manager=cache_manager,
            confidence_evaluator=confidence_evaluator,
            citation_verifier=citation_verifier,
            self_rag_reflector=self_rag_reflector,
            retrieval_bundle=retrieval_bundle,
        )
    
    def _init_ocr_provider(self, config):
        """初始化OCR provider"""
        # 复用现有的初始化逻辑
        from core.services import _init_ocr_provider
        return _init_ocr_provider(config)
    
    def _init_vlm_provider(self, config):
        """初始化VLM provider"""
        from core.services import _init_vlm_provider
        return _init_vlm_provider(config)
    
    def _init_vlm_extractor(self, config):
        """初始化VLM Extractor"""
        from core.services import _init_vlm_extractor
        return _init_vlm_extractor(config)
    
    def _init_image_store(self, config):
        """初始化ImageStore"""
        from core.services import _init_image_store
        return _init_image_store(config)
    
    def _build_file_reader_registry(self, ocr_provider, vlm_provider):
        """构建文件读取器注册表"""
        from core.services import _build_file_reader_registry
        return _build_file_reader_registry(ocr_provider, vlm_provider)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_services/test_bundle_factory.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 提交代码**

```bash
git add backend/core/services/bundle_factory.py tests/unit/test_services/test_bundle_factory.py
git commit -m "feat: implement BundleFactory"
```

---

### Task 7: 重构RAGEngine使用Bundle

**Files:**
- Modify: `backend/core/rag_engine.py`
- Test: `tests/unit/test_rag_engine.py`

- [ ] **Step 1: 编写RAGEngine测试**

```python
# tests/unit/test_rag_engine.py (新增测试)
import pytest
from unittest.mock import Mock, MagicMock, patch
from backend.core.rag_engine import RAGEngine

class TestRAGEngineWithBundles:
    """测试RAGEngine使用Bundle架构"""
    
    @pytest.fixture
    def mock_config(self):
        """创建mock配置"""
        config = Mock()
        config.TOP_K = 5
        config.BM25_TOP_K = 5
        config.RRF_K = 60
        config.RRF_WEIGHT_VECTOR = 0.7
        config.RRF_WEIGHT_BM25 = 0.3
        config.SIMILARITY_THRESHOLD = 0.5
        config.USE_HYDE = False
        config.MULTI_QUERY_ENABLED = False
        config.MULTI_QUERY_COUNT = 3
        config.RERANK_TOP_K = 5
        config.RERANK_GATE_THRESHOLD = 0.3
        config.CITATION_VERIFY_ENABLED = True
        config.SELF_RAG_ENABLED = True
        config.RETRIEVAL_REFETCH_ENABLED = True
        return config
    
    @patch('backend.core.rag_engine.BundleFactory')
    def test_rag_engine_initializes_bundles(self, mock_factory_class, mock_config):
        """验证RAGEngine初始化Bundle"""
        # 准备mock
        mock_factory = Mock()
        mock_factory_class.return_value = mock_factory
        mock_factory.create_retrieval_bundle.return_value = Mock()
        mock_factory.create_processing_bundle.return_value = Mock()
        mock_factory.create_generation_bundle.return_value = Mock()
        
        # 执行测试
        engine = RAGEngine(mock_config)
        
        # 验证Bundle被创建
        assert hasattr(engine, '_retrieval')
        assert hasattr(engine, '_processing')
        assert hasattr(engine, '_generation')
    
    @patch('backend.core.rag_engine.BundleFactory')
    def test_rag_engine_delegates_retrieve(self, mock_factory_class, mock_config):
        """验证RAGEngine.retrieve委托给Bundle"""
        # 准备mock
        mock_factory = Mock()
        mock_factory_class.return_value = mock_factory
        mock_retrieval = Mock()
        mock_factory.create_retrieval_bundle.return_value = mock_retrieval
        mock_factory.create_processing_bundle.return_value = Mock()
        mock_factory.create_generation_bundle.return_value = Mock()
        
        # 执行测试
        engine = RAGEngine(mock_config)
        engine.retrieve("test query", top_k=5)
        
        # 验证委托
        mock_retrieval.retrieve.assert_called_once_with("test query", 5)
    
    @patch('backend.core.rag_engine.BundleFactory')
    def test_rag_engine_backward_compat(self, mock_factory_class, mock_config):
        """验证RAGEngine向后兼容"""
        # 准备mock
        mock_factory = Mock()
        mock_factory_class.return_value = mock_factory
        mock_retrieval = Mock()
        mock_retrieval._embedding_service = Mock()
        mock_factory.create_retrieval_bundle.return_value = mock_retrieval
        mock_factory.create_processing_bundle.return_value = Mock()
        mock_factory.create_generation_bundle.return_value = Mock()
        
        # 执行测试
        engine = RAGEngine(mock_config)
        
        # 验证向后兼容属性
        assert hasattr(engine, 'embedding_service')
        assert engine.embedding_service is mock_retrieval._embedding_service
```

- [ ] **Step 2: 运行测试验证失败**

Run: `pytest tests/unit/test_rag_engine.py::TestRAGEngineWithBundles -v`
Expected: FAIL (导入错误或方法不存在)

- [ ] **Step 3: 重构RAGEngine**

```python
# backend/core/rag_engine.py (重构后)
"""RAG Engine: thin facade over Bundles.

After refactoring, this class uses BundleFactory to create
RetrievalBundle, ProcessingBundle, and GenerationBundle.
Backward-compatible attributes are exposed via properties.
"""

import logging
from typing import Generator, List, Dict, Any, Optional
from core.services.bundle_factory import BundleFactory
from core.services.retrieval_bundle import RetrievalBundle
from core.services.processing_bundle import ProcessingBundle
from core.services.generation_bundle import GenerationBundle
from core.services.protocols import RetrievalResult

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG engine -- thin facade that composes Bundles.
    
    为什么使用Bundle架构：
    1. 单一职责原则
    2. 清晰的服务边界
    3. 便于独立测试
    4. 向后兼容支持
    """
    
    def __init__(self, config, use_factory: bool = False):
        """Initialize RAG engine.
        
        Args:
            config: AppSettings configuration object
            use_factory: 保留参数，向后兼容
        """
        self._config = config
        
        # 创建BundleFactory
        factory = BundleFactory()
        
        # 创建Bundle（按依赖顺序）
        # 为什么按这个顺序：RetrievalBundle和ProcessingBundle独立，
        # GenerationBundle依赖RetrievalBundle
        self._retrieval = factory.create_retrieval_bundle(config)
        self._processing = factory.create_processing_bundle(config)
        self._generation = factory.create_generation_bundle(config, self._retrieval)
        
        # 向后兼容层（deprecated）
        self._setup_backward_compat(config)
        
        logger.info("RAGEngine initialized with Bundles")
    
    @classmethod
    def from_services(cls, config, infra, retrieval, ingestion, generation):
        """Construct facade from pre-existing infra bundle and services.
        
        保留此方法以支持现有的初始化方式。
        """
        instance = cls.__new__(cls)
        instance._config = config
        
        # 创建BundleFactory并创建Bundle
        factory = BundleFactory()
        instance._retrieval = factory.create_retrieval_bundle(config)
        instance._processing = factory.create_processing_bundle(config)
        instance._generation = factory.create_generation_bundle(config, instance._retrieval)
        
        instance._setup_backward_compat(config)
        return instance
    
    def _setup_backward_compat(self, config):
        """Populate backward-compatible attribute aliases from bundles.
        
        为什么保留：渐进式重构，避免破坏现有代码。
        计划：Phase 3移除，届时所有代码应使用Bundle接口。
        """
        # 检索相关组件
        self.embedding_service = self._retrieval._embedding_service
        self.vector_store = self._retrieval._vector_store
        self.bm25_retriever = self._retrieval._bm25_retriever
        self.rerank_manager = self._retrieval._rerank_manager
        self.cache_manager = self._retrieval._cache_manager
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
        
        # 配置属性
        self._citation_verify_enabled = getattr(config, 'CITATION_VERIFY_ENABLED', True)
        self._self_rag_enabled = getattr(config, 'SELF_RAG_ENABLED', True)
        self._refetch_enabled = getattr(config, 'RETRIEVAL_REFETCH_ENABLED', True)
        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.rrf_weight_vector = config.RRF_WEIGHT_VECTOR
        self.rrf_weight_bm25 = config.RRF_WEIGHT_BM25
        self.similarity_threshold = config.SIMILARITY_THRESHOLD
        self.use_hyde = config.USE_HYDE
        self.multi_query_enabled = config.MULTI_QUERY_ENABLED
        self.multi_query_count = config.MULTI_QUERY_COUNT
        self.rerank_top_k = config.RERANK_TOP_K
        self.rerank_gate_threshold = getattr(config, 'RERANK_GATE_THRESHOLD', 0.3)
    
    # 业务API - 委托给Bundle
    
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        use_bm25: bool = True,
        use_rerank: bool = True,
    ) -> List[RetrievalResult]:
        """执行检索"""
        return self._retrieval.retrieve(query, top_k, use_bm25, use_rerank)
    
    def classify_query(self, query: str) -> Dict[str, Any]:
        """分类查询意图"""
        return self._retrieval.classify_query(query)
    
    def process_document(
        self,
        file_path: str,
        file_type: str,
        chunk_strategy: str = "semantic",
    ) -> List[Dict[str, Any]]:
        """处理文档"""
        return self._processing.process_document(file_path, file_type, chunk_strategy)
    
    def extract_images(self, file_path: str) -> List[Dict[str, Any]]:
        """提取图片"""
        return self._processing.extract_images(file_path)
    
    def generate(
        self,
        query: str,
        context: List[RetrievalResult],
        images: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """生成回答"""
        return self._generation.generate(query, context, images)
    
    def verify_citation(self, claim: str, source: str) -> Dict[str, Any]:
        """验证引用"""
        return self._generation.verify_citation(claim, source)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `pytest tests/unit/test_rag_engine.py::TestRAGEngineWithBundles -v`
Expected: PASS (3 tests)

- [ ] **Step 5: 运行所有测试确保没有回归**

Run: `pytest tests/ -v`
Expected: PASS (所有测试通过)

- [ ] **Step 6: 提交代码**

```bash
git add backend/core/rag_engine.py tests/unit/test_rag_engine.py
git commit -m "refactor: RAGEngine to use Bundle architecture"
```

---

## 执行选择

**Plan complete and saved to `docs/superpowers/plans/2026-06-27-architecture-governance-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
