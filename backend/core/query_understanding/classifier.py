import json
from collections import OrderedDict
from typing import Any


class QueryClassifier:
    """查询意图分类器"""

    INTENT_TYPES = {
        "factoid": "事实型查询，寻求具体答案",
        "analytical": "分析型查询，需要推理或比较",
        "procedural": "步骤型查询，寻求操作指南",
        "exploratory": "探索型查询，需要综合信息"
    }

    CLASSIFICATION_PROMPT = """请分析以下查询的意图类型，返回JSON格式：

查询：{query}

返回格式：
{{
    "intent_type": "factoid/analytical/procedural/exploratory",
    "confidence": 0.0-1.0之间的置信度,
    "complexity": "simple/medium/complex"
}}

只返回JSON，不要其他内容。"""

    def __init__(self, llm_client: Any, cache_size: int = 1000):
        """
        Args:
            llm_client: LLM客户端
            cache_size: 缓存大小，设为0时禁用缓存
        """
        self.llm_client = llm_client
        self.cache: OrderedDict[str, dict] = OrderedDict()
        self.cache_size = cache_size

    def classify(self, query: str) -> dict:
        """
        分类查询意图

        Args:
            query: 用户查询

        Returns:
            {
                "intent_type": str,
                "confidence": float,
                "complexity": str
            }
        """
        # 检查缓存
        if query in self.cache:
            self.cache.move_to_end(query)
            return self.cache[query]

        # 生成分类prompt
        prompt = self.CLASSIFICATION_PROMPT.format(query=query)

        # 调用LLM
        response = self.llm_client.generate(prompt)

        # 解析结果
        try:
            result = json.loads(response)
            # 验证字段
            result["intent_type"] = self._validate_intent_type(result.get("intent_type", "factoid"))
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            result["complexity"] = self._validate_complexity(result.get("complexity", "medium"))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # 解析失败时返回默认值
            result = {
                "intent_type": "factoid",
                "confidence": 0.5,
                "complexity": "medium"
            }

        # 更新缓存
        if self.cache_size > 0:
            if len(self.cache) >= self.cache_size:
                self.cache.popitem(last=False)
            self.cache[query] = result

        return result

    def _validate_intent_type(self, intent_type: str) -> str:
        """验证意图类型"""
        if intent_type in self.INTENT_TYPES:
            return intent_type
        return "factoid"

    def _validate_complexity(self, complexity: str) -> str:
        """验证复杂度"""
        if complexity in ["simple", "medium", "complex"]:
            return complexity
        return "medium"

    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
