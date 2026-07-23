"""base.py 表达式类与兼容接口单元测试。"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.providers.base import (
    MatchTextExpr, MatchDenseExpr, FusionExpr, OrderByExpr,
)


# ---------------------------------------------------------------------------
# Expression classes
# ---------------------------------------------------------------------------

class TestMatchTextExpr:
    def test_defaults(self):
        expr = MatchTextExpr(fields=["text"], matching_text="query")
        assert expr.topn == 10
        assert expr.extra_options is None

    def test_custom_options(self):
        expr = MatchTextExpr(
            fields=["text", "title"],
            matching_text="test",
            topn=5,
            extra_options={"minimum_should_match": "80%"},
        )
        assert expr.fields == ["text", "title"]
        assert expr.extra_options["minimum_should_match"] == "80%"


class TestMatchDenseExpr:
    def test_defaults(self):
        expr = MatchDenseExpr(embedding_data=[0.1, 0.2, 0.3])
        assert expr.topn == 10
        assert expr.distance_type == "cosine"
        assert expr.extra_options is None


class TestFusionExpr:
    def test_weighted_sum(self):
        expr = FusionExpr(
            method="weighted_sum",
            topn=15,
            fusion_params={"weights": "0.7,0.3"},
        )
        assert expr.method == "weighted_sum"
        assert expr.fusion_params["weights"] == "0.7,0.3"


class TestOrderByExpr:
    def test_chaining(self):
        order = OrderByExpr().asc("created_at").desc("score")
        assert order.clauses == [("created_at", "asc"), ("score", "desc")]

    def test_empty(self):
        order = OrderByExpr()
        assert order.clauses == []

    def test_returns_self(self):
        order = OrderByExpr()
        result = order.asc("a")
        assert result is order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
