"""Self-RAG 反思机制

在生成回答后检查是否遗漏了检索文档中的关键信息。
仅对复杂查询（analytical / exploratory）启用，避免简单查询的额外延迟。
"""

import json
import re
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SelfRAGReflector:
    """Self-RAG 反思器

    工作流程：
    1. 检查回答是否遗漏了检索文档中的关键信息
    2. 如果发现遗漏，生成补充内容
    3. 返回反思结果（包含是否需要补充 + 补充文本）

    设计原则：
    - 仅对复杂查询启用（analytical / exploratory）
    - 单次 LLM 调用完成反思
    - 补充内容直接追加，不重新生成整个回答
    """

    # 需要反思的查询类型
    REFLECT_INTENTS = {"analytical", "exploratory"}

    REFLECTION_PROMPT = """你是一个 RAG 系统的回答质量审查员。请检查以下回答是否完整覆盖了检索文档中的关键信息。

## 检索文档
{contexts}

## 用户问题
{question}

## 当前回答
{answer}

## 审查要求

请判断：
1. 回答是否遗漏了检索文档中的重要信息？（不包括无关细节）
2. 是否有文档明确支持但回答未提及的关键点？
3. 对于多部分问题，回答是否覆盖了所有方面？

请以 JSON 格式输出：
{{
    "has_gaps": true/false,
    "missing_points": ["遗漏的要点1", "遗漏的要点2"],
    "supplement": "补充内容（如果 has_gaps=true，用完整的句子描述遗漏的信息；否则为空字符串）"
}}

只输出 JSON，不要其他内容。"""

    def __init__(self, llm_client: Any):
        """
        Args:
            llm_client: LLM 客户端，需要有 generate 方法
        """
        self.llm_client = llm_client

    def should_reflect(self, intent_type: str) -> bool:
        """判断是否需要反思

        Args:
            intent_type: 查询意图类型

        Returns:
            是否需要反思
        """
        return intent_type in self.REFLECT_INTENTS

    def reflect(
        self, question: str, answer: str, contexts: list[dict]
    ) -> Optional[dict]:
        """执行反思，检查回答完整性

        Args:
            question: 用户问题
            answer: 生成的回答
            contexts: 检索到的上下文 [{"text": str, "metadata": dict}, ...]

        Returns:
            反思结果 {"has_gaps": bool, "missing_points": list, "supplement": str}
            失败时返回 None
        """
        if not answer.strip() or not contexts:
            return None

        # 限制上下文长度，避免 prompt 过长
        context_str = "\n---\n".join([
            f"[{c['metadata'].get('source', '?')}] {c['text'][:600]}"
            for c in contexts[:5]
        ])

        prompt = self.REFLECTION_PROMPT.format(
            contexts=context_str,
            question=question,
            answer=answer,
        )

        try:
            response = self.llm_client.generate(prompt)
            result = self._parse_response(response)

            if result and result.get("has_gaps") and result.get("supplement"):
                logger.info(
                    "Self-RAG: found %d missing points",
                    len(result.get("missing_points", [])),
                )
            else:
                logger.debug("Self-RAG: no gaps found")

            return result

        except Exception as e:
            logger.warning("Self-RAG reflection failed: %s", e)
            return None

    def _parse_response(self, response: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON"""
        if not response or not isinstance(response, str):
            return None

        # 尝试直接解析
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 部分
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None
