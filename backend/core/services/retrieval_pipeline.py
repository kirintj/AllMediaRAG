"""Retrieval pipeline service extracted from RAGEngine.

Encapsulates all retrieval-related logic: BM25 waiting/rebuilding,
vector+BM25 hybrid retrieval with RRF fusion, reranking, caching,
confidence-based refetching, and similarity filtering.
"""

from __future__ import annotations

import re
import time
import hashlib
import logging
import asyncio
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

from core.observability.metrics_collector import metrics_collector
from core.providers.base import MatchTextExpr, MatchDenseExpr, FusionExpr


class RetrievalPipeline:
    """Pure retrieval pipeline -- no LLM generation, no document ingestion."""

    # Non-document query pattern (greetings / acknowledgements / short noise)
    _GREETING_RE = re.compile(
        r'^(你好|hi|hello|hey|嗨|哈喽|您好|早上好|下午好|晚上好|在吗|在不在'
        r'|谢谢|感谢|thanks|thank|ok|好的|明白了|收到|再见|拜拜|bye)',
        re.IGNORECASE,
    )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, infra: Any) -> None:
        """Initialise from an :class:`InfraBundle`.

        Reads all configuration values from ``infra.settings`` and
        stores references to the shared infrastructure components.
        """
        self.infra = infra
        config = infra.settings

        # Config-derived scalars (used by retrieval methods)
        self.top_k: int = config.TOP_K
        self.bm25_top_k: int = config.BM25_TOP_K
        self.similarity_threshold: float = config.SIMILARITY_THRESHOLD
        self.use_hyde: bool = config.USE_HYDE
        self.multi_query_enabled: bool = config.MULTI_QUERY_ENABLED
        self.multi_query_count: int = config.MULTI_QUERY_COUNT
        self.rerank_top_k: int = config.RERANK_TOP_K
        self.rerank_gate_threshold: float = getattr(config, "RERANK_GATE_THRESHOLD", 0.3)
        self._refetch_enabled: bool = getattr(config, "RETRIEVAL_REFETCH_ENABLED", True)

    def _ensure_tenant(self, tenant_id: str):
        """确保 ES store 使用正确的租户索引"""
        if hasattr(self.infra.vector_store, '_tenant_id'):
            if self.infra.vector_store._tenant_id != tenant_id:
                self.infra.vector_store._tenant_id = tenant_id
                self.infra.vector_store._ensure_index()
                logger.info("Retrieval: switched ES index to tenant: %s", tenant_id)

    # ------------------------------------------------------------------
    # Static / class helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalise query: strip punctuation, lowercase, collapse whitespace (cache key dedup)."""
        q = query.lower().strip()
        q = re.sub(r'[？?。.！!，,；;：:"""\'\s]+', '', q)
        return q

    @classmethod
    def _is_non_document_query(cls, query: str) -> bool:
        """Detect non-document queries (greetings / thanks / very short noise) to skip RAG."""
        q = query.strip()
        if cls._GREETING_RE.match(q):
            return True
        if len(q) <= 3 and not any(c in q for c in '.()[]{}=<>_'):
            return True
        return False

    # ------------------------------------------------------------------
    # Core retrieval (sync)
    # ------------------------------------------------------------------

    def _do_retrieve(self, search_queries: list, query: str,
                     vector_weight: float, bm25_weight: float,
                     retrieve_top_k: int) -> dict:
        """Execute retrieval via ES hybrid search -> rerank (sync core)."""
        t0 = time.time()

        doc_store = self.infra.vector_store

        # 对主查询做一次编码，用于向量检索
        primary_embedding = self.infra.embedding_service.encode([query])[0]

        # 构建表达式
        expressions = [
            MatchTextExpr(
                fields=["text"],
                matching_text=query,
                topn=self.bm25_top_k,
                extra_options={"minimum_should_match": "70%"},
            ),
            MatchDenseExpr(
                embedding_data=primary_embedding,
                topn=self.top_k,
            ),
            FusionExpr(
                method="weighted_sum",
                topn=retrieve_top_k,
                fusion_params={"weights": f"{bm25_weight},{vector_weight}"},
            ),
        ]

        # 单次 ES 混合检索
        try:
            raw = doc_store.search(
                select_fields=["id", "text_raw", "source", "metadata"],
                condition=None,
                match_expressions=expressions,
                limit=retrieve_top_k,
            )
        except Exception as e:
            logger.warning("ES hybrid search failed: %s", e)
            raw = {"documents": [], "metadatas": [], "distances": [], "total": 0}

        t_search = time.time()
        logger.debug("ES retrieval: %.0fms, hits=%d",
                      (t_search - t0) * 1000, raw.get("total", 0))

        # 转换为内部格式
        fused = []
        for doc, meta, dist in zip(raw["documents"], raw["metadatas"], raw["distances"]):
            fused.append({
                "id": meta.get("id", ""),
                "text": doc,
                "metadata": meta,
                "distance": dist,
            })

        # Graph candidate expansion（独立于 ES 检索）
        graph_retriever = getattr(self.infra, "graph_retriever", None)
        if graph_retriever:
            try:
                graph_chunk_ids = graph_retriever.search(query, max_chunks=self.top_k * 4)
                if graph_chunk_ids:
                    existing_ids = {d["id"] for d in fused}
                    for cid in graph_chunk_ids:
                        if any(cid in d.get("id", "") for d in fused):
                            continue
                        try:
                            doc = self.infra.vector_store.get(cid)
                            if doc:
                                fused.append({
                                    "id": f"graph_{cid}",
                                    "text": doc.get("text_raw", doc.get("text", "")),
                                    "metadata": {
                                        "source": doc.get("source", ""),
                                        "section": doc.get("metadata", {}).get("section", ""),
                                        "chunk_index": doc.get("metadata", {}).get("chunk_index", 0),
                                        "retrieval_source": "knowledge_graph",
                                    },
                                })
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Graph retrieval failed: %s", e)

        # Dedup: max 2 chunks per source
        from collections import Counter
        source_counts = Counter()
        deduplicated = []
        for doc in fused:
            src = doc["metadata"].get("source", "")
            if source_counts[src] < 2:
                deduplicated.append(doc)
                source_counts[src] += 1

        # Rerank
        try:
            reranked = self.infra.rerank_manager.rerank(query, deduplicated, top_k=retrieve_top_k)
        except Exception as e:
            logger.warning("Reranking failed: %s", e)
            reranked = deduplicated[:retrieve_top_k]

        t_rerank = time.time()

        # Relevance gating
        if reranked and len(reranked) > self.top_k:
            gated = [d for d in reranked
                     if d.get("rerank_score", 0) >= self.rerank_gate_threshold]
            if len(gated) >= self.top_k:
                logger.debug("Rerank gate: %d -> %d docs (threshold=%.2f)",
                             len(reranked), len(gated), self.rerank_gate_threshold)
                reranked = gated
            elif gated:
                logger.debug("Rerank gate: only %d passed (need %d), keeping top results",
                             len(gated), self.top_k)

        logger.debug("Rerank: %.0fms, total: %.0fms",
                      (t_rerank - t_search) * 1000, (t_rerank - t0) * 1000)

        metrics_collector.record_retrieval({
            "search_ms": (t_search - t0) * 1000,
            "rerank_ms": (t_rerank - t_search) * 1000,
            "total_ms": (t_rerank - t0) * 1000,
        })

        top_docs = reranked[: self.top_k]
        return {
            "documents": [d["text"] for d in top_docs],
            "metadatas": [d["metadata"] for d in top_docs],
            "distances": [d.get("distance", d.get("rerank_score", 0.0)) for d in top_docs],
            "reranked": True,
        }

    # ------------------------------------------------------------------
    # Full retrieval -- sync
    # ------------------------------------------------------------------

    def full_retrieve(self, query: str) -> dict:
        """Full retrieval pipeline (sync version, compatible with query_stream).

        Strategy: classify first, then decide whether to run HyDE+MQ.
        """
        # Fast short-circuit: non-document queries return empty
        if self._is_non_document_query(query):
            return {"documents": [], "metadatas": [], "distances": []}

        t_total = time.time()

        # 1. Normalised cache key
        cache_key = f"rag:{hashlib.md5(self._normalize_query(query).encode()).hexdigest()}"
        cached = self.infra.cache_manager.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for: %s", query[:50])
            return cached

        # 2. Classify (1 LLM call)
        try:
            intent = self.infra.classifier.classify(query)
        except Exception as e:
            logger.warning("Classifier failed: %s", e)
            intent = {"intent_type": "factoid", "confidence": 0.5, "complexity": "medium"}

        # 3. Route: decide whether HyDE / Multi-Query is needed
        route_config = self.infra.router.route(query, intent)
        need_hyde = self.use_hyde and route_config.get("use_hyde", False)
        need_mq = self.multi_query_enabled and route_config.get("num_queries", 1) > 1

        hyde_doc = None
        queries = [query]

        if need_hyde or need_mq:
            executor = self.infra.executor
            futures = {}
            if need_hyde and "hyde" in self.infra.rewriters:
                futures["hyde"] = executor.submit(
                    self.infra.rewriters["hyde"].rewrite_sync, query,
                    {"intent_type": intent.get("intent_type")}
                )
            if need_mq and "multi_query" in self.infra.rewriters:
                num_queries = route_config.get("num_queries", self.multi_query_count)
                futures["mq"] = executor.submit(
                    self.infra.rewriters["multi_query"].rewrite_sync, query,
                    {"num_queries": num_queries}
                )

            for key, fut in futures.items():
                try:
                    result = fut.result()
                    if key == "hyde":
                        hyde_doc = result[0] if result else None
                    elif key == "mq":
                        queries = [query] + result
                except Exception as e:
                    logger.warning("%s failed: %s", key, e)

        # 4. Route params (reuse step 3 route_config)
        vector_weight = route_config.get("weights", {}).get("vector", self.infra.settings.RRF_WEIGHT_VECTOR)
        bm25_weight = route_config.get("weights", {}).get("bm25", self.infra.settings.RRF_WEIGHT_BM25)
        retrieve_top_k = route_config.get("rerank_top_k", self.rerank_top_k)

        # 5. Build search queries
        search_queries = list(queries)
        if hyde_doc:
            search_queries.append(hyde_doc)

        # 6. Retrieve + fusion + rerank
        result = self._do_retrieve(search_queries, query, vector_weight, bm25_weight, retrieve_top_k)

        # 6.5 Confidence evaluation + refetch
        result = self._evaluate_and_refetch(
            result, query, search_queries, vector_weight, bm25_weight,
            retrieve_fn=self._do_retrieve,
        )

        # 7. Write to cache
        try:
            self.infra.cache_manager.set(cache_key, result)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

        logger.debug("full_retrieve total: %.0fms", (time.time() - t_total) * 1000)
        return result

    def _evaluate_and_refetch(
        self,
        result: dict,
        query: str,
        search_queries: list,
        vector_weight: float,
        bm25_weight: float,
        retrieve_fn,
    ) -> dict:
        """低置信度时扩展查询并重新检索，合并结果。

        为什么抽取为独立方法：
        full_retrieve 和 full_retrieve_async 中的 refetch 逻辑完全相同，
        唯一区别是 retrieve_fn 调用方式（同步 vs 通过 asyncio.to_thread 包装）。
        将检索函数作为参数注入，消除两个版本间约 30 行重复代码。

        Args:
            result: 初次检索结果
            query: 原始查询
            search_queries: 初次检索使用的查询列表
            vector_weight: 向量检索权重
            bm25_weight: BM25 检索权重
            retrieve_fn: 检索函数，签名 (queries, query, vec_w, bm25_w, top_k) -> dict
        """
        if not self._refetch_enabled:
            return result

        eval_result = self.infra.confidence_evaluator.evaluate(result)
        if not eval_result["needs_refetch"]:
            return result

        logger.info(
            "Low confidence (%.2f), refetching: %s",
            eval_result["confidence"], eval_result["reason"],
        )
        expanded_top_k = eval_result["suggested_top_k"]

        # 生成更多查询变体
        try:
            if "multi_query" in self.infra.rewriters:
                extra_variants = self.infra.rewriters["multi_query"].rewrite_sync(
                    query, {"num_queries": 5},
                )
                extra_queries = [query] + extra_variants
            else:
                extra_queries = search_queries
            expanded_search_queries = list(set(search_queries + extra_queries))
        except Exception as e:
            logger.warning("Extra query generation failed: %s", e)
            expanded_search_queries = search_queries

        # Refetch（加大 BM25 权重，放松关键词匹配）
        refetch_result = retrieve_fn(
            expanded_search_queries, query,
            vector_weight * 0.5, bm25_weight * 1.5,
            expanded_top_k,
        )
        result = self.infra.confidence_evaluator.merge_results(result, refetch_result)
        logger.info("Refetch merged: %d documents", len(result["documents"]))
        return result

        # 7. Write to cache
        try:
            self.infra.cache_manager.set(cache_key, result)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

        logger.debug("full_retrieve total: %.0fms", (time.time() - t_total) * 1000)
        return result

    # ------------------------------------------------------------------
    # Full retrieval -- async
    # ------------------------------------------------------------------

    async def full_retrieve_async(self, query: str) -> dict:
        """Full retrieval pipeline (async version, used by chat.py).

        Strategy: classify (1 LLM call), then conditionally run HyDE+MQ in
        parallel.  Simple factual queries only cost 1 LLM call; complex
        queries run the full 3-call path.
        """
        # Fast short-circuit: non-document queries return empty
        if self._is_non_document_query(query):
            return {"documents": [], "metadatas": [], "distances": []}

        t_total = time.time()

        # 1. Normalised cache key
        cache_key = f"rag:{hashlib.md5(self._normalize_query(query).encode()).hexdigest()}"
        cached = self.infra.cache_manager.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for: %s", query[:50])
            metrics_collector.record_cache_hit(True)
            return cached

        metrics_collector.record_cache_hit(False)

        # 2. Classify (1 LLM call)
        try:
            intent = await asyncio.to_thread(self.infra.classifier.classify, query)
        except Exception as e:
            logger.warning("Classifier failed: %s", e)
            intent = {"intent_type": "factoid", "confidence": 0.5, "complexity": "medium"}

        t_classify = time.time()
        logger.debug("Classify: %.0fms, intent=%s/%s",
                      (t_classify - t_total) * 1000,
                      intent.get("intent_type"), intent.get("complexity"))

        metrics_collector.record_retrieval({
            "classify_ms": (t_classify - t_total) * 1000,
        })

        # 3. Route: decide whether HyDE / Multi-Query is needed
        route_config = self.infra.router.route(query, intent)
        need_hyde = self.use_hyde and route_config.get("use_hyde", False)
        need_mq = self.multi_query_enabled and route_config.get("num_queries", 1) > 1

        hyde_doc = None
        queries = [query]

        if need_hyde or need_mq:
            # Only run what is needed, still in parallel
            tasks = {}
            if need_hyde and "hyde" in self.infra.rewriters:
                tasks["hyde"] = asyncio.to_thread(
                    self.infra.rewriters["hyde"].rewrite_sync, query,
                    {"intent_type": intent.get("intent_type")}
                )
            if need_mq and "multi_query" in self.infra.rewriters:
                num_queries = route_config.get("num_queries", self.multi_query_count)
                tasks["mq"] = asyncio.to_thread(
                    self.infra.rewriters["multi_query"].rewrite_sync, query,
                    {"num_queries": num_queries}
                )

            results = await asyncio.gather(*tasks.values(), return_exceptions=True)
            for key, result in zip(tasks.keys(), results):
                if key == "hyde":
                    if isinstance(result, Exception):
                        logger.warning("HyDE failed: %s", result)
                    else:
                        hyde_doc = result[0] if result else None
                elif key == "mq":
                    if isinstance(result, Exception):
                        logger.warning("Multi-query failed: %s", result)
                    else:
                        queries = [query] + result

            logger.debug("HyDE+MQ: %.0fms (hyde=%s, mq=%s)",
                          (time.time() - t_classify) * 1000, need_hyde, need_mq)

        # 4. Route params
        vector_weight = route_config.get("weights", {}).get("vector", self.infra.settings.RRF_WEIGHT_VECTOR)
        bm25_weight = route_config.get("weights", {}).get("bm25", self.infra.settings.RRF_WEIGHT_BM25)
        retrieve_top_k = route_config.get("rerank_top_k", self.rerank_top_k)

        # 5. Build search queries
        search_queries = list(queries)
        if hyde_doc:
            search_queries.append(hyde_doc)

        # 6. Retrieve (in thread pool)
        result = await asyncio.to_thread(
            self._do_retrieve, search_queries, query,
            vector_weight, bm25_weight, retrieve_top_k
        )

        # 6.5 Confidence evaluation + refetch（async 版本使用 to_thread 包装检索函数）
        async def _async_retrieve(queries, q, vw, bw, top_k):
            return await asyncio.to_thread(self._do_retrieve, queries, q, vw, bw, top_k)

        if self._refetch_enabled:
            eval_result = self.infra.confidence_evaluator.evaluate(result)
            if eval_result["needs_refetch"]:
                logger.info("Low confidence (%.2f), refetching: %s",
                            eval_result["confidence"], eval_result["reason"])
                expanded_top_k = eval_result["suggested_top_k"]
                try:
                    if "multi_query" in self.infra.rewriters:
                        extra_variants = await asyncio.to_thread(
                            self.infra.rewriters["multi_query"].rewrite_sync,
                            query, {"num_queries": 5}
                        )
                        extra_queries = [query] + extra_variants
                    else:
                        extra_queries = search_queries
                    expanded_search_queries = list(set(search_queries + extra_queries))
                except Exception as e:
                    logger.warning("Extra query generation failed: %s", e)
                    expanded_search_queries = search_queries

                refetch_result = await _async_retrieve(
                    expanded_search_queries, query,
                    vector_weight * 0.5, bm25_weight * 1.5,
                    expanded_top_k,
                )
                result = self.infra.confidence_evaluator.merge_results(result, refetch_result)
                logger.info("Refetch merged: %d documents", len(result["documents"]))

        # 7. Write to cache
        try:
            self.infra.cache_manager.set(cache_key, result)
        except Exception as e:
            logger.warning("Cache write failed: %s", e)

        logger.debug("full_retrieve_async total: %.0fms", (time.time() - t_total) * 1000)
        metrics_collector.record_request(True, (time.time() - t_total) * 1000)
        return result

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the shared thread pool executor."""
        try:
            if self.infra.executor is not None:
                self.infra.executor.shutdown(wait=False)
        except Exception as e:
            logger.warning("Error closing RetrievalPipeline executor: %s", e)
