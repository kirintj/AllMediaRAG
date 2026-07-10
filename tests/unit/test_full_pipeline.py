"""完整检索管道集成测试

测试 full_retrieve 的完整流程：归一化缓存 → 并行分类+HyDE+MQ → 路由 → 检索 → RRF → 重排序
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


def _make_config():
    """创建测试用配置对象"""
    config = Mock()
    # 基础配置
    config.MIMO_API_KEY = "test-key"
    config.MIMO_API_BASE = "https://api.test.com/v1"
    config.MIMO_MODEL = "test-model"
    config.EMBEDDING_MODEL_PATH = "test-model-path"
    config.CHROMA_PERSIST_DIR = "/tmp/test_chroma"
    config.TOP_K = 3
    config.BM25_TOP_K = 6
    config.RRF_K = 60
    config.RRF_WEIGHT_VECTOR = 0.7
    config.RRF_WEIGHT_BM25 = 0.3
    config.SIMILARITY_THRESHOLD = 0.5
    config.MAX_HISTORY_TURNS = 5
    # 查询扩展
    config.USE_HYDE = True
    config.MULTI_QUERY_ENABLED = True
    config.MULTI_QUERY_COUNT = 3
    # 重排序
    config.RERANK_STRATEGY = "cohere"
    config.COHERE_API_KEY = "test-cohere-key"
    config.BGE_RERANKER_PATH = "test-bge-path"
    config.RERANK_TOP_K = 20
    # 缓存
    config.USE_CACHE = True
    config.CACHE_L1_MAX_SIZE = 100
    config.CACHE_L1_TTL = 60
    config.USE_REDIS = False
    config.REDIS_HOST = "localhost"
    config.REDIS_PORT = 6379
    # 语义切分
    config.SEMANTIC_CHUNK_PERCENTILE = 25
    config.SEMANTIC_CHUNK_MIN_SENTENCES = 2
    config.SEMANTIC_CHUNK_MAX_SENTENCES = 20
    # 新增：避免 Mock 对象被当作路径
    config.BM25_PERSIST_DIR = ""
    config.VECTOR_STORE_PROVIDER = "chroma"
    config.OCR_PROVIDER = "none"
    config.USE_VLM = False
    config.VLM_MODEL = ""
    config.VLM_API_BASE = ""
    config.CITATION_VERIFY_ENABLED = True
    config.CITATION_CONFIDENCE_THRESHOLD = 0.5
    config.RETRIEVAL_REFETCH_ENABLED = True
    config.CHUNKING_STRATEGY = "semantic"
    config.CHUNK_SIZE = 512
    config.CHUNK_OVERLAP = 50
    # RAGEngine backward compat attrs
    config.RERANK_GATE_THRESHOLD = 0.3
    config.CITATION_VERIFY_ENABLED = True
    config.SELF_RAG_ENABLED = True
    config.RETRIEVAL_REFETCH_ENABLED = True
    config.EMBEDDING_PROVIDER = "sentence-transformer"
    config.SILICONFLOW_API_KEY = ""
    config.SILICONFLOW_EMBEDDING_MODEL = "BAAI/bge-m3"
    config.SILICONFLOW_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
    return config


def _mock_vector_results():
    """模拟向量检索返回"""
    return {
        "documents": ["vector doc 1", "vector doc 2"],
        "metadatas": [
            {"source": "a.html", "section": "概述"},
            {"source": "b.html", "section": "用法"},
        ],
        "distances": [0.1, 0.2],
    }


def _mock_bm25_results():
    """模拟 BM25 检索返回"""
    return [
        {"id": "bm25_1", "text": "bm25 doc 1", "metadata": {"source": "c.html", "section": "示例"}},
        {"id": "bm25_2", "text": "bm25 doc 2", "metadata": {"source": "d.html", "section": "参数"}},
    ]


def _build_mock_infra(config):
    """Build a mock InfraBundle with sensible defaults.

    After refactoring, RAGEngine delegates full_retrieve() to
    RetrievalPipeline which reads components from InfraBundle.
    We patch create_infra to return this mock so we can control all deps.
    """
    from dataclasses import dataclass, field

    # Reuse the real InfraBundle dataclass so attribute access works
    from core.services import InfraBundle

    mock_embed = Mock()
    mock_embed.encode.side_effect = lambda texts: [[0.1] * 10 for _ in texts]
    mock_embed.encode_single.return_value = [0.1] * 10

    mock_vector = Mock()
    mock_vector.query.return_value = _mock_vector_results()

    mock_llm = Mock()
    mock_llm.generate.return_value = '{"intent_type":"factoid","confidence":0.5,"complexity":"simple"}'
    mock_llm.stream_generate.return_value = iter([])

    mock_bm25 = Mock()
    mock_bm25.search.return_value = []

    mock_rerank = Mock()
    mock_rerank.rerank.side_effect = lambda q, docs, top_k: [
        {**d, "rerank_score": 0.9 - i * 0.1} for i, d in enumerate(docs)
    ][:top_k]

    mock_cache = Mock()
    # Delegate to a real dict for cache get/set
    _cache_store = {}
    mock_cache.get.side_effect = lambda k: _cache_store.get(k)
    mock_cache.set.side_effect = lambda k, v: _cache_store.__setitem__(k, v)

    mock_classifier = Mock()
    mock_classifier.classify.return_value = {
        "intent_type": "factoid", "confidence": 0.5, "complexity": "medium"
    }

    mock_router = Mock()
    mock_router.route.return_value = {
        "use_hyde": False, "num_queries": 1,
        "rerank_top_k": config.RERANK_TOP_K,
        "weights": {"vector": config.RRF_WEIGHT_VECTOR, "bm25": config.RRF_WEIGHT_BM25},
    }

    mock_hyde = Mock()
    mock_hyde.rewrite_sync.return_value = []

    mock_mq = Mock()
    mock_mq.rewrite_sync.return_value = []

    rewriters = {"hyde": mock_hyde, "multi_query": mock_mq}

    mock_confidence = Mock()
    mock_confidence.evaluate.return_value = {"needs_refetch": False, "confidence": 0.8}

    executor = Mock()
    # Make executor.submit work like a real ThreadPoolExecutor
    from concurrent.futures import Future

    def _submit(fn, *args, **kwargs):
        f = Future()
        try:
            result = fn(*args, **kwargs)
            f.set_result(result)
        except Exception as e:
            f.set_exception(e)
        return f

    executor.submit.side_effect = _submit

    infra = InfraBundle(
        settings=config,
        embedding_service=mock_embed,
        vector_store=mock_vector,
        llm_client=mock_llm,
        bm25_retriever=mock_bm25,
        document_processor=Mock(),
        rerank_manager=mock_rerank,
        cache_manager=mock_cache,
        index_manager=Mock(),
        classifier=mock_classifier,
        router=mock_router,
        rewriters=rewriters,
        confidence_evaluator=mock_confidence,
        citation_verifier=Mock(),
        self_rag_reflector=Mock(),
        executor=executor,
        bm25_ready=True,
    )
    return infra


@patch("core.rag_engine.create_infra")
def test_full_retrieve_calls_all_modules(mock_create_infra):
    """测试 full_retrieve 按顺序调用所有模块"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    infra = _build_mock_infra(config)
    mock_create_infra.return_value = infra

    # 设置 BM25 返回结果
    infra.bm25_retriever.search.return_value = _mock_bm25_results()

    # Mock classifier
    infra.classifier.classify = Mock(return_value={
        "intent_type": "analytical", "confidence": 0.9, "complexity": "medium"
    })

    # Mock rewriters (retrieval pipeline reads from infra.rewriters)
    infra.rewriters["hyde"].rewrite_sync.return_value = ["假设性文档内容"]
    infra.rewriters["multi_query"].rewrite_sync.return_value = ["查询变体1", "查询变体2"]

    # 设置路由配置
    infra.router.route.return_value = {
        "use_hyde": True, "num_queries": 3,
        "rerank_top_k": config.RERANK_TOP_K,
        "weights": {"vector": 0.6, "bm25": 0.4},
    }

    engine = RAGEngine(config)

    # 执行
    result = engine.full_retrieve("Python 装饰器怎么用")

    # 验证：classifier 被调用
    infra.classifier.classify.assert_called_once_with("Python 装饰器怎么用")

    # 验证：向量检索被调用（批量 encode + query）
    assert infra.embedding_service.encode.call_count >= 1
    assert infra.vector_store.query.call_count >= 1

    # 验证：BM25 检索被调用
    assert infra.bm25_retriever.search.call_count >= 1

    # 验证：返回格式正确
    assert "documents" in result
    assert "metadatas" in result
    assert "distances" in result
    assert len(result["documents"]) <= config.TOP_K


@patch("core.rag_engine.create_infra")
def test_full_retrieve_cache_hit(mock_create_infra):
    """测试缓存命中时直接返回，不调用检索"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    infra = _build_mock_infra(config)
    mock_create_infra.return_value = infra

    engine = RAGEngine(config)

    # 使用归一化后的 key 预热缓存
    import hashlib
    normalized = engine.retrieval._normalize_query("test query")
    cache_key = f"rag:{hashlib.md5(normalized.encode()).hexdigest()}"
    cached_result = {
        "documents": ["cached doc"],
        "metadatas": [{"source": "cached.html", "section": "test"}],
        "distances": [0.0],
    }
    engine.cache_manager.set(cache_key, cached_result)

    # 重置 mock 调用记录
    infra.vector_store.query.reset_mock()
    infra.bm25_retriever.search.reset_mock()

    # 执行 —— 应命中缓存
    result = engine.full_retrieve("test query")

    # 验证：返回缓存结果
    assert result == cached_result

    # 验证：检索未被调用
    infra.vector_store.query.assert_not_called()
    infra.bm25_retriever.search.assert_not_called()


@patch("core.rag_engine.create_infra")
def test_full_retrieve_classifier_fallback(mock_create_infra):
    """测试分类器失败时降级到默认配置"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    config.USE_HYDE = False
    config.MULTI_QUERY_ENABLED = False

    infra = _build_mock_infra(config)
    mock_create_infra.return_value = infra

    infra.bm25_retriever.search.return_value = _mock_bm25_results()

    # Mock classifier 返回降级默认值
    infra.classifier.classify = Mock(side_effect=RuntimeError("LLM unavailable"))

    engine = RAGEngine(config)

    # 不应抛出异常
    result = engine.full_retrieve("test query")

    # 应该仍然返回结果（降级到默认分类 + 简化检索）
    assert "documents" in result
    assert len(result["documents"]) > 0


@patch("core.rag_engine.create_infra")
def test_full_retrieve_rerank_fallback(mock_create_infra):
    """测试重排序失败时降级到原始顺序"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    infra = _build_mock_infra(config)
    mock_create_infra.return_value = infra

    infra.bm25_retriever.search.return_value = _mock_bm25_results()

    # RerankManager.rerank 抛出异常
    infra.rerank_manager.rerank.side_effect = RuntimeError("Rerank API timeout")

    # Mock classifier
    infra.classifier.classify = Mock(return_value={
        "intent_type": "factoid", "confidence": 0.5, "complexity": "simple"
    })

    engine = RAGEngine(config)

    # 不应抛出异常
    result = engine.full_retrieve("test query")

    # 应该返回结果（降级到无重排序）
    assert "documents" in result
    assert len(result["documents"]) > 0


@patch("core.rag_engine.create_infra")
def test_full_retrieve_dynamic_weights(mock_create_infra):
    """测试路由器返回动态权重后正确传递到 RRF"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    infra = _build_mock_infra(config)
    mock_create_infra.return_value = infra

    infra.bm25_retriever.search.return_value = _mock_bm25_results()

    # Mock classifier
    infra.classifier.classify = Mock(return_value={
        "intent_type": "exploratory", "confidence": 0.8, "complexity": "complex"
    })

    # Mock rewriters
    infra.rewriters["hyde"].rewrite_sync.return_value = ["假设文档"]
    infra.rewriters["multi_query"].rewrite_sync.return_value = ["变体1", "变体2"]

    # 设置路由配置: exploratory + complex → weights = {"vector": 0.5, "bm25": 0.5}
    infra.router.route.return_value = {
        "use_hyde": True, "num_queries": 3,
        "rerank_top_k": config.RERANK_TOP_K,
        "weights": {"vector": 0.5, "bm25": 0.5},
    }

    engine = RAGEngine(config)

    # spy on reciprocal_rank_fusion (on retrieval pipeline)
    original_rrf = engine.retrieval.reciprocal_rank_fusion
    rrf_calls = []

    def spy_rrf(results_list, weights, k):
        rrf_calls.append({"weights": weights, "k": k})
        return original_rrf(results_list, weights, k)

    engine.retrieval.reciprocal_rank_fusion = spy_rrf

    engine.full_retrieve("深入分析 Python 内存管理机制")

    # exploratory + complex → weights = {"vector": 0.5, "bm25": 0.5}
    assert len(rrf_calls) >= 1
    last_call = rrf_calls[-1]
    assert last_call["weights"][0] == 0.5  # vector weight
    assert last_call["weights"][1] == 0.5  # bm25 weight


@patch("core.rag_engine.create_infra")
def test_full_retrieve_hyde_skips_for_high_confidence_factoid(mock_create_infra):
    """测试高置信度事实型查询时 HyDE 被跳过"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    infra = _build_mock_infra(config)
    mock_create_infra.return_value = infra

    # 高置信度事实型
    infra.classifier.classify = Mock(return_value={
        "intent_type": "factoid", "confidence": 0.9, "complexity": "simple"
    })

    # 设置路由: factoid + simple → use_hyde=False
    infra.router.route.return_value = {
        "use_hyde": False, "num_queries": 2,
        "rerank_top_k": 30,
        "weights": {"vector": 0.6, "bm25": 0.4},
    }

    # Mock rewriters - HyDE 应该不被调用
    infra.rewriters["hyde"].rewrite_sync.return_value = ["假设性文档不应被使用"]
    infra.rewriters["multi_query"].rewrite_sync.return_value = ["变体1"]

    engine = RAGEngine(config)

    # spy on embedding encode (use infra.embedding_service which is the same object)
    encode_calls = []
    original_encode = infra.embedding_service.encode

    def spy_encode(texts):
        encode_calls.extend(texts)
        return original_encode(texts)

    infra.embedding_service.encode = spy_encode

    engine.full_retrieve("Python 的 GIL 是什么")

    # factoid + use_hyde=False → HyDE rewriter 不应被调用
    # 所以搜索查询不应包含假设文档
    assert "假设性文档不应被使用" not in encode_calls
    assert "Python 的 GIL 是什么" in encode_calls
