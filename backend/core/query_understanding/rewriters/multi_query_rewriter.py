import logging
from typing import Any

from .base import QueryRewriter

logger = logging.getLogger(__name__)


class MultiQueryRewriter(QueryRewriter):
    """多查询改写器：生成多个查询变体"""

    # 去重相似度阈值（Jaccard），高于此值视为重复
    DEDUP_THRESHOLD = 0.7

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
        """生成多个查询变体（去重后）

        Args:
            query: 用户查询
            context: 可选上下文，支持传入 num_queries 键覆盖默认数量

        Returns:
            去重后的查询变体列表（不含原始查询），失败时返回空列表
        """
        num = context.get("num_queries", self._num_queries) if context else self._num_queries
        try:
            # 多生成 50% 以弥补去重损耗
            extra = max(2, num // 2)
            all_queries = self._generator.generate_queries(query, num + extra)
            # 过滤掉原始查询
            variants = [q for q in all_queries if q != query]
            # 去重
            deduplicated = self._dedup(query, variants)
            return deduplicated[:num]
        except Exception as e:
            logger.debug("MultiQuery rewriter failed: %s", e)
            return []

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        """分词：英文按词，中文按字符（更适合短文本相似度比较）"""
        import re
        # 英文单词 + 中文单字（每个 CJK 字符作为独立 token）
        tokens = re.findall(r'[a-zA-Z0-9]+|[一-鿿]', text.lower())
        return set(tokens)

    @classmethod
    def _jaccard(cls, a: str, b: str) -> float:
        """计算两个字符串的 Jaccard 相似度"""
        tokens_a = cls._tokenize(a)
        tokens_b = cls._tokenize(b)
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    @classmethod
    def _dedup(cls, original: str, variants: list[str]) -> list[str]:
        """去重：移除与原始查询或已保留变体过于相似的查询"""
        if not variants:
            return []

        kept = []
        # 原始查询作为锚点
        reference_texts = [original]

        for v in variants:
            # 检查与所有已保留文本的相似度
            is_dup = False
            for ref in reference_texts:
                if cls._jaccard(v, ref) > cls.DEDUP_THRESHOLD:
                    is_dup = True
                    break
            if not is_dup:
                kept.append(v)
                reference_texts.append(v)

        return kept
