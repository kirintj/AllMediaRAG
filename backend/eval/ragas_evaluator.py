"""RAGAS 标准评估器 - 与自研评估器并存互补

基于 RAGAS (Retrieval Augmented Generation Assessment) 框架，
提供标准化的 RAG 评估指标：faithfulness, answer_relevancy,
context_precision, context_recall。

使用方式：
    from eval.ragas_evaluator import RAGASEvaluator
    evaluator = RAGASEvaluator()
    report = evaluator.evaluate(dataset)

环境变量（RAGAS 默认使用 OpenAI）：
    OPENAI_API_KEY - 必须设置，或通过 llm_client 参数传入自定义 client
"""

import logging
import os

logger = logging.getLogger(__name__)


class RAGASEvaluator:
    """基于 RAGAS 框架的标准评估器"""

    def __init__(self, llm_client=None, embedding_service=None):
        """
        Args:
            llm_client: 可选的 OpenAI 兼容客户端实例（openai.OpenAI）。
                        若为 None，RAGAS 将从环境变量 OPENAI_API_KEY 创建。
            embedding_service: 可选的 embedding 服务（暂未使用，
                               RAGAS 自动推断 embedding provider）
        """
        self.llm_client = llm_client
        self.embedding_service = embedding_service

    def _build_ragas_llm(self):
        """构建 RAGAS 兼容的 LLM 实例"""
        from ragas.llms import llm_factory
        from openai import OpenAI

        model_name = "gpt-4o-mini"  # 默认模型

        if self.llm_client is not None:
            # 使用传入的 client
            client = self.llm_client
        else:
            # 从环境变量或项目配置创建
            api_key = os.environ.get("OPENAI_API_KEY")
            api_base = os.environ.get("OPENAI_API_BASE")
            if api_key is None:
                # 尝试从项目配置读取 MIMO API
                try:
                    from core.config import config
                    api_key = getattr(config, "MIMO_API_KEY", None)
                    api_base = getattr(config, "MIMO_API_BASE", None)
                    configured_model = getattr(config, "MIMO_MODEL", None)
                    if configured_model:
                        model_name = configured_model
                except Exception:
                    pass

            if api_key is None:
                raise ValueError(
                    "RAGAS 需要 OPENAI_API_KEY 环境变量，"
                    "或通过 llm_client 参数传入 OpenAI 兼容客户端"
                )

            kwargs = {"api_key": api_key}
            if api_base:
                kwargs["base_url"] = api_base
            client = OpenAI(**kwargs)

        return llm_factory(model_name, client=client)

    def evaluate(self, dataset: list[dict]) -> dict:
        """运行 RAGAS 评估

        Args:
            dataset: 评估样本列表，每个样本包含:
                - question (str): 用户问题
                - answer (str): 系统生成的回答
                - contexts (list[str]): 检索到的上下文列表
                - ground_truth (str): 参考答案

        Returns:
            与 evaluator.py report.json 结构对齐的评估报告
        """
        try:
            from ragas import evaluate as ragas_evaluate
            from datasets import Dataset
        except ImportError as e:
            logger.error("RAGAS 依赖未安装: %s", e)
            return {
                "total_samples": len(dataset),
                "framework": "ragas",
                "error": f"依赖缺失: {e}",
                "retrieval": {},
                "generation": {},
            }

        # 转换为 RAGAS 所需的 HuggingFace Dataset 格式
        ragas_data = {
            "question": [s["question"] for s in dataset],
            "answer": [s.get("answer", "") for s in dataset],
            "contexts": [s.get("contexts", []) for s in dataset],
            "ground_truth": [s.get("ground_truth", "") for s in dataset],
        }
        hf_dataset = Dataset.from_dict(ragas_data)

        logger.info("开始 RAGAS 评估，样本数: %d", len(dataset))

        try:
            ragas_llm = self._build_ragas_llm()
        except Exception as e:
            logger.error("RAGAS LLM 初始化失败: %s", e)
            return {
                "total_samples": len(dataset),
                "framework": "ragas",
                "error": f"LLM 初始化失败: {e}",
                "retrieval": {},
                "generation": {},
            }

        try:
            # metrics=None 使用 RAGAS 默认指标集，
            # llm 参数注入到所有需要 LLM 的指标中
            result = ragas_evaluate(
                dataset=hf_dataset,
                llm=ragas_llm,
                show_progress=True,
            )
        except Exception as e:
            logger.error("RAGAS 评估执行失败: %s", e)
            return {
                "total_samples": len(dataset),
                "framework": "ragas",
                "error": f"评估失败: {e}",
                "retrieval": {},
                "generation": {},
            }

        # 从 EvaluationResult 提取各指标均值
        scores = result.scores  # list[dict]
        aggregated = {}
        if scores:
            metric_names = scores[0].keys()
            for name in metric_names:
                values = [s[name] for s in scores if s.get(name) is not None]
                if values:
                    aggregated[name] = sum(values) / len(values)

        # 构建与 evaluator.py 对齐的报告结构
        report = {
            "total_samples": len(dataset),
            "framework": "ragas",
            "retrieval": {
                "context_precision": aggregated.get("context_precision"),
                "context_recall": aggregated.get("context_recall"),
            },
            "generation": {
                "faithfulness": aggregated.get("faithfulness"),
                "answer_relevancy": aggregated.get("answer_relevancy"),
            },
            "details": scores,
        }

        logger.info("RAGAS 评估完成")
        return report
