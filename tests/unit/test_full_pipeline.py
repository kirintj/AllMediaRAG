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


@patch("core.reranking.manager.CohereReranker")
@patch("core.reranking.manager.BGEReranker")
@patch("core.rag_engine.EmbeddingService")
@patch("core.rag_engine.VectorStore")
@patch("core.rag_engine.LLMClient")
@patch("core.rag_engine.DocumentProcessor")
def test_full_retrieve_calls_all_modules(
    mock_doc_proc, mock_llm, mock_vector, mock_embed, mock_bge_cls, mock_cohere_cls
):
    """测试 full_retrieve 按顺序调用所有模块"""
    from core.rag_engine import RAGEngine

    config = _make_config()

    # 设置 mock — 使用 encode (batch) 而非 encode_single
    mock_embed_instance = Mock()
    # encode 返回与输入等长的向量列表
    mock_embed_instance.encode.side_effect = lambda texts: [[0.1] * 10 for _ in texts]
    mock_embed_instance.encode_single.return_value = [0.1] * 10
    mock_embed.return_value = mock_embed_instance

    mock_vector_instance = Mock()
    mock_vector_instance.query.return_value = _mock_vector_results()
    mock_vector.return_value = mock_vector_instance

    mock_llm_instance = Mock()
    mock_llm_instance.stream_generate.return_value = iter(["回答"])
    mock_llm.return_value = mock_llm_instance

    mock_doc_proc_instance = Mock()
    mock_doc_proc.return_value = mock_doc_proc_instance

    # RerankManager mock
    mock_cohere = Mock()
    mock_cohere.is_available.return_value = True
    mock_cohere.rerank.side_effect = lambda q, docs, top_k: [
        {**d, "rerank_score": 0.9 - i * 0.1} for i, d in enumerate(docs)
    ][:top_k]
    mock_cohere_cls.return_value = mock_cohere
    mock_bge_cls.return_value = Mock(is_available=Mock(return_value=False))

    engine = RAGEngine(config)
    engine.bm25_retriever = Mock()
    engine.bm25_retriever.search.return_value = _mock_bm25_results()

    # Mock 各模块以避免 LLM 调用
    engine.classifier.classify = Mock(return_value={
        "intent_type": "analytical", "confidence": 0.9, "complexity": "medium"
    })
    engine.hyde_generator.generate_hypothetical_document = Mock(return_value="假设性文档内容")
    engine.multi_query_generator.generate_queries = Mock(
        return_value=["Python 装饰器怎么用", "查询变体1", "查询变体2"]
    )

    # 执行
    result = engine.full_retrieve("Python 装饰器怎么用")

    # 验证：classifier 被调用
    engine.classifier.classify.assert_called_once_with("Python 装饰器怎么用")

    # 验证：向量检索被调用（批量 encode + query）
    assert mock_embed_instance.encode.call_count >= 1
    assert mock_vector_instance.query.call_count >= 1

    # 验证：BM25 检索被调用
    assert engine.bm25_retriever.search.call_count >= 1

    # 验证：返回格式正确
    assert "documents" in result
    assert "metadatas" in result
    assert "distances" in result
    assert len(result["documents"]) <= config.TOP_K


@patch("core.reranking.manager.CohereReranker")
@patch("core.reranking.manager.BGEReranker")
@patch("core.rag_engine.EmbeddingService")
@patch("core.rag_engine.VectorStore")
@patch("core.rag_engine.LLMClient")
@patch("core.rag_engine.DocumentProcessor")
def test_full_retrieve_cache_hit(
    mock_doc_proc, mock_llm, mock_vector, mock_embed, mock_bge_cls, mock_cohere_cls
):
    """测试缓存命中时直接返回，不调用检索"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    mock_embed.return_value = Mock(
        encode_single=Mock(return_value=[0.1] * 10),
        encode=Mock(side_effect=lambda t: [[0.1] * 10 for _ in t]),
    )
    mock_vector.return_value = Mock(query=Mock(return_value=_mock_vector_results()))
    mock_llm.return_value = Mock(
        generate=Mock(return_value='{"intent_type":"factoid","confidence":0.5,"complexity":"simple"}'),
        stream_generate=Mock(return_value=iter([])),
    )
    mock_doc_proc.return_value = Mock()
    mock_cohere_cls.return_value = Mock(is_available=Mock(return_value=False))
    mock_bge_cls.return_value = Mock(is_available=Mock(return_value=False))

    engine = RAGEngine(config)
    engine.bm25_retriever = Mock(search=Mock(return_value=[]))

    # 使用归一化后的 key 预热缓存
    import hashlib
    normalized = engine._normalize_query("test query")
    cache_key = f"rag:{hashlib.md5(normalized.encode()).hexdigest()}"
    cached_result = {
        "documents": ["cached doc"],
        "metadatas": [{"source": "cached.html", "section": "test"}],
        "distances": [0.0],
    }
    engine.cache_manager.set(cache_key, cached_result)

    # 重置 mock 调用记录
    mock_vector.return_value.query.reset_mock()
    engine.bm25_retriever.search.reset_mock()

    # 执行 —— 应命中缓存
    result = engine.full_retrieve("test query")

    # 验证：返回缓存结果
    assert result == cached_result

    # 验证：检索未被调用
    mock_vector.return_value.query.assert_not_called()
    engine.bm25_retriever.search.assert_not_called()


@patch("core.reranking.manager.CohereReranker")
@patch("core.reranking.manager.BGEReranker")
@patch("core.rag_engine.EmbeddingService")
@patch("core.rag_engine.VectorStore")
@patch("core.rag_engine.LLMClient")
@patch("core.rag_engine.DocumentProcessor")
def test_full_retrieve_classifier_fallback(
    mock_doc_proc, mock_llm, mock_vector, mock_embed, mock_bge_cls, mock_cohere_cls
):
    """测试分类器失败时降级到默认配置"""
    from core.rag_engine import RAGEngine

    config = _make_config()
    config.USE_HYDE = False
    config.MULTI_QUERY_ENABLED = False

    mock_embed.return_value = Mock(
        encode_single=Mock(return_value=[0.1] * 10),
        encode=Mock(side_effect=lambda t: [[0.1] * 10 for _ in t]),
    )
    mock_vector.return_value = Mock(query=Mock(return_value=_mock_vector_results()))

    mock_llm_instance = Mock()
    mock_llm_instance.generate.side_effect = RuntimeError("LLM unavailable")
    mock_llm_instance.stream_generate.return_value = iter(["回答"])
    mock_llm.return_value = mock_llm_instance

    mock_doc_proc.return_value = Mock()
    mock_cohere_cls.return_value = Mock(is_available=Mock(return_value=False))
    mock_bge_cls.return_value = Mock(is_available=Mock(return_value=False))

    engine = RAGEngine(config)
    engine.bm25_retriever = Mock(search=Mock(return_value=_mock_bm25_results()))

    # Mock classifier 返回降级默认值
    engine.classifier.classify = Mock(side_effect=RuntimeError("LLM unavailable"))
    engine.hyde_generator.generate_hypothetical_document = Mock(return_value=None)
    engine.multi_query_generator.generate_queries = Mock(return_value=["test query"])

    # 不应抛出异常
    result = engine.full_retrieve("test query")

    # 应该仍然返回结果（降级到默认分类 + 简化检索）
    assert "documents" in result
    assert len(result["documents"]) > 0


@patch("core.reranking.manager.CohereReranker")
@patch("core.reranking.manager.BGEReranker")
@patch("core.rag_engine.EmbeddingService")
@patch("core.rag_engine.VectorStore")
@patch("core.rag_engine.LLMClient")
@patch("core.rag_engine.DocumentProcessor")
def test_full_retrieve_rerank_fallback(
    mock_doc_proc, mock_llm, mock_vector, mock_embed, mock_bge_cls, mock_cohere_cls
):
    """测试重排序失败时降级到原始顺序"""
    from core.rag_engine import RAGEngine

    config = _make_config()

    mock_embed.return_value = Mock(
        encode_single=Mock(return_value=[0.1] * 10),
        encode=Mock(side_effect=lambda t: [[0.1] * 10 for _ in t]),
    )
    mock_vector.return_value = Mock(query=Mock(return_value=_mock_vector_results()))
    mock_llm.return_value = Mock(
        generate=Mock(return_value='{"intent_type":"factoid","confidence":0.5,"complexity":"simple"}'),
        stream_generate=Mock(return_value=iter([])),
    )
    mock_doc_proc.return_value = Mock()

    # RerankManager.rerank 抛出异常
    mock_cohere = Mock()
    mock_cohere.is_available.return_value = True
    mock_cohere.rerank.side_effect = RuntimeError("Rerank API timeout")
    mock_cohere_cls.return_value = mock_cohere
    mock_bge_cls.return_value = Mock(is_available=Mock(return_value=False))

    engine = RAGEngine(config)
    engine.bm25_retriever = Mock(search=Mock(return_value=_mock_bm25_results()))
    engine.classifier.classify = Mock(return_value={
        "intent_type": "factoid", "confidence": 0.5, "complexity": "simple"
    })
    engine.hyde_generator.generate_hypothetical_document = Mock(return_value=None)
    engine.multi_query_generator.generate_queries = Mock(return_value=["test query"])

    # 不应抛出异常
    result = engine.full_retrieve("test query")

    # 应该返回结果（降级到无重排序）
    assert "documents" in result
    assert len(result["documents"]) > 0


@patch("core.reranking.manager.CohereReranker")
@patch("core.reranking.manager.BGEReranker")
@patch("core.rag_engine.EmbeddingService")
@patch("core.rag_engine.VectorStore")
@patch("core.rag_engine.LLMClient")
@patch("core.rag_engine.DocumentProcessor")
def test_full_retrieve_dynamic_weights(
    mock_doc_proc, mock_llm, mock_vector, mock_embed, mock_bge_cls, mock_cohere_cls
):
    """测试路由器返回动态权重后正确传递到 RRF"""
    from core.rag_engine import RAGEngine

    config = _make_config()

    mock_embed.return_value = Mock(
        encode_single=Mock(return_value=[0.1] * 10),
        encode=Mock(side_effect=lambda t: [[0.1] * 10 for _ in t]),
    )
    mock_vector.return_value = Mock(query=Mock(return_value=_mock_vector_results()))
    mock_llm.return_value = Mock(
        generate=Mock(return_value='{"intent_type":"exploratory","confidence":0.8,"complexity":"complex"}'),
        stream_generate=Mock(return_value=iter([])),
    )
    mock_doc_proc.return_value = Mock()
    mock_cohere_cls.return_value = Mock(is_available=Mock(return_value=False))
    mock_bge_cls.return_value = Mock(is_available=Mock(return_value=False))

    engine = RAGEngine(config)
    engine.bm25_retriever = Mock(search=Mock(return_value=_mock_bm25_results()))
    engine.classifier.classify = Mock(return_value={
        "intent_type": "exploratory", "confidence": 0.8, "complexity": "complex"
    })
    engine.hyde_generator.generate_hypothetical_document = Mock(return_value="假设文档")
    engine.multi_query_generator.generate_queries = Mock(
        return_value=["深入分析 Python 内存管理机制", "变体1", "变体2"]
    )

    # spy on reciprocal_rank_fusion
    original_rrf = engine.reciprocal_rank_fusion
    rrf_calls = []

    def spy_rrf(results_list, weights, k):
        rrf_calls.append({"weights": weights, "k": k})
        return original_rrf(results_list, weights, k)

    engine.reciprocal_rank_fusion = spy_rrf

    engine.full_retrieve("深入分析 Python 内存管理机制")

    # exploratory + complex → weights = {"vector": 0.5, "bm25": 0.5}
    assert len(rrf_calls) >= 1
    last_call = rrf_calls[-1]
    assert last_call["weights"][0] == 0.5  # vector weight
    assert last_call["weights"][1] == 0.5  # bm25 weight


@patch("core.reranking.manager.CohereReranker")
@patch("core.reranking.manager.BGEReranker")
@patch("core.rag_engine.EmbeddingService")
@patch("core.rag_engine.VectorStore")
@patch("core.rag_engine.LLMClient")
@patch("core.rag_engine.DocumentProcessor")
def test_full_retrieve_hyde_skips_for_high_confidence_factoid(
    mock_doc_proc, mock_llm, mock_vector, mock_embed, mock_bge_cls, mock_cohere_cls
):
    """测试高置信度事实型查询时 HyDE 被跳过"""
    from core.rag_engine import RAGEngine

    config = _make_config()

    mock_embed.return_value = Mock(
        encode_single=Mock(return_value=[0.1] * 10),
        encode=Mock(side_effect=lambda t: [[0.1] * 10 for _ in t]),
    )
    mock_vector.return_value = Mock(query=Mock(return_value=_mock_vector_results()))
    mock_llm.return_value = Mock(
        generate=Mock(return_value='{"intent_type":"factoid","confidence":0.9,"complexity":"simple"}'),
        stream_generate=Mock(return_value=iter([])),
    )
    mock_doc_proc.return_value = Mock()
    mock_cohere_cls.return_value = Mock(is_available=Mock(return_value=False))
    mock_bge_cls.return_value = Mock(is_available=Mock(return_value=False))

    engine = RAGEngine(config)
    engine.bm25_retriever = Mock(search=Mock(return_value=[]))

    # 高置信度事实型 + HyDE 文档
    engine.classifier.classify = Mock(return_value={
        "intent_type": "factoid", "confidence": 0.9, "complexity": "simple"
    })
    engine.hyde_generator.generate_hypothetical_document = Mock(return_value="假设性文档不应被使用")
    engine.multi_query_generator.generate_queries = Mock(return_value=["Python 的 GIL 是什么", "变体1"])

    # spy on embedding encode
    encode_calls = []
    original_encode = engine.embedding_service.encode

    def spy_encode(texts):
        encode_calls.extend(texts)
        return original_encode(texts)

    engine.embedding_service.encode = spy_encode

    engine.full_retrieve("Python 的 GIL 是什么")

    # factoid + confidence > 0.85 → hyde_doc 被置为 None
    # 所以搜索查询只有原始查询 + 变体，不应包含假设文档
    assert "假设性文档不应被使用" not in encode_calls
    assert "Python 的 GIL 是什么" in encode_calls
