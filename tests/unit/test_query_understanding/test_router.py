import pytest


def test_router_returns_routing_config():
    """测试路由器返回配置"""
    from core.query_understanding.router import QueryRouter

    router = QueryRouter()

    intent = {
        "intent_type": "analytical",
        "confidence": 0.9,
        "complexity": "complex"
    }

    config = router.route("比较Python和Java的优缺点", intent)

    assert "use_hyde" in config
    assert isinstance(config["use_hyde"], bool)
    assert "num_queries" in config
    assert isinstance(config["num_queries"], int)
    assert "rerank_top_k" in config
    assert isinstance(config["rerank_top_k"], int)
    assert "weights" in config
    assert "vector" in config["weights"]
    assert "bm25" in config["weights"]


def test_router_simple_factoid():
    """测试简单事实型查询的路由"""
    from core.query_understanding.router import QueryRouter

    router = QueryRouter()

    intent = {
        "intent_type": "factoid",
        "confidence": 0.95,
        "complexity": "simple"
    }

    config = router.route("Python的创始人是谁？", intent)

    assert config["use_hyde"] is False
    assert config["num_queries"] == 1
    assert config["rerank_top_k"] == 10


def test_router_analytical_complex():
    """测试复杂分析型查询的路由"""
    from core.query_understanding.router import QueryRouter

    router = QueryRouter()

    intent = {
        "intent_type": "analytical",
        "confidence": 0.85,
        "complexity": "complex"
    }

    config = router.route("比较Python和Java的优缺点", intent)

    assert config["use_hyde"] is True
    assert config["num_queries"] == 5
    assert config["rerank_top_k"] == 20


def test_router_unknown_intent():
    """测试未知意图类型使用默认配置"""
    from core.query_understanding.router import QueryRouter

    router = QueryRouter()

    intent = {
        "intent_type": "unknown",
        "confidence": 0.5,
        "complexity": "medium"
    }

    config = router.route("测试查询", intent)

    assert "use_hyde" in config
    assert "num_queries" in config
