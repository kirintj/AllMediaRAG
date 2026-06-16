"""自定义评估指标集合"""


def hit_rate(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """至少命中一个相关文档返回 1.0，否则 0.0"""
    if not expected_sources:
        return 0.0
    return 1.0 if any(src in expected_sources for src in retrieved_sources) else 0.0


def recall_at_k(retrieved_sources: list[str], expected_sources: set[str], k: int = 5) -> float:
    """前 K 个结果中命中的相关文档比例"""
    if not expected_sources:
        return 0.0
    hits = sum(1 for src in retrieved_sources[:k] if src in expected_sources)
    return hits / len(expected_sources)


def mrr(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """第一个命中结果的排名倒数"""
    for i, src in enumerate(retrieved_sources):
        if src in expected_sources:
            return 1.0 / (i + 1)
    return 0.0


def precision(retrieved_sources: list[str], expected_sources: set[str]) -> float:
    """召回结果中匹配的比例"""
    if not retrieved_sources:
        return 0.0
    retrieved_set = set(retrieved_sources)
    hits = len(retrieved_set & expected_sources)
    return hits / len(retrieved_set)


def keyword_coverage(answer: str, expected_keywords: list[str]) -> float:
    """关键词覆盖率"""
    if not expected_keywords:
        return 0.0
    return sum(1 for kw in expected_keywords if kw in answer) / len(expected_keywords)
