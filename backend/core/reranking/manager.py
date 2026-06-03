import logging
from typing import Optional

from .base import RerankerProvider
from .cohere_reranker import CohereReranker
from .bge_reranker import BGEReranker

logger = logging.getLogger(__name__)


class RerankManager:
    """重排序管理器：策略选择和执行"""

    def __init__(self, config):
        """
        Args:
            config: 配置对象，需要包含:
                - RERANK_STRATEGY: str
                - COHERE_API_KEY: str
                - BGE_RERANKER_PATH: str
                - RERANK_TOP_K: int
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

        logger.info("RerankManager initialized with strategy: %s", self.strategy)

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
            logger.warning("No reranker available, returning original order")
            return documents[:top_k]

        # 执行重排序
        return reranker.rerank(query, documents, top_k)

    def _select_reranker(self) -> Optional[RerankerProvider]:
        """根据策略选择重排序器"""
        if self.strategy == "cohere":
            # 优先使用Cohere
            if self.cohere_reranker.is_available():
                return self.cohere_reranker
            # 回退到BGE
            elif self.bge_reranker.is_available():
                logger.info("Cohere not available, falling back to BGE")
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

        logger.warning("Unknown rerank strategy: %s", self.strategy)
        return None


class HybridReranker(RerankerProvider):
    """混合重排序器：结合Cohere和BGE分数"""

    def __init__(self, cohere_reranker, bge_reranker,
                 cohere_weight: float = 0.6, bge_weight: float = 0.4):
        """
        Args:
            cohere_reranker: Cohere重排序器实例
            bge_reranker: BGE重排序器实例
            cohere_weight: Cohere分数权重
            bge_weight: BGE分数权重

        Raises:
            ValueError: 如果权重之和不接近1.0
        """
        if abs(cohere_weight + bge_weight - 1.0) > 1e-6:
            raise ValueError(
                f"Weights must sum to 1.0, got {cohere_weight + bge_weight}"
            )
        self.cohere = cohere_reranker
        self.bge = bge_reranker
        self.cohere_weight = cohere_weight
        self.bge_weight = bge_weight

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """混合重排序"""
        # 分别使用两个重排序器，传入副本避免修改原始列表
        cohere_results = self.cohere.rerank(query, documents.copy(), top_k=len(documents))
        bge_results = self.bge.rerank(query, documents.copy(), top_k=len(documents))

        # 使用索引作为键，避免相同文本的文档互相覆盖
        score_map: dict[int, dict] = {}

        for i, doc in enumerate(cohere_results):
            score_map[i] = {
                "doc": doc,
                "cohere_score": doc.get("rerank_score", 0.0),
            }

        for i, doc in enumerate(bge_results):
            if i in score_map:
                score_map[i]["bge_score"] = doc.get("rerank_score", 0.0)
            else:
                score_map[i] = {
                    "doc": doc,
                    "bge_score": doc.get("rerank_score", 0.0),
                }

        # 计算混合分数（创建新字典而非修改原字典）
        reranked = []
        for data in score_map.values():
            cohere_score = data.get("cohere_score", 0.0)
            bge_score = data.get("bge_score", 0.0)
            new_doc = data["doc"].copy()
            new_doc["rerank_score"] = (
                self.cohere_weight * cohere_score +
                self.bge_weight * bge_score
            )
            reranked.append(new_doc)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

    def is_available(self) -> bool:
        """混合重排序器始终可用（依赖的子重排序器已在创建时验证）"""
        return True
