import logging
from typing import Any

logger = logging.getLogger(__name__)


class MultiQueryGenerator:
    """多查询生成器：生成多个查询变体以提高召回率"""

    MULTI_QUERY_PROMPT = """请根据以下原始查询，生成{num_queries}个不同的查询变体。
这些变体应该表达相同的意图，但使用不同的表述方式。

原始查询：{original_query}

请生成{num_queries}个查询变体，每行一个，用数字编号：
1. """

    def __init__(self, llm_client: Any):
        """
        Args:
            llm_client: LLM客户端，需要有generate方法
        """
        self.llm_client = llm_client

    def generate_queries(self, original_query: str, num_queries: int = 3) -> list[str]:
        """
        生成多个查询变体

        Args:
            original_query: 原始查询
            num_queries: 生成的变体数量

        Returns:
            查询列表，第一个是原始查询，后续是生成的变体
        """
        # 生成prompt
        prompt = self.MULTI_QUERY_PROMPT.format(
            original_query=original_query,
            num_queries=num_queries
        )

        try:
            # 调用LLM
            response = self.llm_client.generate(prompt)

            # 解析结果
            variants = self._parse_queries(response, num_queries)

            # 返回：原始查询 + 变体
            return [original_query] + variants

        except Exception as e:
            logger.debug("Multi-query generation failed: %s", e)
            # 失败时只返回原始查询
            return [original_query]

    def _parse_queries(self, response: str, expected_count: int) -> list[str]:
        """
        解析LLM返回的查询列表

        Args:
            response: LLM响应文本
            expected_count: 期望的查询数量

        Returns:
            解析出的查询变体列表
        """
        if not response or not isinstance(response, str):
            return []

        queries = []

        for line in response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            # 移除编号（如 "1. ", "2. "等）
            if line[0].isdigit() and '. ' in line:
                line = line.split('. ', 1)[1]

            if line:
                queries.append(line)

        # 确保返回预期数量（或更少）
        return queries[:expected_count]
