import re
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CitationVerifier:
    """引用核查器：验证回答是否基于检索到的文档

    功能：
    - 从回答中提取引用标记
    - 用 LLM 验证回答的忠实度
    - 计算引用置信度
    - 检测潜在幻觉
    """

    # 引用标记正则模式
    CITATION_PATTERNS = [
        r'\[来源\s*(\d+)\]',       # [来源 1]
        r'\[(\d+)\]',               # [1]
        r'【来源\s*(\d+)】',       # 【来源1】
        r'参考\s*(\d+)',           # 参考 1
    ]

    def __init__(self, llm_client: Any, threshold: float = 0.5):
        """
        Args:
            llm_client: LLM 客户端
            threshold: 置信度阈值，低于此值标记为高风险
        """
        self.llm_client = llm_client
        self.threshold = threshold

    def verify(self, query: str, answer: str, contexts: list[dict]) -> dict:
        """核查回答的引用质量

        Args:
            query: 用户查询
            answer: LLM 生成的回答
            contexts: 检索到的上下文 [{"text": str, "metadata": dict}, ...]

        Returns:
            {
                "verified": bool,           # 是否通过核查
                "confidence": float,        # 置信度 0-1
                "citations": list,          # 找到的引用列表
                "hallucination_risk": str,  # "low" | "medium" | "high"
                "unsupported_claims": list, # 无来源支撑的断言
                "suggested_disclaimer": str # 建议添加的免责声明
            }
        """
        if not answer.strip():
            return self._empty_result()

        # 1. 提取引用标记
        citations = self._extract_citations(answer)

        # 2. 验证忠实度（使用 LLM）
        faithfulness = self._verify_faithfulness(answer, contexts)

        # 3. 计算置信度
        confidence = self._compute_confidence(citations, faithfulness, contexts)

        # 4. 确定风险等级
        hallucination_risk = self._assess_risk(confidence, faithfulness)

        # 5. 生成免责声明
        disclaimer = self._generate_disclaimer(hallucination_risk, faithfulness)

        return {
            "verified": confidence >= self.threshold,
            "confidence": round(confidence, 3),
            "citations": citations,
            "hallucination_risk": hallucination_risk,
            "unsupported_claims": faithfulness.get("unsupported_claims", []),
            "suggested_disclaimer": disclaimer,
        }

    def _empty_result(self) -> dict:
        """返回空结果"""
        return {
            "verified": False,
            "confidence": 0.0,
            "citations": [],
            "hallucination_risk": "high",
            "unsupported_claims": [],
            "suggested_disclaimer": "无法验证回答的准确性",
        }

    def _extract_citations(self, answer: str) -> list[dict]:
        """从回答中提取引用标记

        Returns:
            [{"marker": str, "index": int, "position": int}, ...]
        """
        citations = []
        seen_indices = set()

        for pattern in self.CITATION_PATTERNS:
            for match in re.finditer(pattern, answer):
                index = int(match.group(1))
                if index not in seen_indices:
                    citations.append({
                        "marker": match.group(0),
                        "index": index,
                        "position": match.start(),
                    })
                    seen_indices.add(index)

        return citations

    def _verify_faithfulness(self, answer: str, contexts: list[dict]) -> dict:
        """用 LLM 验证回答忠实度

        Returns:
            {
                "claims": [{"text": str, "supported": bool, "source_index": int|None}],
                "unsupported_claims": [str],
                "support_ratio": float
            }
        """
        if not contexts:
            return {
                "claims": [],
                "unsupported_claims": [answer],
                "support_ratio": 0.0,
            }

        # 构建参考文档字符串
        context_str = "\n---\n".join([
            f"[来源 {i+1}] {c['text'][:500]}" for i, c in enumerate(contexts[:5])
        ])

        prompt = f"""请逐句分析以下回答，判断每句话是否有参考文档支撑。

---参考文档---
{context_str}

---回答---
{answer}

请以 JSON 格式输出分析结果：
{{
    "claims": [
        {{"text": "句子内容", "supported": true/false, "source_index": 来源编号或null}}
    ],
    "unsupported_claims": ["无支撑的句子1", ...],
    "support_ratio": 有支撑的句子比例(0-1)
}}

只输出 JSON，不要其他内容。"""

        try:
            response = self.llm_client.generate(prompt)
            # 尝试解析 JSON
            result = self._parse_json_response(response)
            if result:
                return result
        except Exception as e:
            logger.warning("Faithfulness verification failed: %s", e)

        # 降级：简单统计
        return self._simple_faithfulness_check(answer, contexts)

    def _parse_json_response(self, response: str) -> Optional[dict]:
        """解析 LLM 返回的 JSON"""
        try:
            # 尝试直接解析
            return json.loads(response)
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

    def _simple_faithfulness_check(self, answer: str, contexts: list[dict]) -> dict:
        """简单的忠实度检查（降级方案）"""
        # 合并所有上下文
        all_context = " ".join([c["text"] for c in contexts])

        # 简单的句子切分
        sentences = re.split(r'[。！？\n]', answer)
        sentences = [s.strip() for s in sentences if s.strip() and len(s) > 5]

        claims = []
        unsupported = []

        for sent in sentences:
            # 简单检查：句子中的关键词是否在上下文中出现
            keywords = set(re.findall(r'[一-龥a-zA-Z0-9]{2,}', sent))
            if not keywords:
                continue

            # 计算关键词在上下文中的覆盖率
            found = sum(1 for kw in keywords if kw in all_context)
            supported = found / len(keywords) > 0.3

            claims.append({
                "text": sent,
                "supported": supported,
                "source_index": None,
            })

            if not supported:
                unsupported.append(sent)

        support_ratio = len([c for c in claims if c["supported"]]) / len(claims) if claims else 0

        return {
            "claims": claims,
            "unsupported_claims": unsupported,
            "support_ratio": support_ratio,
        }

    def _compute_confidence(self, citations: list, faithfulness: dict, contexts: list) -> float:
        """综合计算引用置信度

        公式：
        - citation_score: 引用标记覆盖率 (0.3)
        - support_ratio: 忠实度支撑比例 (0.5)
        - context_coverage: 上下文利用率 (0.2)
        """
        # 引用标记得分：有引用得 1，无引用得 0.5（可能隐式引用）
        citation_score = 1.0 if citations else 0.5

        # 忠实度支撑比例
        support_ratio = faithfulness.get("support_ratio", 0.0)

        # 上下文覆盖率：回答长度与上下文总长度的比值（合理范围内越高越好）
        answer_length = sum(len(c["text"]) for c in faithfulness.get("claims", []))
        context_length = sum(len(c["text"]) for c in contexts)
        if context_length > 0:
            coverage = min(answer_length / context_length, 1.0)
        else:
            coverage = 0.0

        # 综合置信度
        confidence = (
            citation_score * 0.3 +
            support_ratio * 0.5 +
            coverage * 0.2
        )

        return min(confidence, 1.0)

    def _assess_risk(self, confidence: float, faithfulness: dict) -> str:
        """评估幻觉风险等级"""
        support_ratio = faithfulness.get("support_ratio", 0.0)

        if confidence >= 0.7 and support_ratio >= 0.8:
            return "low"
        elif confidence >= 0.4 and support_ratio >= 0.5:
            return "medium"
        else:
            return "high"

    def _compute_retrieval_metrics(self, retrieval_results: Optional[dict]) -> dict:
        """计算检索质量指标

        Args:
            retrieval_results: 包含 documents 和 distances 的字典

        Returns:
            {
                "doc_count": int,
                "max_similarity": float,
                "avg_similarity": float,
                "stability": float,
            }
        """
        if not retrieval_results:
            return {}

        distances = retrieval_results.get("distances", [])
        doc_count = len(retrieval_results.get("documents", []))

        if not distances:
            return {"doc_count": doc_count}

        # 计算相似度（距离越小越相似）
        similarities = [1 - d for d in distances]
        avg_similarity = sum(similarities) / len(similarities)

        # 计算稳定性（方差越小越稳定）
        variance = sum((s - avg_similarity) ** 2 for s in similarities) / len(similarities)
        stability = max(0, 1 - variance * 10)  # 归一化

        return {
            "doc_count": doc_count,
            "max_similarity": round(max(similarities), 3),
            "avg_similarity": round(avg_similarity, 3),
            "stability": round(stability, 3),
        }

    def _generate_disclaimer(self, risk: str, faithfulness: dict) -> str:
        """生成免责声明"""
        unsupported = faithfulness.get("unsupported_claims", [])

        if risk == "low":
            return ""
        elif risk == "medium":
            return "⚠️ 部分内容可能缺乏文档支撑，请谨慎参考。"
        else:
            disclaimer = "⚠️ 该回答可能包含未经文档验证的内容。"
            if unsupported:
                disclaimer += f"\n以下内容可能缺乏支撑：\n" + "\n".join(
                    [f"- {claim[:50]}..." if len(claim) > 50 else f"- {claim}"
                     for claim in unsupported[:3]]
                )
            return disclaimer
