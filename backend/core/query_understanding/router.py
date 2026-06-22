import logging

logger = logging.getLogger(__name__)


class QueryRouter:
    """查询路由器：根据查询特征选择检索策略"""

    # 路由规则配置
    ROUTING_RULES = {
        # (intent_type, complexity) -> config
        ("factoid", "simple"): {
            "use_hyde": False,
            "num_queries": 1,       # 简单事实查询无需扩展
            "rerank_top_k": 15,
            "weights": {"vector": 0.7, "bm25": 0.3}
        },
        ("factoid", "medium"): {
            "use_hyde": False,      # 事实型一般不需要 HyDE
            "num_queries": 1,       # 减少 LLM 调用
            "rerank_top_k": 15,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("factoid", "complex"): {
            "use_hyde": True,
            "num_queries": 2,
            "rerank_top_k": 20,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("analytical", "simple"): {
            "use_hyde": False,
            "num_queries": 1,
            "rerank_top_k": 15,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("analytical", "medium"): {
            "use_hyde": True,
            "num_queries": 2,
            "rerank_top_k": 20,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("analytical", "complex"): {
            "use_hyde": True,
            "num_queries": 3,
            "rerank_top_k": 25,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("procedural", "simple"): {
            "use_hyde": False,
            "num_queries": 1,
            "rerank_top_k": 15,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("procedural", "medium"): {
            "use_hyde": True,
            "num_queries": 2,
            "rerank_top_k": 20,
            "weights": {"vector": 0.6, "bm25": 0.4}
        },
        ("procedural", "complex"): {
            "use_hyde": True,
            "num_queries": 3,
            "rerank_top_k": 25,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("exploratory", "simple"): {
            "use_hyde": True,
            "num_queries": 2,
            "rerank_top_k": 20,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("exploratory", "medium"): {
            "use_hyde": True,
            "num_queries": 3,
            "rerank_top_k": 25,
            "weights": {"vector": 0.5, "bm25": 0.5}
        },
        ("exploratory", "complex"): {
            "use_hyde": True,
            "num_queries": 4,
            "rerank_top_k": 30,
            "weights": {"vector": 0.5, "bm25": 0.5}
        }
    }

    # 默认配置（当规则未匹配时使用）
    DEFAULT_CONFIG = {
        "use_hyde": False,
        "num_queries": 1,
        "rerank_top_k": 10,
        "weights": {"vector": 0.7, "bm25": 0.3}
    }

    def route(self, query: str, intent: dict) -> dict:
        """
        根据查询特征选择检索策略

        Args:
            query: 用户查询
            intent: 意图分类结果，包含 intent_type, confidence, complexity

        Returns:
            {
                "use_hyde": bool,
                "num_queries": int,
                "rerank_top_k": int,
                "weights": {"vector": float, "bm25": float}
            }
        """
        intent_type = intent.get("intent_type", "factoid")
        complexity = intent.get("complexity", "medium")

        # 查找匹配的规则
        key = (intent_type, complexity)
        config = self.ROUTING_RULES.get(key, self.DEFAULT_CONFIG).copy()

        logger.debug("Routing query with intent=%s, complexity=%s -> config=%s",
                     intent_type, complexity, config)

        return config
