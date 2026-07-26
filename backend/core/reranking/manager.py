import hashlib
import logging
from typing import Optional

from .base import RerankerProvider
from .cohere_reranker import CohereReranker
from .bge_reranker import BGEReranker
from .siliconflow_reranker import SiliconFlowReranker
from .dashscope_reranker import DashScopeReranker

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
        # 注意：RERANK_STRATEGY 每次调用 rerank 时会从 config 重新读取，
        # 以支持前端 Settings Drawer 的热更新；此处只保留首次启动时的值。
        self.strategy = config.RERANK_STRATEGY

        # 懒加载：首次使用时才创建对应 reranker 实例
        self._rerankers: dict[str, RerankerProvider | None] = {}

        logger.info("RerankManager initialized with strategy: %s", self.strategy)

    def _get_reranker(self, name: str) -> RerankerProvider | None:
        """按需创建并缓存 reranker 实例"""
        if name not in self._rerankers:
            if name == "cohere":
                self._rerankers[name] = CohereReranker(
                    api_key=self.config.COHERE_API_KEY,
                    model="rerank-multilingual-v3.0",
                )
            elif name == "bge":
                self._rerankers[name] = BGEReranker(
                    model_path=self.config.BGE_RERANKER_PATH,
                )
            elif name == "siliconflow":
                self._rerankers[name] = SiliconFlowReranker(
                    api_key=getattr(self.config, "SILICONFLOW_API_KEY", ""),
                    model=getattr(self.config, "SILICONFLOW_RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"),
                )
            elif name == "dashscope":
                self._rerankers[name] = DashScopeReranker(
                    api_key=getattr(self.config, "DASHSCOPE_API_KEY", ""),
                    model=getattr(self.config, "DASHSCOPE_RERANKER_MODEL", "gte-rerank"),
                )
            else:
                self._rerankers[name] = None
        return self._rerankers[name]

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

        # 支持热更新：重新从 config 读取当前策略
        current_strategy = self.config.RERANK_STRATEGY
        if current_strategy != self.strategy:
            logger.info("Rerank strategy updated: %s -> %s",
                        self.strategy, current_strategy)
            self.strategy = current_strategy

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
            reranker = self._get_reranker("cohere")
            if reranker and reranker.is_available():
                return reranker
            # 回退到BGE
            fallback = self._get_reranker("bge")
            if fallback and fallback.is_available():
                logger.info("Cohere not available, falling back to BGE")
                return fallback
            return None

        elif self.strategy == "bge":
            reranker = self._get_reranker("bge")
            if reranker and reranker.is_available():
                return reranker
            return None

        elif self.strategy == "hybrid":
            cohere = self._get_reranker("cohere")
            bge = self._get_reranker("bge")
            cohere_ok = cohere and cohere.is_available()
            bge_ok = bge and bge.is_available()
            if cohere_ok and bge_ok:
                return HybridReranker(cohere, bge)
            if cohere_ok:
                return cohere
            if bge_ok:
                return bge
            return None

        elif self.strategy == "siliconflow":
            reranker = self._get_reranker("siliconflow")
            if reranker and reranker.is_available():
                return reranker
            # 回退到 BGE 本地模型
            fallback = self._get_reranker("bge")
            if fallback and fallback.is_available():
                logger.info("SiliconFlow not available, falling back to BGE")
                return fallback
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

    @staticmethod
    def _doc_key(doc: dict) -> str:
        """生成稳定的文档标识，用于跨重排序器匹配合并"""
        text = doc.get("text", doc.get("content", ""))
        return hashlib.md5(text.encode()).hexdigest()

    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """混合重排序：按位置索引配对两个重排序器的分数并融合"""
        # 分别使用两个重排序器，传入副本避免修改原始列表
        cohere_results = self.cohere.rerank(query, documents.copy(), top_k=len(documents))
        bge_results = self.bge.rerank(query, documents.copy(), top_k=len(documents))

        # 按索引位置配对，避免同文本文档被错误合并
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
