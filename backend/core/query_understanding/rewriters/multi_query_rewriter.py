import logging
from typing import Any

from .base import QueryRewriter

logger = logging.getLogger(__name__)


class MultiQueryRewriter(QueryRewriter):
    """多查询改写器：生成多个查询变体"""

    def __init__(self, llm_client: Any, num_queries: int = 3):
        """
        Args:
            llm_client: LLM客户端，需要有generate方法
            num_queries: 每次生成的变体数量
        """
        from core.query_understanding.multi_query import MultiQueryGenerator
        self._generator = MultiQueryGenerator(llm_client)
        self._num_queries = num_queries

    @property
    def name(self) -> str:
        return "multi_query"

    def rewrite_sync(self, query: str, context: dict = None) -> list[str]:
        """生成多个查询变体

        Args:
            query: 用户查询
            context: 可选上下文，支持传入 num_queries 键覆盖默认数量

        Returns:
            查询变体列表（不含原始查询），失败时返回空列表
        """
        num = context.get("num_queries", self._num_queries) if context else self._num_queries
        try:
            all_queries = self._generator.generate_queries(query, num)
            # generate_queries 返回 [original_query] + variants，过滤掉原始查询
            return [q for q in all_queries if q != query]
        except Exception as e:
            logger.debug("MultiQuery rewriter failed: %s", e)
            return []
