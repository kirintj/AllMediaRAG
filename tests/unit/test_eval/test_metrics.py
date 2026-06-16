"""eval.metrics 单元测试"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend"))

from eval.metrics import hit_rate, recall_at_k, mrr, precision, keyword_coverage


# ── hit_rate ──────────────────────────────────────────────────────────────────

class TestHitRate:
    def test_hit(self):
        assert hit_rate(["a", "b"], {"a"}) == 1.0

    def test_miss(self):
        assert hit_rate(["x", "y"], {"a", "b"}) == 0.0

    def test_empty_retrieved(self):
        assert hit_rate([], {"a"}) == 0.0

    def test_empty_expected(self):
        assert hit_rate(["a"], set()) == 0.0

    def test_partial_hit(self):
        """只要命中一个就返回 1.0"""
        assert hit_rate(["x", "a", "y"], {"a", "b"}) == 1.0


# ── recall_at_k ──────────────────────────────────────────────────────────────

class TestRecallAtK:
    def test_full_recall(self):
        assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=5) == 1.0

    def test_partial_recall(self):
        assert recall_at_k(["a", "x"], {"a", "b"}, k=5) == 0.5

    def test_k_limits_results(self):
        """只看前 K 个结果"""
        assert recall_at_k(["x", "a", "b"], {"a", "b"}, k=1) == 0.0
        assert recall_at_k(["a", "x", "b"], {"a", "b"}, k=1) == 0.5

    def test_no_hits(self):
        assert recall_at_k(["x", "y"], {"a", "b"}, k=5) == 0.0

    def test_empty_expected(self):
        assert recall_at_k(["a"], set()) == 0.0


# ── mrr ──────────────────────────────────────────────────────────────────────

class TestMRR:
    def test_first_rank(self):
        assert mrr(["a", "b"], {"a"}) == 1.0

    def test_second_rank(self):
        assert mrr(["x", "a"], {"a"}) == 0.5

    def test_third_rank(self):
        assert mrr(["x", "y", "a"], {"a"}) == pytest.approx(1.0 / 3)

    def test_no_hit(self):
        assert mrr(["x", "y"], {"a"}) == 0.0

    def test_empty_retrieved(self):
        assert mrr([], {"a"}) == 0.0


# ── precision ────────────────────────────────────────────────────────────────

class TestPrecision:
    def test_all_match(self):
        assert precision(["a", "b"], {"a", "b"}) == 1.0

    def test_half_match(self):
        assert precision(["a", "x"], {"a", "b"}) == 0.5

    def test_no_match(self):
        assert precision(["x", "y"], {"a", "b"}) == 0.0

    def test_empty_retrieved(self):
        assert precision([], {"a"}) == 0.0

    def test_empty_expected(self):
        assert precision(["a"], set()) == 0.0


# ── keyword_coverage ─────────────────────────────────────────────────────────

class TestKeywordCoverage:
    def test_full_coverage(self):
        assert keyword_coverage("hello world", ["hello", "world"]) == 1.0

    def test_partial_coverage(self):
        assert keyword_coverage("hello world", ["hello", "missing"]) == 0.5

    def test_no_coverage(self):
        assert keyword_coverage("foo bar", ["hello", "world"]) == 0.0

    def test_empty_keywords(self):
        assert keyword_coverage("hello", []) == 0.0

    def test_empty_answer(self):
        assert keyword_coverage("", ["hello"]) == 0.0
