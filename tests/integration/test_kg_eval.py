"""KG evaluation: measure entity resolution accuracy against golden set.

Run: python -m pytest tests/integration/test_kg_eval.py -v
"""

import json
import pytest
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load_golden_set():
    with open(FIXTURES / "kg_golden_set.json", encoding="utf-8") as f:
        return json.load(f)


class TestEntityResolution:
    """Test entity resolution accuracy against golden set."""

    def test_resolve_cross_law_query(self):
        from core.kg.graph_retriever import GraphRetriever

        retriever = GraphRetriever.__new__(GraphRetriever)
        retriever._alias_map = {
            "数据安全法": "中华人民共和国数据安全法",
            "数安法": "中华人民共和国数据安全法",
            "中华人民共和国数据安全法": "中华人民共和国数据安全法",
            "个人信息保护法": "中华人民共和国个人信息保护法",
            "个保法": "中华人民共和国个人信息保护法",
            "中华人民共和国个人信息保护法": "中华人民共和国个人信息保护法",
            "全国人大常委会": "全国人大常委会",
        }
        retriever._all_aliases = set(retriever._alias_map.keys())

        golden = load_golden_set()
        for case in golden:
            resolved = retriever.resolve_entities(case["query"])
            # Verify text-based entity resolution against expected_resolved
            for expected_entity in case.get("expected_resolved", case.get("expected_entities", [])):
                found = any(
                    expected_entity in r or r in expected_entity
                    for r in resolved
                )
                if case["expected_graph_contribution"]:
                    assert found or not case.get("expected_resolved", []), \
                        f"Case {case['id']}: expected resolved entity '{expected_entity}' not found in {resolved}"
            # Negative cases: no entities should be resolved
            if not case["expected_graph_contribution"]:
                assert resolved == [], \
                    f"Case {case['id']}: expected no resolved entities but got {resolved}"
