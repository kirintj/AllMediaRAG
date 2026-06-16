import os
import re
import uuid
import time
import hashlib
import logging
import asyncio
import threading
from typing import Generator
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from core.embedding_service import EmbeddingService
from core.vector_store import VectorStore
from core.llm_client import LLMClient
from core.document_processor import DocumentProcessor
from core.bm25_retriever import BM25Retriever
from core.query_understanding.classifier import QueryClassifier
from core.query_understanding.router import QueryRouter
from core.query_understanding.hyde_generator import HyDEGenerator
from core.query_understanding.multi_query import MultiQueryGenerator
from core.query_understanding.rewriters import HyDERewriter, MultiQueryRewriter
from core.reranking.manager import RerankManager
from core.performance.cache.manager import CacheManager
from core.ocr.paddle_provider import PaddleOCRProvider
from core.ocr.tesseract_provider import TesseractOCRProvider
from core.ocr.vlm_provider import VLMProvider
from core.index_manager import IndexManager
from core.verification.citation_verifier import CitationVerifier
from core.retrieval.confidence_evaluator import ConfidenceEvaluator
from core.providers.factory import ProviderFactory
from core.providers.adapters import (
    ChromaVectorStoreAdapter,
    SentenceTransformerAdapter,
    OpenAICompatibleLLMAdapter,
)

logger = logging.getLogger(__name__)


class RAGEngine:
    """RAG 引擎：组合各模块，提供完整的 RAG 查询接口

    支持两种初始化模式：
    1. 直接模式：直接实例化现有实现（默认）
    2. 工厂模式：通过 ProviderFactory 创建可插拔组件
    """

    def __init__(self, config, use_factory: bool = False):
        """初始化 RAG 引擎

        Args:
            config: 配置对象
            use_factory: 是否使用工厂模式创建组件
        """
        if use_factory:
            self._init_with_factory(config)
        else:
            self._init_direct(config)

        # 初始化 OCR 提供者
        ocr_provider = self._init_ocr_provider(config)

        # 初始化 VLM 提供者
        vlm_provider = self._init_vlm_provider(config)

        # 构建文件读取器注册表
        file_reader_registry = self._build_file_reader_registry(ocr_provider, vlm_provider)

        self.document_processor = DocumentProcessor(
            config, ocr_provider, vlm_provider,
            file_reader_registry=file_reader_registry
        )
        self.document_processor.set_embedding_service(self.embedding_service)

        # BM25：优先从磁盘加载，加载失败再从向量库重建
        bm25_base_dir = getattr(config, 'BM25_PERSIST_DIR', '') or config.CHROMA_PERSIST_DIR
        bm25_path = os.path.join(bm25_base_dir, "bm25_index.pkl")
        self.bm25_retriever = BM25Retriever(persist_path=bm25_path)
        self._bm25_lock = threading.Lock()

        if not self.bm25_retriever.load():
            self._bm25_ready = False
            threading.Thread(target=self._rebuild_bm25_index, daemon=True).start()
        else:
            self._bm25_ready = True

        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.rrf_weight_vector = config.RRF_WEIGHT_VECTOR
        self.rrf_weight_bm25 = config.RRF_WEIGHT_BM25
        self.similarity_threshold = config.SIMILARITY_THRESHOLD

        # 查询理解层
        self.classifier = QueryClassifier()
        self.router = QueryRouter()
        self.hyde_generator = HyDEGenerator(self.llm_client)
        self.multi_query_generator = MultiQueryGenerator(self.llm_client)

        # 查询改写器注册表
        self.rewriters: dict = {}
        if config.USE_HYDE:
            self.rewriters["hyde"] = HyDERewriter(self.llm_client)
        if config.MULTI_QUERY_ENABLED:
            self.rewriters["multi_query"] = MultiQueryRewriter(
                self.llm_client, num_queries=config.MULTI_QUERY_COUNT
            )

        # 重排序层
        self.rerank_manager = RerankManager(config)

        # 缓存层
        self.cache_manager = CacheManager({
            "use_cache": config.USE_CACHE,
            "l1_max_size": config.CACHE_L1_MAX_SIZE,
            "l1_ttl": config.CACHE_L1_TTL,
            "use_redis": config.USE_REDIS,
            "redis_host": config.REDIS_HOST,
            "redis_port": config.REDIS_PORT,
            "l2_ttl": getattr(config, 'CACHE_L2_TTL', 600),
        })

        # 增量索引管理
        if getattr(config, 'VECTOR_STORE_PROVIDER', 'chroma') == "pgvector":
            from core.providers.pgvector_index_adapter import PgIndexManager
            self.index_manager = PgIndexManager(database_url=config.database_url)
        else:
            self.index_manager = IndexManager(
                state_file=os.path.join(config.CHROMA_PERSIST_DIR, "index_state.json")
            )

        # 引用核查
        self.citation_verifier = CitationVerifier(
            llm_client=self.llm_client,
            threshold=getattr(config, 'CITATION_CONFIDENCE_THRESHOLD', 0.5)
        )
        self._citation_verify_enabled = getattr(config, 'CITATION_VERIFY_ENABLED', True)

        # 低置信度二次检索
        self.confidence_evaluator = ConfidenceEvaluator(
            threshold=config.SIMILARITY_THRESHOLD,
            min_docs=2
        )
        self._refetch_enabled = getattr(config, 'RETRIEVAL_REFETCH_ENABLED', True)

        # 配置项缓存
        self.use_hyde = config.USE_HYDE
        self.multi_query_enabled = config.MULTI_QUERY_ENABLED
        self.multi_query_count = config.MULTI_QUERY_COUNT
        self.rerank_top_k = config.RERANK_TOP_K

    def _init_direct(self, config):
        """直接模式初始化：使用现有实现类

        Args:
            config: 配置对象
        """
        self.embedding_service = EmbeddingService(config.EMBEDDING_MODEL_PATH)

        # 根据配置选择向量存储后端
        if getattr(config, 'VECTOR_STORE_PROVIDER', 'chroma') == "pgvector":
            from core.providers.pgvector_adapter import PgVectorStoreAdapter
            self.vector_store = PgVectorStoreAdapter(database_url=config.database_url)
        else:
            self.vector_store = VectorStore(config.CHROMA_PERSIST_DIR)

        self.llm_client = LLMClient(
            config.MIMO_API_KEY,
            config.MIMO_API_BASE,
            config.MIMO_MODEL
        )

        # BM25：优先从磁盘加载，加载失败再从向量库重建
        bm25_base_dir = getattr(config, 'BM25_PERSIST_DIR', '') or config.CHROMA_PERSIST_DIR
        bm25_path = os.path.join(bm25_base_dir, "bm25_index.pkl")
        self.bm25_retriever = BM25Retriever(persist_path=bm25_path)
        self._bm25_lock = threading.Lock()

        if not self.bm25_retriever.load():
            self._bm25_ready = False
            threading.Thread(target=self._rebuild_bm25_index, daemon=True).start()
        else:
            self._bm25_ready = True

        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.rrf_weight_vector = config.RRF_WEIGHT_VECTOR
        self.rrf_weight_bm25 = config.RRF_WEIGHT_BM25
        self.similarity_threshold = config.SIMILARITY_THRESHOLD

        # 查询理解层
        self.classifier = QueryClassifier()
        self.router = QueryRouter()
        self.hyde_generator = HyDEGenerator(self.llm_client)
        self.multi_query_generator = MultiQueryGenerator(self.llm_client)

        # 查询改写器注册表
        self.rewriters: dict = {}
        if config.USE_HYDE:
            self.rewriters["hyde"] = HyDERewriter(self.llm_client)
        if config.MULTI_QUERY_ENABLED:
            self.rewriters["multi_query"] = MultiQueryRewriter(
                self.llm_client, num_queries=config.MULTI_QUERY_COUNT
            )

        # 重排序层
        self.rerank_manager = RerankManager(config)

        # 缓存层
        self.cache_manager = CacheManager({
            "use_cache": config.USE_CACHE,
            "l1_max_size": config.CACHE_L1_MAX_SIZE,
            "l1_ttl": config.CACHE_L1_TTL,
            "use_redis": config.USE_REDIS,
            "redis_host": config.REDIS_HOST,
            "redis_port": config.REDIS_PORT,
            "l2_ttl": getattr(config, 'CACHE_L2_TTL', 600),
        })

        # 增量索引管理
        if getattr(config, 'VECTOR_STORE_PROVIDER', 'chroma') == "pgvector":
            from core.providers.pgvector_index_adapter import PgIndexManager
            self.index_manager = PgIndexManager(database_url=config.database_url)
        else:
            self.index_manager = IndexManager(
                state_file=os.path.join(config.CHROMA_PERSIST_DIR, "index_state.json")
            )

        # 引用核查
        self.citation_verifier = CitationVerifier(
            llm_client=self.llm_client,
            threshold=getattr(config, 'CITATION_CONFIDENCE_THRESHOLD', 0.5)
        )
        self._citation_verify_enabled = getattr(config, 'CITATION_VERIFY_ENABLED', True)

        # 低置信度二次检索
        self.confidence_evaluator = ConfidenceEvaluator(
            threshold=config.SIMILARITY_THRESHOLD,
            min_docs=2
        )
        self._refetch_enabled = getattr(config, 'RETRIEVAL_REFETCH_ENABLED', True)

        logger.info("RAGEngine initialized in direct mode")

    def _init_with_factory(self, config):
        """工厂模式初始化：通过 ProviderFactory 创建可插拔组件

        Args:
            config: 配置对象
        """
        # 注册默认 Provider
        ProviderFactory.register_vector_store("chroma", ChromaVectorStoreAdapter)
        ProviderFactory.register_embedding_provider("sentence-transformer", SentenceTransformerAdapter)
        ProviderFactory.register_llm_provider("openai-compatible", OpenAICompatibleLLMAdapter)

        # 注册 pgvector provider
        from core.providers.pgvector_adapter import PgVectorStoreAdapter
        ProviderFactory.register_vector_store("pgvector", PgVectorStoreAdapter)

        # 通过工厂创建组件
        self.embedding_service = ProviderFactory.create_embedding_provider(
            "sentence-transformer",
            model_path=config.EMBEDDING_MODEL_PATH
        )

        # 根据配置选择向量存储后端
        provider_name = getattr(config, 'VECTOR_STORE_PROVIDER', 'chroma')
        if provider_name == "pgvector":
            self.vector_store = ProviderFactory.create_vector_store(
                "pgvector",
                database_url=config.database_url,
            )
        else:
            self.vector_store = ProviderFactory.create_vector_store(
                "chroma",
                persist_dir=config.CHROMA_PERSIST_DIR,
            )
        self.llm_client = ProviderFactory.create_llm_provider(
            "openai-compatible",
            api_key=config.MIMO_API_KEY,
            api_base=config.MIMO_API_BASE,
            model=config.MIMO_MODEL
        )

        # BM25 索引（不使用工厂模式，因为它是独立的检索器）
        bm25_base_dir = getattr(config, 'BM25_PERSIST_DIR', '') or config.CHROMA_PERSIST_DIR
        bm25_path = os.path.join(bm25_base_dir, "bm25_index.pkl")
        self.bm25_retriever = BM25Retriever(persist_path=bm25_path)
        self._bm25_lock = threading.Lock()

        if not self.bm25_retriever.load():
            self._bm25_ready = False
            threading.Thread(target=self._rebuild_bm25_index, daemon=True).start()
        else:
            self._bm25_ready = True

        self.top_k = config.TOP_K
        self.bm25_top_k = config.BM25_TOP_K
        self.rrf_k = config.RRF_K
        self.rrf_weight_vector = config.RRF_WEIGHT_VECTOR
        self.rrf_weight_bm25 = config.RRF_WEIGHT_BM25
        self.similarity_threshold = config.SIMILARITY_THRESHOLD

        # 查询理解层
        self.classifier = QueryClassifier()
        self.router = QueryRouter()
        self.hyde_generator = HyDEGenerator(self.llm_client)
        self.multi_query_generator = MultiQueryGenerator(self.llm_client)

        # 查询改写器注册表
        self.rewriters: dict = {}
        if config.USE_HYDE:
            self.rewriters["hyde"] = HyDERewriter(self.llm_client)
        if config.MULTI_QUERY_ENABLED:
            self.rewriters["multi_query"] = MultiQueryRewriter(
                self.llm_client, num_queries=config.MULTI_QUERY_COUNT
            )

        # 重排序层
        self.rerank_manager = RerankManager(config)

        # 缓存层
        self.cache_manager = CacheManager({
            "use_cache": config.USE_CACHE,
            "l1_max_size": config.CACHE_L1_MAX_SIZE,
            "l1_ttl": config.CACHE_L1_TTL,
            "use_redis": config.USE_REDIS,
            "redis_host": config.REDIS_HOST,
            "redis_port": config.REDIS_PORT,
            "l2_ttl": getattr(config, 'CACHE_L2_TTL', 600),
        })

        # 增量索引管理
        if getattr(config, 'VECTOR_STORE_PROVIDER', 'chroma') == "pgvector":
            from core.providers.pgvector_index_adapter import PgIndexManager
            self.index_manager = PgIndexManager(database_url=config.database_url)
        else:
            self.index_manager = IndexManager(
                state_file=os.path.join(config.CHROMA_PERSIST_DIR, "index_state.json")
            )

        # 引用核查
        self.citation_verifier = CitationVerifier(
            llm_client=self.llm_client,
            threshold=getattr(config, 'CITATION_CONFIDENCE_THRESHOLD', 0.5)
        )
        self._citation_verify_enabled = getattr(config, 'CITATION_VERIFY_ENABLED', True)

        # 低置信度二次检索
        self.confidence_evaluator = ConfidenceEvaluator(
            threshold=config.SIMILARITY_THRESHOLD,
            min_docs=2
        )
        self._refetch_enabled = getattr(config, 'RETRIEVAL_REFETCH_ENABLED', True)

        logger.info("RAGEngine initialized in factory mode")

    def _rebuild_bm25_index(self):
        """从向量库重建 BM25 索引（后台线程调用）"""
        try:
            docs = self.vector_store.get_all_documents()
            if docs:
                with self._bm25_lock:
                    self.bm25_retriever.build_index(docs)  # build_index 内部会自动 save
                logger.info("BM25 index rebuilt: %d documents", len(docs))
            else:
                logger.info("Vector store is empty, BM25 index not built")
        except Exception as e:
            logger.warning("Failed to rebuild BM25 index: %s", e)
        finally:
            self._bm25_ready = True

    def close(self):
        """关闭引擎，释放资源（数据库连接池等）"""
        try:
            if hasattr(self.vector_store, 'close'):
                self.vector_store.close()
            if hasattr(self.index_manager, 'close'):
                self.index_manager.close()
            logger.info("RAGEngine closed")
        except Exception as e:
            logger.warning("Error closing RAGEngine: %s", e)

    def _init_ocr_provider(self, config):
        """初始化 OCR 提供者"""
        ocr_type = config.OCR_PROVIDER.lower()
        if ocr_type == "none":
            logger.info("OCR disabled by config")
            return None

        if ocr_type == "paddle":
            try:
                provider = PaddleOCRProvider(
                    lang=config.OCR_LANG,
                    use_gpu=config.OCR_USE_GPU
                )
                logger.info("PaddleOCR provider initialized")
                return provider
            except Exception as e:
                logger.warning("Failed to init PaddleOCR: %s", e)
                return None

        elif ocr_type == "tesseract":
            try:
                provider = TesseractOCRProvider(lang="chi_sim+eng")
                logger.info("TesseractOCR provider initialized")
                return provider
            except Exception as e:
                logger.warning("Failed to init TesseractOCR: %s", e)
                return None

        logger.warning("Unknown OCR_PROVIDER: %s", ocr_type)
        return None

    def _init_vlm_provider(self, config):
        """初始化 VLM 提供者"""
        if not config.USE_VLM:
            logger.info("VLM disabled by config")
            return None

        if not config.VLM_MODEL or not config.VLM_API_BASE:
            logger.warning("VLM_MODEL or VLM_API_BASE not configured")
            return None

        try:
            provider = VLMProvider(
                api_key=config.MIMO_API_KEY,
                api_base=config.VLM_API_BASE,
                model=config.VLM_MODEL
            )
            logger.info("VLM provider initialized (model=%s)", config.VLM_MODEL)
            return provider
        except Exception as e:
            logger.warning("Failed to init VLM: %s", e)
            return None

    def _build_file_reader_registry(self, ocr_provider, vlm_provider) -> dict:
        """构建文件读取器注册表

        Args:
            ocr_provider: OCR 提供者实例
            vlm_provider: VLM 提供者实例

        Returns:
            {extension: reader_instance} 映射
        """
        from core.providers.readers import (
            EnhancedPDFReader, MarkdownReader, DocxReader, HtmlReader, ImageReader
        )
        readers = [
            EnhancedPDFReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
            MarkdownReader(),
            DocxReader(),
            HtmlReader(),
            ImageReader(ocr_provider=ocr_provider, vlm_provider=vlm_provider),
        ]
        registry = {}
        for reader in readers:
            for ext in reader.supported_extensions():
                registry[ext] = reader
        logger.info("File reader registry built: %s", list(registry.keys()))
        return registry

    def _wait_bm25_ready(self, timeout: float = 30.0):
        """等待 BM25 索引就绪（带超时）"""
        if self._bm25_ready:
            return
        deadline = time.time() + timeout
        while not self._bm25_ready and time.time() < deadline:
            time.sleep(0.1)
        if not self._bm25_ready:
            logger.warning("BM25 index not ready after %.1fs, proceeding without it", timeout)

    @staticmethod
    def _normalize_query(query: str) -> str:
        """归一化查询：去标点、小写、去空白，用于缓存 key 去重"""
        q = query.lower().strip()
        q = re.sub(r'[？?。.！!，,；;：:"""\'\s]+', '', q)
        return q

    # 非文档查询的快速识别模式（命中后跳过 RAG 管线）
    _GREETING_RE = re.compile(
        r'^(你好|hi|hello|hey|嗨|哈喽|您好|早上好|下午好|晚上好|在吗|在不在'
        r'|谢谢|感谢|thanks|thank|ok|好的|明白了|收到|再见|拜拜|bye)',
        re.IGNORECASE,
    )

    @classmethod
    def _is_non_document_query(cls, query: str) -> bool:
        """判断是否为非文档查询（问候/致谢/极短无意义），跳过 RAG 管线"""
        q = query.strip()
        # 问候/致谢/告别
        if cls._GREETING_RE.match(q):
            return True
        # 极短消息（≤3 字符且不含技术关键词）
        if len(q) <= 3 and not any(c in q for c in '.()[]{}=<>_'):
            return True
        return False

    def _classify_and_expand(self, query: str) -> tuple:
        """并行执行意图分类 + HyDE + Multi-Query

        Returns:
            (intent, hyde_doc, queries)
        """
        with ThreadPoolExecutor(max_workers=3) as executor:
            intent_f = executor.submit(self.classifier.classify, query)
            hyde_f = executor.submit(
                self.hyde_generator.generate_hypothetical_document, query, None
            )
            mq_f = executor.submit(
                self.multi_query_generator.generate_queries, query, self.multi_query_count
            )

            try:
                intent = intent_f.result()
            except Exception as e:
                logger.warning("Classifier failed: %s", e)
                intent = {"intent_type": "factoid", "confidence": 0.5, "complexity": "medium"}

            try:
                hyde_doc = hyde_f.result()
            except Exception as e:
                logger.warning("HyDE failed: %s", e)
                hyde_doc = None

            try:
                queries = mq_f.result()
            except Exception as e:
                logger.warning("Multi-query failed: %s", e)
                queries = [query]

        return intent, hyde_doc, queries

    def _do_retrieve(self, search_queries: list, query: str,
                     vector_weight: float, bm25_weight: float,
                     retrieve_top_k: int) -> dict:
        """执行检索 → RRF 融合 → 去重 → 重排序（同步核心逻辑）"""
        t0 = time.time()
        all_vector_results = []
        all_bm25_results = []

        # 批量编码 + 向量/BM25 并行检索
        with ThreadPoolExecutor(max_workers=2) as executor:
            def vector_search():
                results = []
                embeddings = self.embedding_service.encode(search_queries)
                for q_text, emb in zip(search_queries, embeddings):
                    try:
                        raw = self.vector_store.query(emb, self.bm25_top_k)
                        for doc, meta, dist in zip(
                            raw["documents"], raw["metadatas"], raw["distances"]
                        ):
                            results.append({
                                "id": f"vec_{hashlib.sha256(doc.encode('utf-8')).hexdigest()[:16]}",
                                "text": doc, "metadata": meta, "distance": dist,
                            })
                    except Exception as e:
                        logger.warning("Vector retrieval failed for '%s': %s", q_text[:30], e)
                return results

            def bm25_search():
                results = []
                for q_text in search_queries:
                    try:
                        for r in self.bm25_retriever.search(q_text, self.bm25_top_k):
                            results.append({
                                "id": r["id"], "text": r["text"], "metadata": r["metadata"],
                            })
                    except Exception as e:
                        logger.warning("BM25 retrieval failed for '%s': %s", q_text[:30], e)
                return results

            vec_f = executor.submit(vector_search)
            bm25_f = executor.submit(bm25_search)
            all_vector_results = vec_f.result()
            all_bm25_results = bm25_f.result()

        t_search = time.time()
        logger.debug("Retrieval: %.0fms (queries=%d, vec=%d, bm25=%d)",
                      (t_search - t0) * 1000, len(search_queries),
                      len(all_vector_results), len(all_bm25_results))

        # RRF 融合
        fused = self.reciprocal_rank_fusion(
            [all_vector_results, all_bm25_results],
            weights=[vector_weight, bm25_weight],
            k=self.rrf_k,
        )

        # Chunk 级去重（同文档最多 2 个 chunk，而非仅 1 个）
        source_counts = Counter()
        deduplicated = []
        for doc in fused:
            src = doc["metadata"].get("source", "")
            if source_counts[src] < 2:
                deduplicated.append(doc)
                source_counts[src] += 1

        # 重排序
        try:
            reranked = self.rerank_manager.rerank(query, deduplicated, top_k=retrieve_top_k)
        except Exception as e:
            logger.warning("Reranking failed: %s", e)
            reranked = deduplicated[:retrieve_top_k]

        t_rerank = time.time()
        logger.debug("Rerank: %.0fms, total: %.0fms",
                      (t_rerank - t_search) * 1000, (t_rerank - t0) * 1000)

        top_docs = reranked[: self.top_k]
        return {
            "documents": [d["text"] for d in top_docs],
            "metadatas": [d["metadata"] for d in top_docs],
            "distances": [d.get("distance", d.get("rerank_score", 0.0)) for d in top_docs],
        }

    def ingest_document(self, file_path: str) -> int:
        """导入文档，返回 chunk 数量

        Args:
            file_path: 文档文件路径

        Returns:
            处理的 chunk 数量
        """
        source = os.path.basename(file_path)
        chunks, precomputed_embeddings = self.document_processor.process_file(file_path)

        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # 复用语义分块时的 embedding（均值池化），仅编码缺失部分
        embeddings: list[list[float]] = []
        missing_idx: list[int] = []
        for i, emb in enumerate(precomputed_embeddings):
            if emb is not None:
                embeddings.append(emb)
            else:
                embeddings.append([])  # 占位
                missing_idx.append(i)

        if missing_idx:
            missing_texts = [texts[i] for i in missing_idx]
            missing_embs = self.embedding_service.encode(missing_texts)
            for i, emb in zip(missing_idx, missing_embs):
                embeddings[i] = emb

        # 写入向量库
        self.vector_store.add_documents(texts, embeddings, metadatas)

        # 写入 BM25 索引
        doc_ids = [str(uuid.uuid4()) for _ in range(len(texts))]
        bm25_docs = [
            {"id": doc_id, "text": text, "metadata": meta}
            for doc_id, text, meta in zip(doc_ids, texts, metadatas)
        ]
        self.bm25_retriever.add_documents(bm25_docs)

        return len(chunks)

    def retrieve(self, query: str, top_k: int = None) -> dict:
        """检索相关文档（混合检索）

        Args:
            query: 用户查询
            top_k: 未使用，保留接口兼容

        Returns:
            检索结果
        """
        return self.hybrid_retrieve(query)

    def full_retrieve(self, query: str) -> dict:
        """完整检索管道（同步版本，兼容 query_stream）

        策略：先分类，再根据意图决定是否跑 HyDE+MQ。
        """
        # 快速短路：非文档查询直接返回空
        if self._is_non_document_query(query):
            return {"documents": [], "metadatas": [], "distances": []}

        t_total = time.time()
        self._wait_bm25_ready()

        # 1. 归一化缓存 key
        cache_key = f"rag:{hashlib.md5(self._normalize_query(query).encode()).hexdigest()}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for: %s", query[:50])
            return cached

        # 2. 先分类（仅 1 次 LLM）
        try:
            intent = self.classifier.classify(query)
        except Exception as e:
            logger.warning("Classifier failed: %s", e)
            intent = {"intent_type": "factoid", "confidence": 0.5, "complexity": "medium"}

        # 3. 根据路由决定是否需要 HyDE / Multi-Query
        route_config = self.router.route(query, intent)
        need_hyde = self.use_hyde and route_config.get("use_hyde", False)
        need_mq = self.multi_query_enabled and route_config.get("num_queries", 1) > 1

        hyde_doc = None
        queries = [query]

        if need_hyde or need_mq:
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                if need_hyde:
                    futures["hyde"] = executor.submit(
                        self.hyde_generator.generate_hypothetical_document,
                        query, intent.get("intent_type")
                    )
                if need_mq:
                    num_queries = route_config.get("num_queries", self.multi_query_count)
                    futures["mq"] = executor.submit(
                        self.multi_query_generator.generate_queries, query, num_queries
                    )

                for key, fut in futures.items():
                    try:
                        result = fut.result()
                        if key == "hyde":
                            hyde_doc = result
                        elif key == "mq":
                            queries = result
                    except Exception as e:
                        logger.warning("%s failed: %s", key, e)

        # 4. 路由参数（复用步骤 3 的 route_config）
        vector_weight = route_config.get("weights", {}).get("vector", self.rrf_weight_vector)
        bm25_weight = route_config.get("weights", {}).get("bm25", self.rrf_weight_bm25)
        retrieve_top_k = route_config.get("rerank_top_k", self.rerank_top_k)

        # 5. 构建搜索查询
        search_queries = list(queries)
        if hyde_doc:
            search_queries.append(hyde_doc)

        # 6. 检索 + 融合 + 重排序
        result = self._do_retrieve(search_queries, query, vector_weight, bm25_weight, retrieve_top_k)

        # 6.5 置信度评估 + 二次检索
        if self._refetch_enabled:
            eval_result = self.confidence_evaluator.evaluate(result)
            if eval_result["needs_refetch"]:
                logger.info("Low confidence (%.2f), refetching: %s",
                            eval_result["confidence"], eval_result["reason"])
                # 扩大检索参数
                expanded_top_k = eval_result["suggested_top_k"]
                # 生成更多查询变体
                try:
                    extra_queries = self.multi_query_generator.generate_queries(query, 5)
                    expanded_search_queries = list(set(search_queries + extra_queries))
                except Exception as e:
                    logger.warning("Extra query generation failed: %s", e)
                    expanded_search_queries = search_queries

                # 二次检索（加重 BM25 权重，关键词匹配更宽松）
                refetch_result = self._do_retrieve(
                    expanded_search_queries, query,
                    vector_weight * 0.5, bm25_weight * 1.5,
                    expanded_top_k
                )
                # 合并结果（去重）
                result = self.confidence_evaluator.merge_results(result, refetch_result)
                logger.info("Refetch merged: %d documents", len(result["documents"]))

        # 7. 写入缓存
        try:
            self.cache_manager.set(cache_key, result)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

        logger.debug("full_retrieve total: %.0fms", (time.time() - t_total) * 1000)
        return result

    async def full_retrieve_async(self, query: str) -> dict:
        """完整检索管道（异步版本，供 chat.py 使用）

        策略：先分类(1次LLM)，再根据意图决定是否并行跑 HyDE+MQ。
        简单事实型只花 1 次 LLM，复杂问题才跑满 3 次。
        """
        # 快速短路：非文档查询直接返回空
        if self._is_non_document_query(query):
            return {"documents": [], "metadatas": [], "distances": []}

        t_total = time.time()
        self._wait_bm25_ready()

        # 1. 归一化缓存 key
        cache_key = f"rag:{hashlib.md5(self._normalize_query(query).encode()).hexdigest()}"
        cached = self.cache_manager.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for: %s", query[:50])
            return cached

        # 2. 先分类（仅 1 次 LLM）
        try:
            intent = await asyncio.to_thread(self.classifier.classify, query)
        except Exception as e:
            logger.warning("Classifier failed: %s", e)
            intent = {"intent_type": "factoid", "confidence": 0.5, "complexity": "medium"}

        t_classify = time.time()
        logger.debug("Classify: %.0fms, intent=%s/%s",
                      (t_classify - t_total) * 1000,
                      intent.get("intent_type"), intent.get("complexity"))

        # 3. 根据路由决定是否需要 HyDE / Multi-Query
        route_config = self.router.route(query, intent)
        need_hyde = self.use_hyde and route_config.get("use_hyde", False)
        need_mq = self.multi_query_enabled and route_config.get("num_queries", 1) > 1

        hyde_doc = None
        queries = [query]

        if need_hyde or need_mq:
            # 只跑需要的部分，仍然并行
            tasks = {}
            if need_hyde:
                tasks["hyde"] = asyncio.to_thread(
                    self.hyde_generator.generate_hypothetical_document, query,
                    intent.get("intent_type")
                )
            if need_mq:
                num_queries = route_config.get("num_queries", self.multi_query_count)
                tasks["mq"] = asyncio.to_thread(
                    self.multi_query_generator.generate_queries, query, num_queries
                )

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), results):
                if key == "hyde":
                    hyde_doc = result if not isinstance(result, Exception) else None
                    if isinstance(result, Exception):
                        logger.warning("HyDE failed: %s", result)
                elif key == "mq":
                    queries = result if not isinstance(result, Exception) else [query]
                    if isinstance(result, Exception):
                        logger.warning("Multi-query failed: %s", result)

            logger.debug("HyDE+MQ: %.0fms (hyde=%s, mq=%s)",
                          (time.time() - t_classify) * 1000, need_hyde, need_mq)

        # 4. 路由参数
        vector_weight = route_config.get("weights", {}).get("vector", self.rrf_weight_vector)
        bm25_weight = route_config.get("weights", {}).get("bm25", self.rrf_weight_bm25)
        retrieve_top_k = route_config.get("rerank_top_k", self.rerank_top_k)

        # 5. 构建搜索查询
        search_queries = list(queries)
        if hyde_doc:
            search_queries.append(hyde_doc)

        # 6. 检索（在线程池中执行）
        result = await asyncio.to_thread(
            self._do_retrieve, search_queries, query,
            vector_weight, bm25_weight, retrieve_top_k
        )

        # 6.5 置信度评估 + 二次检索
        if self._refetch_enabled:
            eval_result = self.confidence_evaluator.evaluate(result)
            if eval_result["needs_refetch"]:
                logger.info("Low confidence (%.2f), refetching: %s",
                            eval_result["confidence"], eval_result["reason"])
                # 扩大检索参数
                expanded_top_k = eval_result["suggested_top_k"]
                # 生成更多查询变体
                try:
                    extra_queries = await asyncio.to_thread(
                        self.multi_query_generator.generate_queries, query, 5
                    )
                    expanded_search_queries = list(set(search_queries + extra_queries))
                except Exception as e:
                    logger.warning("Extra query generation failed: %s", e)
                    expanded_search_queries = search_queries

                # 二次检索（加重 BM25 权重）
                refetch_result = await asyncio.to_thread(
                    self._do_retrieve, expanded_search_queries, query,
                    vector_weight * 0.5, bm25_weight * 1.5,
                    expanded_top_k
                )
                # 合并结果
                result = self.confidence_evaluator.merge_results(result, refetch_result)
                logger.info("Refetch merged: %d documents", len(result["documents"]))

        # 7. 写入缓存
        try:
            self.cache_manager.set(cache_key, result)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

        logger.debug("full_retrieve_async total: %.0fms", (time.time() - t_total) * 1000)
        return result

    def filter_by_similarity(self, results: dict, threshold: float) -> dict:
        """按相似度过滤结果

        Args:
            results: 原始检索结果
            threshold: 相似度阈值

        Returns:
            过滤后的结果
        """
        if not results["distances"]:
            return results

        filtered_docs = []
        filtered_metas = []
        filtered_dists = []

        for doc, meta, dist in zip(
            results["documents"],
            results["metadatas"],
            results["distances"]
        ):
            similarity = 1 - dist
            if similarity >= threshold:
                filtered_docs.append(doc)
                filtered_metas.append(meta)
                filtered_dists.append(dist)

        return {
            "documents": filtered_docs,
            "metadatas": filtered_metas,
            "distances": filtered_dists
        }

    def reciprocal_rank_fusion(
        self,
        results_list: list[list[dict]],
        weights: list[float],
        k: int
    ) -> list[dict]:
        """加权 RRF 融合多路召回结果

        Args:
            results_list: 多路召回结果，每路为 [{"id": str, ...}, ...]
            weights: 每路的权重
            k: RRF 常数

        Returns:
            融合后的排序结果
        """
        score_map = {}  # id -> (total_score, doc_dict)

        for weight, results in zip(weights, results_list):
            for rank, doc in enumerate(results):
                doc_id = doc["id"]
                rrf_score = weight / (k + rank + 1)

                if doc_id in score_map:
                    score_map[doc_id] = (
                        score_map[doc_id][0] + rrf_score,
                        score_map[doc_id][1],
                    )
                else:
                    score_map[doc_id] = (rrf_score, doc)

        sorted_docs = sorted(score_map.values(), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in sorted_docs]

    def hybrid_retrieve(self, query: str) -> dict:
        """混合检索：向量 + BM25，RRF 融合

        Args:
            query: 用户查询

        Returns:
            检索结果，格式与原 retrieve 一致
        """
        # 0. 等待 BM25 就绪
        self._wait_bm25_ready()
        # 1. 向量检索
        query_embedding = self.embedding_service.encode_single(query)
        vector_raw = self.vector_store.query(query_embedding, self.bm25_top_k)

        # 将向量结果转为统一格式
        vector_results = []
        for doc, meta, dist in zip(
            vector_raw["documents"],
            vector_raw["metadatas"],
            vector_raw["distances"],
        ):
            vector_results.append({
                "id": f"vec_{hashlib.sha256(doc.encode('utf-8')).hexdigest()[:16]}",  # 用内容 hash 作为 id
                "text": doc,
                "metadata": meta,
                "distance": dist,
            })

        # 2. BM25 检索
        bm25_raw = self.bm25_retriever.search(query, self.bm25_top_k)
        bm25_results = [
            {"id": r["id"], "text": r["text"], "metadata": r["metadata"]}
            for r in bm25_raw
        ]

        # 3. 加权 RRF 融合
        fused = self.reciprocal_rank_fusion(
            [vector_results, bm25_results],
            weights=[self.rrf_weight_vector, self.rrf_weight_bm25],
            k=self.rrf_k
        )

        # 4. 按 source 去重，每个文档只保留最高分的 chunk
        seen_sources = set()
        deduplicated = []
        for doc in fused:
            source = doc["metadata"].get("source", "")
            if source not in seen_sources:
                seen_sources.add(source)
                deduplicated.append(doc)

        # 5. 取 top_k，转换为 retrieve 返回格式
        top_docs = deduplicated[: self.top_k]
        return {
            "documents": [d["text"] for d in top_docs],
            "metadatas": [d["metadata"] for d in top_docs],
            "distances": [d.get("distance", 0.0) for d in top_docs],
        }

    def build_prompt(self, query: str, contexts: list[dict], history: list[dict] = None) -> str:
        """构建 Prompt

        Args:
            query: 用户问题
            contexts: 检索到的上下文
            history: 对话历史 [{role, content}, ...]，由调用方传入

        Returns:
            完整的 Prompt
        """
        context_parts = []
        for i, ctx in enumerate(contexts, 1):
            source = ctx["metadata"]["source"]
            section = ctx["metadata"]["section"]
            context_parts.append(f"[来源 {i}: {source} - {section}]\n{ctx['text']}")

        context_str = "\n\n".join(context_parts)

        history_str = ""
        if history:
            history_lines = []
            for msg in history:
                role = "用户" if msg["role"] == "user" else "助手"
                history_lines.append(f"{role}: {msg['content']}")
            history_str = "\n".join(history_lines)

        prompt = f"""你是一个知识库文档问答助手。请基于以下参考文档内容回答用户问题。

要求：
1. 仅基于提供的文档内容回答，不要编造信息
2. 如果文档中没有相关信息，请明确说明"文档中未找到相关信息"
3. 回答要准确、简洁，必要时引用代码示例
4. 在回答末尾标注引用的文档来源
5. 结合对话历史理解上下文，避免重复已说明的内容

---参考文档---
{context_str}
"""

        if history_str:
            prompt += f"""
---对话历史---
{history_str}
"""

        prompt += f"""
---用户问题---
{query}"""

        return prompt

    def query_stream(self, question: str, history: list[dict] = None) -> Generator[dict, None, None]:
        """流式查询，返回 {answer_chunk, sources, verification}

        Args:
            question: 用户问题
            history: 对话历史 [{role, content}, ...]

        Yields:
            包含 answer_chunk、sources 和 verification 的字典
        """
        results = self.full_retrieve(question)

        # 将 results 转换为 contexts 格式
        contexts = []
        for doc, meta in zip(results["documents"], results["metadatas"]):
            contexts.append({
                "text": doc,
                "metadata": meta
            })

        prompt = self.build_prompt(question, contexts, history=history)

        sources = []
        for ctx in contexts:
            sources.append({
                "source": ctx["metadata"]["source"],
                "section": ctx["metadata"]["section"],
                "text": ctx["text"][:200] + "..." if len(ctx["text"]) > 200 else ctx["text"]
            })

        full_answer = ""
        for chunk in self.llm_client.stream_generate(prompt):
            full_answer += chunk
            yield {
                "answer_chunk": chunk,
                "full_answer": full_answer,
                "sources": sources
            }

        # 流式结束后进行引用核查
        verification = None
        if self._citation_verify_enabled and contexts and full_answer.strip():
            try:
                verification = self.citation_verifier.verify(question, full_answer, contexts)
                logger.info("Citation verification: confidence=%.2f, risk=%s",
                           verification["confidence"], verification["hallucination_risk"])
            except Exception as e:
                logger.warning("Citation verification failed: %s", e)

        # 最终结果包含 verification
        yield {
            "answer_chunk": "",
            "full_answer": full_answer,
            "sources": sources,
            "verification": verification,
            "done": True
        }

    def delete_by_source(self, source: str):
        """按来源删除文档（向量库 + BM25 + 缓存失效）"""
        self.vector_store.delete_by_source(source)
        self.bm25_retriever.delete_by_source(source)
        # 缓存失效
        self.cache_manager.invalidate_by_source(source)

    def delete_all(self):
        """清空所有文档"""
        self.vector_store.delete_all()
        self.bm25_retriever.delete_all()
        # 删除持久化文件
        if self.bm25_retriever.persist_path and os.path.exists(self.bm25_retriever.persist_path):
            os.remove(self.bm25_retriever.persist_path)
        # 清空缓存
        self.cache_manager.clear()

    def sync_index(self, data_dir: str) -> dict:
        """增量同步索引

        扫描 data_dir 目录，对比已索引文档的 Hash，
        只处理新增、修改、删除的文档。

        Args:
            data_dir: 数据目录路径

        Returns:
            {"added": int, "modified": int, "deleted": int, "unchanged": int}
        """
        changes = self.index_manager.detect_changes(data_dir)
        stats = {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "unchanged": len(changes["unchanged"])
        }

        # 处理删除
        for filename in changes["deleted"]:
            try:
                self.delete_by_source(filename)
                self.index_manager.remove_record(filename)
                stats["deleted"] += 1
                logger.info("Deleted from index: %s", filename)
            except Exception as e:
                logger.warning("Failed to delete %s: %s", filename, e)

        # 处理新增和修改
        for filename in changes["added"] + changes["modified"]:
            file_path = os.path.join(data_dir, filename)
            try:
                # 修改场景：先删旧的
                if filename in changes["modified"]:
                    self.delete_by_source(filename)

                # 索引新文档
                chunks = self.ingest_document(file_path)
                file_hash = IndexManager.compute_file_hash(file_path)
                self.index_manager.record_indexed(filename, file_hash, chunks)

                if filename in changes["added"]:
                    stats["added"] += 1
                    logger.info("Added to index: %s (%d chunks)", filename, chunks)
                else:
                    stats["modified"] += 1
                    logger.info("Updated index: %s (%d chunks)", filename, chunks)
            except Exception as e:
                logger.warning("Failed to index %s: %s", filename, e)

        logger.info("Sync completed: %s", stats)
        return stats

    def get_index_stats(self) -> dict:
        """获取索引统计信息"""
        return {
            "indexed_documents": self.index_manager.get_record_count(),
            "vector_count": self.vector_store.get_document_count(),
            "bm25_ready": self._bm25_ready,
        }
