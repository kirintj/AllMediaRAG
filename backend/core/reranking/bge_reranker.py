import logging

from .base import RerankerProvider

logger = logging.getLogger(__name__)


class BGEReranker(RerankerProvider):
    """BGE Reranker 本地推理"""

    def __init__(self, model_path: str = "BAAI/bge-reranker-base"):
        """
        Args:
            model_path: 模型路径或HuggingFace模型ID
        """
        self.model_path = model_path
        self._model = None
        self._initialization_failed = False

    @property
    def model(self):
        """延迟加载模型"""
        if self._model is None and not self._initialization_failed:
            try:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_path, max_length=512)
                logger.debug("BGE reranker model loaded: %s", self.model_path)
            except Exception as e:
                logger.warning("Failed to load BGE reranker: %s", e)
                self._initialization_failed = True
        return self._model

    def rerank(
        self, query: str, documents: list[dict], top_k: int = 5
    ) -> list[dict]:
        """
        使用BGE模型进行重排序

        Args:
            query: 用户查询
            documents: 文档列表
            top_k: 返回数量

        Returns:
            重排序后的文档列表
        """
        if not self.is_available():
            logger.warning("BGE reranker not available, returning original order")
            return documents[:top_k]

        # 验证文档
        validated_docs = self._validate_documents(documents)

        if not validated_docs:
            return []

        # 构建query-doc对
        pairs = [[query, doc["text"]] for doc in validated_docs]

        try:
            # 预测相关性分数
            scores = self.model.predict(pairs)

            # 将分数附加到文档
            for doc, score in zip(validated_docs, scores):
                doc["rerank_score"] = float(score)

            # 按rerank_score降序排序
            reranked = sorted(
                validated_docs, key=lambda x: x["rerank_score"], reverse=True
            )

            logger.debug(
                "BGE rerank completed: %d documents -> %d results",
                len(pairs),
                len(reranked[:top_k]),
            )

            return reranked[:top_k]

        except Exception as e:
            logger.warning("BGE rerank failed: %s, returning original order", e)
            return documents[:top_k]

    def is_available(self) -> bool:
        """检查模型是否已加载"""
        return self.model is not None
