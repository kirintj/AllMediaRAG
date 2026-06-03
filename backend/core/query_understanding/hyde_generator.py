import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class HyDEGenerator:
    """假设性文档生成器（Hypothetical Document Embeddings）"""

    HYDE_PROMPT = """请根据以下查询，生成一段假设性的理想答案文档。
这段文档应该包含查询可能涉及的关键信息，用于改进检索效果。

查询：{query}

请生成一段详细的假设性文档（200-500字）："""

    # 不使用HyDE的意图类型
    SKIP_INTENTS = {"factoid"}

    def __init__(self, llm_client: Any):
        """
        Args:
            llm_client: LLM客户端，需要有generate方法
        """
        self.llm_client = llm_client

    def generate_hypothetical_document(self, query: str,
                                        intent_type: Optional[str] = None) -> Optional[str]:
        """
        生成假设性文档

        Args:
            query: 用户查询
            intent_type: 意图类型（可选），factoid类型会跳过生成

        Returns:
            假设性文档字符串，如果不需要生成则返回None
        """
        # 事实型查询不使用HyDE
        if intent_type in self.SKIP_INTENTS:
            return None

        # 生成prompt
        prompt = self.HYDE_PROMPT.format(query=query)

        try:
            # 调用LLM生成
            hypothetical_doc = self.llm_client.generate(prompt)

            # 验证返回值
            if hypothetical_doc and isinstance(hypothetical_doc, str) and len(hypothetical_doc.strip()) > 0:
                return hypothetical_doc.strip()
            return None

        except Exception as e:
            logger.debug("HyDE generation failed: %s", e)
            return None
