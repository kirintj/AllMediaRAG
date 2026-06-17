import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConfidenceEvaluator:
    """检索置信度评估器：判断首次检索结果是否足够好

    当置信度低于阈值时，触发二次检索：
    - 扩大 top_k 检索范围
    - 生成更多查询变体
    - 调整 BM25/向量权重
    """

    def __init__(self, threshold: float = 0.5, min_docs: int = 2):
        """
        Args:
            threshold: 置信度阈值，低于此值触发二次检索
            min_docs: 最少相关文档数
        """
        self.threshold = threshold
        self.min_docs = min_docs

    def evaluate(self, results: dict) -> dict:
        """评估检索结果的置信度

        Args:
            results: {"documents": [...], "metadatas": [...], "distances": [...]}

        Returns:
            {
                "confidence": float,       # 综合置信度 0-1
                "needs_refetch": bool,     # 是否需要二次检索
                "reason": str,             # 原因说明
                "suggested_top_k": int,    # 建议的扩大 top_k
                "suggested_strategy": str  # 建议的策略调整
            }
        """
        if not results.get("documents"):
            return {
                "confidence": 0.0,
                "needs_refetch": True,
                "reason": "无检索结果",
                "suggested_top_k": 30,
                "suggested_strategy": "expand",
            }

        distances = results.get("distances", [])
        doc_count = len(results["documents"])
        reranked = results.get("reranked", False)

        if not distances:
            return {
                "confidence": 0.0,
                "needs_refetch": True,
                "reason": "无距离信息",
                "suggested_top_k": 30,
                "suggested_strategy": "expand",
            }

        # 根据是否经过重排序，正确解读分数
        # - 未重排序：distances 是向量距离，越小越相关
        # - 已重排序：distances 是 rerank_score，越大越相关
        avg_raw = sum(distances) / len(distances)

        if reranked:
            # rerank_score 已是相关度（越高越好），直接使用
            max_similarity = max(distances)
            min_similarity = min(distances)
            avg_similarity = avg_raw
        else:
            # 向量距离：distance = 1 - cosine_similarity
            max_similarity = max(1 - d for d in distances)
            min_similarity = min(1 - d for d in distances)
            avg_similarity = 1 - avg_raw

        # 文档数量因子
        count_factor = min(doc_count / self.min_docs, 1.0)

        # 分数方差（越小越稳定）
        if len(distances) > 1:
            variance = sum((d - avg_raw) ** 2 for d in distances) / len(distances)
            stability = max(0, 1 - variance * 10)  # 归一化
        else:
            stability = 0.5

        # 综合置信度计算
        # - 最高相似度权重 0.5
        # - 文档数量因子 0.2
        # - 平均相似度 0.2
        # - 稳定性 0.1
        confidence = (
            max_similarity * 0.5 +
            count_factor * 0.2 +
            avg_similarity * 0.2 +
            stability * 0.1
        )

        confidence = min(confidence, 1.0)

        # 判断是否需要二次检索
        needs_refetch = False
        reason = ""

        if max_similarity < self.threshold:
            needs_refetch = True
            reason = f"最高相似度 {max_similarity:.2f} 低于阈值 {self.threshold}"
        elif doc_count < self.min_docs:
            needs_refetch = True
            reason = f"文档数 {doc_count} 少于最少要求 {self.min_docs}"
        elif avg_similarity < self.threshold * 0.8:
            needs_refetch = True
            reason = f"平均相似度 {avg_similarity:.2f} 过低"

        # 计算建议的 top_k
        if needs_refetch:
            # 根据置信度动态调整扩展倍数
            expansion_factor = max(2, int(1 / max(confidence, 0.1)))
            suggested_top_k = min(30, doc_count * expansion_factor)
        else:
            suggested_top_k = doc_count

        return {
            "confidence": round(confidence, 3),
            "needs_refetch": needs_refetch,
            "reason": reason,
            "suggested_top_k": suggested_top_k,
            "suggested_strategy": "expand" if needs_refetch else "keep",
            "stats": {
                "max_similarity": round(max_similarity, 3),
                "min_similarity": round(min_similarity, 3),
                "avg_similarity": round(avg_similarity, 3),
                "doc_count": doc_count,
                "stability": round(stability, 3),
            }
        }

    def merge_results(self, result1: dict, result2: dict) -> dict:
        """合并两次检索结果并去重

        Args:
            result1: 第一次检索结果
            result2: 第二次检索结果

        Returns:
            合并后的结果
        """
        if not result1.get("documents"):
            return result2
        if not result2.get("documents"):
            return result1

        # 按文档内容去重
        seen_texts = set()
        merged_docs = []
        merged_metas = []
        merged_distances = []

        # 优先保留第一次的结果（通常更相关）
        for i, doc in enumerate(result1["documents"]):
            doc_hash = hash(doc[:100])  # 简单的去重
            if doc_hash not in seen_texts:
                seen_texts.add(doc_hash)
                merged_docs.append(doc)
                merged_metas.append(result1["metadatas"][i])
                if i < len(result1.get("distances", [])):
                    merged_distances.append(result1["distances"][i])

        # 添加第二次的结果
        for i, doc in enumerate(result2["documents"]):
            doc_hash = hash(doc[:100])
            if doc_hash not in seen_texts:
                seen_texts.add(doc_hash)
                merged_docs.append(doc)
                merged_metas.append(result2["metadatas"][i])
                if i < len(result2.get("distances", [])):
                    merged_distances.append(result2["distances"][i])

        return {
            "documents": merged_docs,
            "metadatas": merged_metas,
            "distances": merged_distances,
        }
