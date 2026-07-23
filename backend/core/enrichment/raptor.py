"""RAPTOR — 递归摘要树构建

与 RAGFlow 对齐：
- UMAP 降维
- GMM 聚类（BIC 选最优 K，软分配）
- 递归摘要树
- 小层折叠防退化
- 并行摘要 + Redis 缓存
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING

import numpy as np

from core.enrichment.prompt_loader import load_prompt

if TYPE_CHECKING:
    from core.models.llm_bundle import LLMBundle
    from core.enrichment.cache import LLMCache

logger = logging.getLogger(__name__)


class RAPTORProcessor:
    """递归摘要树构建器

    实现 RAPTOR 论文的核心流程：
    1. 对输入 chunks 做 embedding
    2. UMAP 降维
    3. GMM 聚类（BIC 自动选 K，软分配允许 chunk 属于多个簇）
    4. 对每个簇做 LLM 摘要，摘要作为新节点进入下一层
    5. 递归直到只剩一个节点或达到最大深度
    6. 小层折叠：剩余节点 <= small_layer_collapse 时直接合并摘要
    7. 防退化：n_clusters >= n_inputs 时强制合并为 1 个簇
    """

    def __init__(
        self,
        llm_bundle: LLMBundle,
        embedding_bundle: LLMBundle,
        cache: LLMCache,
        max_cluster: int = 64,
        threshold: float = 0.1,
        clustering_method: str = "gmm",
        small_layer_collapse: int = 8,
        max_errors: int = 3,
        max_depth: int = 3,
    ):
        self._llm = llm_bundle
        self._emb = embedding_bundle
        self._cache = cache
        self._max_cluster = max_cluster
        self._threshold = threshold
        self._clustering_method = clustering_method
        self._small_layer_collapse = small_layer_collapse
        self._max_errors = max_errors
        self._max_depth = max_depth
        self._error_count = 0

    def process(self, chunks: list[dict], source: str) -> list[dict]:
        """同步版本 — 构建 RAPTOR 树，返回所有层级的摘要节点

        Args:
            chunks: 输入文档块列表，每个 dict 至少包含 "text" 键
            source: 来源标识，写入摘要节点的 metadata

        Returns:
            所有层级产生的摘要节点列表（可用于写入向量库）
        """
        if len(chunks) < 3:
            return []
        return self._build_tree(chunks, source)

    async def process_async(self, chunks: list[dict], source: str) -> list[dict]:
        """异步版本 — 每层的簇摘要通过 asyncio.gather 并行执行

        Args:
            chunks: 输入文档块列表
            source: 来源标识

        Returns:
            所有层级产生的摘要节点列表
        """
        if len(chunks) < 3:
            return []
        return await self._build_tree_async(chunks, source)

    # ------------------------------------------------------------------
    # Tree building — sync
    # ------------------------------------------------------------------

    def _build_tree(self, chunks: list[dict], source: str) -> list[dict]:
        """经典 RAPTOR 树构建（同步）"""
        all_summaries: list[dict] = []
        current_chunks = list(chunks)
        depth = 0

        while len(current_chunks) > 1 and depth < self._max_depth:
            # 小层折叠：节点数不足时直接合并
            if len(current_chunks) <= self._small_layer_collapse:
                summary = self._summarize_cluster(current_chunks, source, depth, 0)
                if summary:
                    all_summaries.append(summary)
                break

            # Embedding（带缓存）
            embeddings = self._embed_with_cache(current_chunks)
            if not embeddings:
                break

            # UMAP 降维
            reduced = self._umap_reduce(np.array(embeddings))
            if reduced is None:
                break

            # 聚类
            labels = self._cluster(reduced)
            if not labels:
                break

            # 计算簇数量
            n_clusters = max(labels) + 1

            # 防退化：簇数 >= 节点数时强制合并为 1 个簇
            if n_clusters >= len(current_chunks):
                n_clusters = 1
                labels = [0] * len(current_chunks)

            # 每个簇做摘要
            level_summaries: list[dict] = []
            for c in range(n_clusters):
                if self._error_count >= self._max_errors:
                    logger.error(
                        "RAPTOR: too many errors (%d), aborting",
                        self._error_count,
                    )
                    break
                cluster_chunks = [
                    current_chunks[i]
                    for i in range(len(current_chunks))
                    if self._in_cluster(labels[i], c)
                ]
                if not cluster_chunks:
                    continue
                summary = self._summarize_cluster(cluster_chunks, source, depth, c)
                if summary:
                    level_summaries.append(summary)

            if not level_summaries:
                break

            all_summaries.extend(level_summaries)
            current_chunks = level_summaries
            depth += 1

        return all_summaries

    # ------------------------------------------------------------------
    # Tree building — async
    # ------------------------------------------------------------------

    async def _build_tree_async(self, chunks: list[dict], source: str) -> list[dict]:
        """异步版树构建 — 每层簇摘要并行执行"""
        all_summaries: list[dict] = []
        current_chunks = list(chunks)
        depth = 0

        while len(current_chunks) > 1 and depth < self._max_depth:
            # 小层折叠
            if len(current_chunks) <= self._small_layer_collapse:
                summary = await self._summarize_cluster_async(
                    current_chunks, source, depth, 0
                )
                if summary:
                    all_summaries.append(summary)
                break

            # Embedding（带缓存）
            embeddings = self._embed_with_cache(current_chunks)
            if not embeddings:
                break

            # UMAP 降维
            reduced = self._umap_reduce(np.array(embeddings))
            if reduced is None:
                break

            # 聚类
            labels = self._cluster(reduced)
            if not labels:
                break

            n_clusters = max(labels) + 1

            # 防退化
            if n_clusters >= len(current_chunks):
                n_clusters = 1
                labels = [0] * len(current_chunks)

            # 并行摘要
            tasks = []
            for c in range(n_clusters):
                if self._error_count >= self._max_errors:
                    logger.error(
                        "RAPTOR: too many errors (%d), aborting",
                        self._error_count,
                    )
                    break
                cluster_chunks = [
                    current_chunks[i]
                    for i in range(len(current_chunks))
                    if self._in_cluster(labels[i], c)
                ]
                if cluster_chunks:
                    tasks.append(
                        self._summarize_cluster_async(cluster_chunks, source, depth, c)
                    )

            results = await asyncio.gather(*tasks, return_exceptions=True)
            level_summaries = [r for r in results if isinstance(r, dict)]

            if not level_summaries:
                break

            all_summaries.extend(level_summaries)
            current_chunks = level_summaries
            depth += 1

        return all_summaries

    # ------------------------------------------------------------------
    # Embedding with cache
    # ------------------------------------------------------------------

    def _embed_with_cache(self, chunks: list[dict]) -> list[list[float]]:
        """对 chunks 做 embedding，优先从缓存读取

        Returns:
            embedding 向量列表；如果全部失败返回空列表
        """
        embeddings: list[list[float] | None] = []
        to_encode: list[str] = []
        to_encode_idx: list[int] = []

        for i, chunk in enumerate(chunks):
            cached = self._cache.get("embedding", chunk["text"][:500], "raptor")
            if cached:
                try:
                    embeddings.append(json.loads(cached))
                except (json.JSONDecodeError, TypeError):
                    embeddings.append(None)
                    to_encode.append(chunk["text"])
                    to_encode_idx.append(i)
            else:
                embeddings.append(None)
                to_encode.append(chunk["text"])
                to_encode_idx.append(i)

        if to_encode:
            try:
                new_embs = self._emb.encode(to_encode)
                for idx, emb in zip(to_encode_idx, new_embs):
                    embeddings[idx] = emb
                    self._cache.set(
                        "embedding",
                        chunks[idx]["text"][:500],
                        "raptor",
                        json.dumps(emb),
                    )
            except Exception as e:
                logger.error("RAPTOR embedding failed: %s", e)
                return []

        return [e for e in embeddings if e is not None]

    # ------------------------------------------------------------------
    # UMAP dimensionality reduction
    # ------------------------------------------------------------------

    def _umap_reduce(self, embeddings: np.ndarray) -> np.ndarray | None:
        """UMAP 降维，失败时回退到原始 embeddings"""
        n = len(embeddings)
        if n < 3:
            return embeddings
        try:
            import umap  # noqa: E402

            n_neighbors = min(int((n - 1) ** 0.8), 100)
            n_components = min(12, n - 2)
            if n_components < 2:
                n_components = 2
            reducer = umap.UMAP(
                n_neighbors=max(2, n_neighbors),
                n_components=n_components,
                metric="cosine",
                random_state=42,
            )
            return reducer.fit_transform(embeddings)
        except Exception as e:
            logger.warning("UMAP reduction failed: %s, using raw embeddings", e)
            return embeddings

    # ------------------------------------------------------------------
    # Clustering
    # ------------------------------------------------------------------

    def _cluster(self, embeddings: np.ndarray) -> list[int] | None:
        """根据 clustering_method 选择聚类算法"""
        if self._clustering_method == "ahc":
            return self._cluster_ahc(embeddings)
        return self._cluster_gmm(embeddings)

    def _cluster_gmm(self, embeddings: np.ndarray) -> list[int] | None:
        """GMM 聚类 + BIC 自动选最优 K + 软分配（取 argmax 做硬分配）"""
        from sklearn.mixture import GaussianMixture

        n = len(embeddings)
        max_k = min(self._max_cluster, n - 1)
        if max_k < 2:
            return [0] * n

        best_k, best_bic = 1, float("inf")
        for k in range(1, max_k + 1):
            try:
                gmm = GaussianMixture(
                    n_components=k,
                    covariance_type="diag",
                    reg_covar=1e-4,
                    random_state=42,
                )
                gmm.fit(embeddings)
                bic = gmm.bic(embeddings)
                if bic < best_bic:
                    best_bic = bic
                    best_k = k
            except Exception:
                continue

        gmm = GaussianMixture(
            n_components=best_k,
            covariance_type="diag",
            reg_covar=1e-4,
            random_state=42,
        )
        gmm.fit(embeddings)
        probs = gmm.predict_proba(embeddings)

        # 软分配：保留概率信息（用于 _in_cluster 判断），
        # 但树构建时展平为硬分配（取第一个高于阈值的簇，否则取 argmax）
        labels: list[int] = []
        for row in probs:
            assigned = [i for i, p in enumerate(row) if p > self._threshold]
            labels.append(assigned[0] if assigned else int(np.argmax(row)))

        return labels

    def _cluster_ahc(self, embeddings: np.ndarray) -> list[int] | None:
        """层次聚类 — 基于距离突变自动选簇数"""
        from sklearn.cluster import AgglomerativeClustering

        n = len(embeddings)
        if n < 2:
            return [0] * n
        try:
            clustering = AgglomerativeClustering(
                n_clusters=None, distance_threshold=0, linkage="ward"
            )
            clustering.fit(embeddings)
            distances = clustering.distances_
            max_gap_idx = int(np.argmax(np.diff(distances)))
            n_clusters = max(1, min(n - max_gap_idx - 1, self._max_cluster))
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters, linkage="ward"
            )
            return clustering.fit_predict(embeddings).tolist()
        except Exception as e:
            logger.warning("AHC clustering failed: %s", e)
            return [0] * n

    @staticmethod
    def _in_cluster(label, cluster_id: int) -> bool:
        """判断节点是否属于指定簇（兼容软分配列表和硬分配整数）"""
        if isinstance(label, list):
            return cluster_id in label
        return label == cluster_id

    # ------------------------------------------------------------------
    # Summarization
    # ------------------------------------------------------------------

    def _summarize_cluster(
        self,
        cluster_chunks: list[dict],
        source: str,
        depth: int,
        cluster_id: int,
    ) -> dict | None:
        """对一个簇的所有 chunks 调 LLM 做摘要（带缓存 + 错误计数）"""
        texts = "\n---\n".join(c["text"][:500] for c in cluster_chunks[:20])
        content_key = texts[:2000]

        # 查缓存
        cached = self._cache.get("chat", content_key, "raptor_summary")
        if cached:
            title, summary = self._parse_summary(cached)
            return self._make_summary_chunk(
                title, summary, source, depth, cluster_id, len(cluster_chunks)
            )

        # 调 LLM（3x 重试）
        prompt = load_prompt("raptor_summary_prompt.md", cluster_content=texts)
        result = self._llm_call_with_retry(prompt)
        if result is None:
            return None

        self._cache.set("chat", content_key, "raptor_summary", result)
        title, summary = self._parse_summary(result)
        return self._make_summary_chunk(
            title, summary, source, depth, cluster_id, len(cluster_chunks)
        )

    async def _summarize_cluster_async(
        self,
        cluster_chunks: list[dict],
        source: str,
        depth: int,
        cluster_id: int,
    ) -> dict | None:
        """异步版摘要 — 当前 LLMBundle.generate 是同步包装，用 run_in_executor 避免阻塞"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._summarize_cluster, cluster_chunks, source, depth, cluster_id
        )

    def _llm_call_with_retry(self, prompt: str, retries: int = 3) -> str | None:
        """带指数退避的 LLM 调用重试"""
        for attempt in range(retries):
            try:
                return self._llm.generate(prompt, max_tokens=512)
            except Exception as e:
                wait = 2 ** attempt
                self._error_count += 1
                logger.warning(
                    "RAPTOR summarization failed (attempt %d/%d, error %d/%d): %s",
                    attempt + 1,
                    retries,
                    self._error_count,
                    self._max_errors,
                    e,
                )
                if self._error_count >= self._max_errors:
                    logger.error(
                        "RAPTOR: max errors reached (%d), aborting",
                        self._error_count,
                    )
                    return None
                if attempt < retries - 1:
                    time.sleep(wait)
        return None

    def _parse_summary(self, text: str) -> tuple[str, str]:
        """第一行为标题，其余为摘要（与 RAGFlow 对齐）"""
        lines = text.strip().split("\n", 1)
        title = lines[0].strip()
        summary = lines[1].strip() if len(lines) > 1 else title
        return title, summary

    def _make_summary_chunk(
        self,
        title: str,
        summary: str,
        source: str,
        depth: int,
        cluster_id: int,
        child_count: int,
    ) -> dict:
        """构造摘要节点 dict"""
        return {
            "text": f"{title}\n{summary}",
            "metadata": {
                "source": source,
                "chunk_type": "raptor_summary",
                "raptor_level": depth + 1,
                "raptor_cluster": cluster_id,
                "child_count": child_count,
            },
        }
