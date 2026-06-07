import json
import numpy as np


class RAGEvaluator:
    """RAG 系统评估器"""

    def __init__(self, rag_engine, llm_client):
        """
        Args:
            rag_engine: RAGEngine 实例
            llm_client: LLMClient 实例（用于 LLM-as-Judge）
        """
        self.engine = rag_engine
        self.llm_client = llm_client

    def evaluate_retrieval(self, question: str, expected_sources: list[str], top_k: int = 5) -> dict:
        """评估检索质量

        Args:
            question: 用户问题
            expected_sources: 期望命中的文档来源列表
            top_k: 召回数量

        Returns:
            {"recall": float, "mrr": float, "precision": float, "retrieved_sources": list}
        """
        results = self.engine.full_retrieve(question)
        retrieved_sources = [meta["source"] for meta in results["metadatas"]]

        if not expected_sources:
            return {
                "recall": None,
                "mrr": None,
                "precision": None,
                "retrieved_sources": retrieved_sources,
            }

        # Recall@K: expected_sources 中有多少出现在召回结果里
        expected_set = set(expected_sources)
        retrieved_set = set(retrieved_sources)
        hits = expected_set & retrieved_set
        recall = len(hits) / len(expected_set) if expected_set else 0.0

        # MRR: 第一个命中结果的排名倒数
        mrr = 0.0
        for i, src in enumerate(retrieved_sources):
            if src in expected_set:
                mrr = 1.0 / (i + 1)
                break

        # Precision: 召回结果中匹配的比例
        precision = len(hits) / len(retrieved_set) if retrieved_set else 0.0

        return {
            "recall": recall,
            "mrr": mrr,
            "precision": precision,
            "retrieved_sources": retrieved_sources,
        }

    def evaluate_generation(self, question: str, answer: str, contexts: list[str], reference_answer: str) -> dict:
        """评估生成质量（LLM-as-Judge）

        Args:
            question: 用户问题
            answer: 系统生成的回答
            contexts: 检索到的上下文文本列表
            reference_answer: 参考答案

        Returns:
            {"faithfulness": int, "relevancy": int, "reasoning": str}
        """
        context_str = "\n---\n".join(contexts)

        judge_prompt = f"""你是一个 RAG 系统评估专家。请根据以下信息评估回答质量。

---参考文档---
{context_str}

---用户问题---
{question}

---参考答案---
{reference_answer}

---系统回答---
{answer}

请评估以下两个维度，每个维度打 1-5 分：
1. Faithfulness（忠实度）：回答是否基于参考文档，没有编造信息
2. Answer Relevancy（相关性）：回答是否切题，是否完整回答了问题

输出 JSON 格式：
{{"faithfulness": 分数, "relevancy": 分数, "reasoning": "简要理由"}}"""

        try:
            response = self.llm_client.generate(judge_prompt)
            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(response)
            return {
                "faithfulness": int(result.get("faithfulness", 0)),
                "relevancy": int(result.get("relevancy", 0)),
                "reasoning": result.get("reasoning", ""),
            }
        except Exception as e:
            return {
                "faithfulness": 0,
                "relevancy": 0,
                "reasoning": f"LLM 评估失败: {str(e)}",
            }

    def run(self, dataset_path: str, top_k: int = 5) -> dict:
        """运行完整评估

        Args:
            dataset_path: 评估数据集路径
            top_k: 召回数量

        Returns:
            评估报告
        """
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        results = []
        for sample in dataset:
            question = sample["question"]
            expected_sources = sample.get("expected_sources", [])
            expected_keywords = sample.get("expected_keywords", [])
            reference_answer = sample.get("reference_answer", "")

            # 检索评估（使用完整管道）
            retrieval_result = self.evaluate_retrieval(question, expected_sources, top_k)

            # 生成回答（使用完整管道）
            rag_result = self.engine.full_retrieve(question)
            contexts = rag_result["documents"]
            contexts_meta = rag_result["metadatas"]

            prompt = self.engine.build_prompt(question, [
                {"text": doc, "metadata": meta}
                for doc, meta in zip(contexts, contexts_meta)
            ])
            answer = self.llm_client.generate(prompt)

            # 关键词覆盖率
            keyword_hits = sum(1 for kw in expected_keywords if kw in answer)
            keyword_coverage = keyword_hits / len(expected_keywords) if expected_keywords else None

            # 生成评估
            gen_result = self.evaluate_generation(question, answer, contexts, reference_answer)

            results.append({
                "question": question,
                "answer": answer,
                "retrieval": retrieval_result,
                "generation": gen_result,
                "keyword_coverage": keyword_coverage,
            })

        # 汇总指标
        report = self._aggregate(results, len(dataset))
        return report

    def _aggregate(self, results: list[dict], total: int) -> dict:
        """汇总评估指标"""
        # 检索指标
        recalls = [r["retrieval"]["recall"] for r in results if r["retrieval"]["recall"] is not None]
        mrrs = [r["retrieval"]["mrr"] for r in results if r["retrieval"]["mrr"] is not None]
        precisions = [r["retrieval"]["precision"] for r in results if r["retrieval"]["precision"] is not None]

        # 生成指标
        faithfulness_scores = [r["generation"]["faithfulness"] for r in results if r["generation"]["faithfulness"] > 0]
        relevancy_scores = [r["generation"]["relevancy"] for r in results if r["generation"]["relevancy"] > 0]

        # 关键词覆盖率
        kw_coverages = [r["keyword_coverage"] for r in results if r["keyword_coverage"] is not None]

        report = {
            "total_samples": total,
            "retrieval": {
                "recall_at_k": float(np.mean(recalls)) if recalls else None,
                "mrr": float(np.mean(mrrs)) if mrrs else None,
                "precision": float(np.mean(precisions)) if precisions else None,
            },
            "generation": {
                "faithfulness": float(np.mean(faithfulness_scores)) if faithfulness_scores else None,
                "relevancy": float(np.mean(relevancy_scores)) if relevancy_scores else None,
            },
            "keyword_coverage": float(np.mean(kw_coverages)) if kw_coverages else None,
            "details": results,
        }
        return report
