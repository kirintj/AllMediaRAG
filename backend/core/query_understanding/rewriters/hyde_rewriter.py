import logging
from typing import Any, Optional

from .base import QueryRewriter

logger = logging.getLogger(__name__)


class HyDERewriter(QueryRewriter):
    """HyDE 查询改写器：将查询改写为假设性文档"""

    def __init__(self, llm_client: Any):
        """
        Args:
            llm_client: LLM客户端，需要有generate方法
        """
        from core.query_understanding.hyde_generator import HyDEGenerator
        self._generator = HyDEGenerator(llm_client)

    @property
    def name(self) -> str:
        return "hyde"

    def rewrite_sync(self, query: str, context: dict = None) -> list[str]:
        """生成假设性文档作为查询改写

        Args:
            query: 用户查询
            context: 可选上下文，支持传入 intent_type 键

        Returns:
            假设性文档列表（0或1个元素），失败时返回空列表
        """
        intent_type = context.get("intent_type") if context else None
        try:
            doc = self._generator.generate_hypothetical_document(query, intent_type)
            return [doc] if doc else []
        except Exception as e:
            logger.debug("HyDE rewriter failed: %s", e)
            return []
