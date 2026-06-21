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


def test_compute_retrieval_metrics_distances_present_but_documents_empty():
    """Edge case: distances provided but documents list is empty."""
    verifier = CitationVerifier(MockLLMClient())

    retrieval_results = {"documents": [], "distances": [0.1]}
    metrics = verifier._compute_retrieval_metrics(retrieval_results)

    assert metrics["doc_count"] == 0
    assert metrics["max_similarity"] == 0.9
    assert metrics["avg_similarity"] == 0.9
    # Single distance means variance is 0, so stability is 1.0
    assert metrics["stability"] == 1.0


def test_compute_retrieval_metrics_none_distances():
    """Edge case: distances key is explicitly None."""
    verifier = CitationVerifier(MockLLMClient())

    retrieval_results = {"documents": ["doc1"], "distances": None}
    metrics = verifier._compute_retrieval_metrics(retrieval_results)

    assert metrics == {"doc_count": 1}


def test_compute_retrieval_metrics_single_document():
    """Single-document case: variance is always 0, so stability is always 1."""
    verifier = CitationVerifier(MockLLMClient())

    retrieval_results = {"documents": ["doc1"], "distances": [0.5]}
    metrics = verifier._compute_retrieval_metrics(retrieval_results)

    assert metrics["doc_count"] == 1
    assert metrics["max_similarity"] == 0.5
    assert metrics["avg_similarity"] == 0.5
    assert metrics["stability"] == 1.0


def test_compute_retrieval_metrics_large_distances_clamped():
    """L2 distances > 1 should not produce negative similarities."""
    verifier = CitationVerifier(MockLLMClient())

    retrieval_results = {"documents": ["doc1", "doc2"], "distances": [2.0, 1.5]}
    metrics = verifier._compute_retrieval_metrics(retrieval_results)

    assert metrics["max_similarity"] == 0.0
    assert metrics["avg_similarity"] == 0.0
    assert metrics["stability"] == 1.0


# Task 2: 忠实度指标测试
def test_extract_faithfulness_metrics():
    verifier = CitationVerifier(MockLLMClient())

    faithfulness = {
        "claims": [
            {"text": "claim1", "supported": True, "source_index": 1},
            {"text": "claim2", "supported": False, "source_index": None},
            {"text": "claim3", "supported": True, "source_index": 2},
        ],
        "unsupported_claims": ["claim2"],
        "support_ratio": 0.667
    }
    metrics = verifier._extract_faithfulness_metrics(faithfulness)

    assert metrics["support_ratio"] == 0.667
    assert metrics["claim_count"] == 3
    assert metrics["supported_count"] == 2


def test_extract_faithfulness_metrics_empty():
    verifier = CitationVerifier(MockLLMClient())

    metrics = verifier._extract_faithfulness_metrics(None)
    assert metrics == {}

    # 空字典也会返回空（因为 if not faithfulness 为 True）
    metrics = verifier._extract_faithfulness_metrics({})
    assert metrics == {}


# Task 3: 上下文覆盖率测试
def test_compute_context_coverage():
    verifier = CitationVerifier(MockLLMClient())

    answer = "这是一个测试回答，长度约为20个字符。"
    contexts = [
        {"text": "这是一个很长的上下文文档，包含了很多内容。" * 10, "metadata": {}},
        {"text": "另一个上下文文档。" * 5, "metadata": {}},
    ]
    coverage = verifier._compute_context_coverage(answer, contexts)

    assert isinstance(coverage, float)
    assert 0 <= coverage <= 1


def test_compute_context_coverage_empty():
    verifier = CitationVerifier(MockLLMClient())

    coverage = verifier._compute_context_coverage("test", [])
    assert coverage == 0.0


# Task 4: 集成测试
def test_verify_with_retrieval_results():
    verifier = CitationVerifier(MockLLMClient())

    query = "测试问题"
    answer = "测试回答"
    contexts = [{"text": "测试上下文", "metadata": {}}]
    retrieval_results = {
        "documents": ["doc1"],
        "distances": [0.2],
        "metadatas": [{"source": "test.md"}]
    }

    result = verifier.verify(query, answer, contexts, retrieval_results=retrieval_results)

    assert "retrieval_metrics" in result
    assert "faithfulness_metrics" in result
    assert "context_coverage" in result
    assert result["retrieval_metrics"]["doc_count"] == 1
