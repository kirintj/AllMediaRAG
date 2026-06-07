import re
from typing import Any


class QueryClassifier:
    """查询意图分类器（纯规则，0 LLM 调用，<1ms）"""

    INTENT_TYPES = {
        "factoid": "事实型查询，寻求具体答案",
        "analytical": "分析型查询，需要推理或比较",
        "procedural": "步骤型查询，寻求操作指南",
        "exploratory": "探索型查询，需要综合信息",
    }

    # ── 意图关键词模式（按优先级排列）──
    _PROCEDURAL_RE = re.compile(
        r'(如何|怎么|怎样|步骤|教程|方法|实现|配置|部署|安装|搭建|使用|操作|'
        r'搭建|设置|编写|创建|引入|集成|部署|调用|运行|启动|部署)',
    )
    _ANALYTICAL_RE = re.compile(
        r'(区别|对比|比较|为什么|为何|原理|优缺点|利弊|异同|差异|'
        r'哪个好|哪个快|选择|权衡|分析|深入|详解|剖析|底层|机制)',
    )
    _EXPLORATORY_RE = re.compile(
        r'(全面|详细|深入|系统|完整|综合|总结|梳理|整理|盘点|概览|'
        r'所有|全部|方方面面|来龙去脉|整体)',
    )
    _FACTOID_RE = re.compile(
        r'(什么是|是什么|有哪些|定义|含义|概念|作用|功能|特点|'
        r'类型|分类|版本|区别)',
    )

    def __init__(self, llm_client: Any = None, cache_size: int = 0):
        """
        Args:
            llm_client: 保留参数兼容，不再使用
            cache_size: 保留参数兼容
        """
        pass

    def classify(self, query: str) -> dict:
        """
        分类查询意图（纯规则匹配）

        Args:
            query: 用户查询

        Returns:
            {"intent_type": str, "confidence": float, "complexity": str}
        """
        q = query.strip()
        length = len(q)

        # ── 意图分类 ──
        # 优先匹配：探索 > 分析 > 步骤 > 事实
        if self._EXPLORATORY_RE.search(q):
            intent_type = "exploratory"
            confidence = 0.85
        elif self._ANALYTICAL_RE.search(q):
            intent_type = "analytical"
            confidence = 0.85
        elif self._PROCEDURAL_RE.search(q):
            intent_type = "procedural"
            confidence = 0.85
        elif self._FACTOID_RE.search(q):
            intent_type = "factoid"
            confidence = 0.9
        else:
            # 无关键词匹配：根据长度和标点推断
            if length <= 15:
                intent_type = "factoid"
                confidence = 0.7
            elif '？' in q or '?' in q:
                intent_type = "factoid"
                confidence = 0.65
            else:
                intent_type = "analytical"
                confidence = 0.6

        # ── 复杂度分类 ──
        # 基于长度 + 子句数 + 是否有多个实体
        clause_separators = len(re.findall(r'[，,；;、和与及或及以及]', q))
        has_code_ref = bool(re.search(r'[.\[\](){}\-><_]', q))

        if length <= 12 and clause_separators == 0:
            complexity = "simple"
        elif length <= 30 and clause_separators <= 1:
            complexity = "medium"
        elif clause_separators >= 2 and length > 30:
            complexity = "complex"
        elif clause_separators >= 3 or length > 60:
            complexity = "complex"
        else:
            complexity = "medium"

        # 代码相关查询通常更复杂
        if has_code_ref and complexity == "simple":
            complexity = "medium"

        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "complexity": complexity,
        }

    def clear_cache(self):
        """保留接口兼容"""
        pass
