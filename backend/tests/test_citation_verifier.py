import pytest
from core.verification.citation_verifier import CitationVerifier


class MockLLMClient:
    def generate(self, prompt):
        return '{"claims": [{"text": "test", "supported": true, "source_index": 1}], "unsupported_claims": [], "support_ratio": 1.0}'


def test_compute_retrieval_metrics():
    verifier = CitationVerifier(MockLLMClient())

    # 测试正常情况
    retrieval_results = {
        "documents": ["doc1", "doc2", "doc3"],
        "distances": [0.1, 0.2, 0.3]
    }
    metrics = verifier._compute_retrieval_metrics(retrieval_results)

    assert metrics["doc_count"] == 3
    assert metrics["max_similarity"] == 0.9  # 1 - 0.1
    assert metrics["avg_similarity"] == 0.8  # 1 - 0.2
    assert "stability" in metrics


def test_compute_retrieval_metrics_empty():
    verifier = CitationVerifier(MockLLMClient())

    # 测试空结果
    metrics = verifier._compute_retrieval_metrics(None)
    assert metrics == {}

    metrics = verifier._compute_retrieval_metrics({"documents": [], "distances": []})
    assert metrics == {"doc_count": 0}
