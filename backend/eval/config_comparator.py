"""自动化配置比较框架

比较不同 RAG 配置（分块策略、检索参数、重排序模型等）的评估效果，
生成 Markdown 对比报告。

运行方式：
    cd backend && python eval/config_comparator.py \
        --dataset eval/eval_dataset.json \
        --compare top_k:3,5,10 \
        --compare rrf_k:30,60 \
        --output comparison_report.md
"""

import sys
import json
import argparse
import itertools
from dataclasses import dataclass, field
from pathlib import Path
from copy import deepcopy

# 添加项目路径（与 run_eval.py 保持一致）
project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

import os
os.chdir(project_root)

from core.config import config
from core.rag_engine import RAGEngine
from core.llm_client import LLMClient
from eval.evaluator import RAGEvaluator


@dataclass
class ComparisonReport:
    """配置比较报告"""

    baseline: dict
    candidates: list[dict]
    best_config: dict
    summary_table: str


class ConfigComparator:
    """自动化配置比较器

    对比不同 RAG 配置的评估效果，找到最优配置组合。

    Args:
        rag_engine: RAGEngine 实例
        evaluator: RAGEvaluator 实例
    """

    def __init__(self, rag_engine: RAGEngine, evaluator: RAGEvaluator):
        self.engine = rag_engine
        self.evaluator = evaluator

    def compare(
        self,
        base_config: dict,
        candidates: list[dict],
        dataset_path: str,
        top_k: int = 5,
    ) -> ComparisonReport:
        """运行配置比较

        Args:
            base_config: 基准配置字典 {attr_name: value}
            candidates: 候选配置列表，每个为 {attr_name: value}
            dataset_path: 评估数据集路径
            top_k: 检索返回文档数量

        Returns:
            ComparisonReport 包含基准、各候选的评估结果和最优配置
        """
        # 保存引擎原始属性快照，用于最终恢复
        original_attrs = {}
        all_attrs = set(base_config.keys())
        for c in candidates:
            all_attrs.update(c.keys())
        for attr in all_attrs:
            # 统一使用小写属性名（引擎属性通常为小写，如 top_k）
            normalized = attr.lower() if hasattr(self.engine, attr.lower()) else attr
            if hasattr(self.engine, normalized):
                original_attrs[normalized] = getattr(self.engine, normalized)

        # 运行基准配置评估
        self._apply_config(base_config)
        baseline_report = self.evaluator.run(dataset_path, top_k=top_k)
        baseline_metrics = self._extract_metrics(baseline_report)
        baseline_entry = {
            "config": deepcopy(base_config),
            "metrics": baseline_metrics,
            "composite_score": self._score_config(baseline_metrics),
        }

        # 运行各候选配置评估
        candidate_results = []
        for candidate in candidates:
            self._apply_config(candidate)
            report = self.evaluator.run(dataset_path, top_k=top_k)
            metrics = self._extract_metrics(report)
            entry = {
                "config": deepcopy(candidate),
                "metrics": metrics,
                "composite_score": self._score_config(metrics),
            }
            candidate_results.append(entry)

        # 恢复引擎原始属性
        for attr, value in original_attrs.items():
            setattr(self.engine, attr, value)

        # 找出最优配置
        all_results = [baseline_entry] + candidate_results
        best = max(all_results, key=lambda x: x["composite_score"])

        # 生成 Markdown 对比表
        summary_table = self._generate_markdown_table(all_results)

        return ComparisonReport(
            baseline=baseline_entry,
            candidates=candidate_results,
            best_config=best,
            summary_table=summary_table,
        )

    def _apply_config(self, config_dict: dict) -> None:
        """将配置字典应用到引擎实例

        遍历配置字典，依次尝试以小写属性名和原始 key 名设置引擎属性。

        Args:
            config_dict: {attr_name: value} 配置字典
        """
        for key, value in config_dict.items():
            # 先尝试小写属性名（引擎常用小写，如 top_k）
            if hasattr(self.engine, key.lower()):
                setattr(self.engine, key.lower(), value)
            elif hasattr(self.engine, key):
                setattr(self.engine, key, value)

    def _extract_metrics(self, report: dict) -> dict:
        """从评估报告中提取核心指标

        Args:
            report: RAGEvaluator.run() 返回的评估报告

        Returns:
            包含 MRR, Recall, Precision, Faithfulness, Relevancy 的字典
        """
        retrieval = report.get("retrieval", {})
        generation = report.get("generation", {})

        return {
            "mrr": retrieval.get("mrr"),
            "recall": retrieval.get("recall_at_k"),
            "precision": retrieval.get("precision"),
            "faithfulness": generation.get("faithfulness"),
            "relevancy": generation.get("relevancy"),
        }

    def _score_config(self, metrics: dict) -> float:
        """计算综合评分

        公式：MRR*0.4 + Recall@K*0.3 + Faithfulness_norm*0.3
        Faithfulness 为 1-5 分制，归一化到 0-1 后参与计算。

        Args:
            metrics: 包含各指标的字典

        Returns:
            综合评分（0-1 范围）
        """
        mrr = metrics.get("mrr") or 0.0
        recall = metrics.get("recall") or 0.0
        faithfulness_raw = metrics.get("faithfulness") or 0.0

        # Faithfulness 归一化：1-5 分 -> 0-1
        faithfulness_norm = faithfulness_raw / 5.0

        return mrr * 0.4 + recall * 0.3 + faithfulness_norm * 0.3

    def _generate_markdown_table(self, results: list[dict]) -> str:
        """生成 Markdown 对比表

        Args:
            results: 包含 config, metrics, composite_score 的字典列表

        Returns:
            Markdown 格式表格字符串
        """
        header = "| 配置 | MRR | Recall@K | Precision | Faithfulness | Relevancy | 综合评分 |"
        separator = "| --- | --- | --- | --- | --- | --- | --- |"

        rows = []
        for entry in results:
            config = entry["config"]
            metrics = entry["metrics"]
            score = entry["composite_score"]

            # 配置描述：取 key=value 的简写
            if config:
                config_str = ", ".join(f"{k}={v}" for k, v in config.items())
            else:
                config_str = "baseline"

            mrr = self._fmt(metrics.get("mrr"))
            recall = self._fmt(metrics.get("recall"))
            precision = self._fmt(metrics.get("precision"))
            faithfulness = self._fmt(metrics.get("faithfulness"))
            relevancy = self._fmt(metrics.get("relevancy"))
            composite = f"{score:.4f}"

            row = (
                f"| {config_str} | {mrr} | {recall} | {precision} | "
                f"{faithfulness} | {relevancy} | {composite} |"
            )
            rows.append(row)

        return "\n".join([header, separator] + rows)

    @staticmethod
    def _fmt(value) -> str:
        """格式化指标值，None 显示为 N/A"""
        if value is None:
            return "N/A"
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)


def _generate_config_combinations(comparisons: dict) -> list[dict]:
    """生成配置的笛卡尔积组合

    Args:
        comparisons: {key: [value1, value2, ...], ...} 的比较参数

    Returns:
        所有可能的配置组合列表
    """
    keys = list(comparisons.keys())
    value_lists = [comparisons[k] for k in keys]

    combinations = []
    for combo in itertools.product(*value_lists):
        config_dict = dict(zip(keys, combo))
        combinations.append(config_dict)

    return combinations


# 预置对比方案
_PRESETS = {
    "chunking": {
        "chunking_strategy": ["fixed_size", "recursive", "semantic", "parent_child"],
    },
    "reranker": {
        "rerank_strategy": ["cohere", "bge", "hybrid", "siliconflow"],
    },
    "retrieval": {
        "top_k": [3, 5, 10],
        "rrf_k": [30, 60, 100],
    },
}


def _parse_compare_arg(arg: str) -> tuple:
    """解析 --compare 参数

    格式：key:value1,value2,...
    数值会尝试转为 int 或 float。

    Args:
        arg: 形如 "top_k:3,5,10" 的参数字符串

    Returns:
        (key, [values]) 元组
    """
    if ":" not in arg:
        raise ValueError(f"无效的 --compare 格式: {arg}，应为 key:value1,value2")

    key, values_str = arg.split(":", 1)
    values = []
    for v in values_str.split(","):
        v = v.strip()
        # 尝试类型转换
        try:
            values.append(int(v))
        except ValueError:
            try:
                values.append(float(v))
            except ValueError:
                # 布尔值特殊处理
                if v.lower() == "true":
                    values.append(True)
                elif v.lower() == "false":
                    values.append(False)
                else:
                    values.append(v)

    return key, values


def main():
    parser = argparse.ArgumentParser(
        description="RAG 配置自动比较工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""预置方案:
  --preset chunking    切分策略对比 (fixed_size/recursive/semantic/parent_child)
  --preset reranker    重排序模型对比 (cohere/bge/hybrid/siliconflow)
  --preset retrieval   召回参数对比 (top_k x rrf_k 笛卡尔积)

示例:
  python eval/config_comparator.py \\
      --dataset eval/eval_dataset.json \\
      --compare top_k:3,5,10 \\
      --compare rrf_k:30,60 \\
      --output comparison_report.md

  python eval/config_comparator.py \\
      --dataset eval/eval_dataset.json \\
      --preset retrieval
""",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        required=True,
        help="评估数据集路径",
    )
    parser.add_argument(
        "--compare",
        action="append",
        metavar="key:v1,v2",
        help="配置比较项，格式 key:value1,value2（可重复使用）",
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=list(_PRESETS.keys()),
        help="预置对比方案: chunking / reranker / retrieval",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="comparison_report.md",
        help="输出报告路径 (default: comparison_report.md)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="检索返回文档数量 (default: 5)",
    )

    args = parser.parse_args()

    # 确定比较参数来源：--preset 或 --compare
    if args.preset:
        comparisons = _PRESETS[args.preset]
        print(f"使用预置方案: {args.preset}")
    elif args.compare:
        comparisons = {}
        for arg in args.compare:
            key, values = _parse_compare_arg(arg)
            comparisons[key] = values
    else:
        parser.error("必须指定 --preset 或至少一个 --compare 参数")

    # 生成配置组合
    candidates = _generate_config_combinations(comparisons)

    # 基准配置：取各参数的第一个值
    base_config = {k: v[0] for k, v in comparisons.items()}

    # 从候选中移除基准配置，避免重复评估
    candidates = [c for c in candidates if c != base_config]

    if not candidates:
        print("错误: 未生成任何配置组合")
        sys.exit(1)

    print("=" * 50)
    print("    RAG 配置自动比较")
    print("=" * 50)
    print(f"数据集:      {args.dataset}")
    print(f"Top-K:       {args.top_k}")
    print(f"比较项:      {list(comparisons.keys())}")
    print(f"候选配置数:  {len(candidates)}")
    print(f"基准配置:    {base_config}")
    print()

    # 初始化引擎和评估器
    print("正在初始化 RAG 引擎...")
    engine = RAGEngine(config)
    llm_client = LLMClient(
        config.MIMO_API_KEY,
        config.MIMO_API_BASE,
        config.MIMO_MODEL,
    )
    evaluator = RAGEvaluator(engine, llm_client)

    # 运行比较
    comparator = ConfigComparator(engine, evaluator)
    report = comparator.compare(
        base_config=base_config,
        candidates=candidates,
        dataset_path=args.dataset,
        top_k=args.top_k,
    )

    # 输出报告
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# RAG 配置比较报告\n\n")
        f.write(report.summary_table)
        f.write("\n\n")

        # 写入最优配置详情
        best = report.best_config
        f.write("## 最优配置\n\n")
        f.write(f"**综合评分**: {best['composite_score']:.4f}\n\n")
        f.write("**配置参数**:\n\n")
        for k, v in best["config"].items():
            f.write(f"- `{k}`: {v}\n")
        f.write("\n")

        # 写入详细指标
        f.write("## 详细指标\n\n")
        all_results = [report.baseline] + report.candidates
        for i, entry in enumerate(all_results):
            label = "基准" if i == 0 else f"候选 {i}"
            cfg_str = ", ".join(f"{k}={v}" for k, v in entry["config"].items())
            f.write(f"### {label}: {cfg_str}\n\n")
            m = entry["metrics"]
            f.write(f"- MRR: {m.get('mrr', 'N/A')}\n")
            f.write(f"- Recall@K: {m.get('recall', 'N/A')}\n")
            f.write(f"- Precision: {m.get('precision', 'N/A')}\n")
            f.write(f"- Faithfulness: {m.get('faithfulness', 'N/A')}\n")
            f.write(f"- Relevancy: {m.get('relevancy', 'N/A')}\n")
            f.write(f"- 综合评分: {entry['composite_score']:.4f}\n\n")

    # 终端输出表格
    print(report.summary_table)
    print()
    print(f"最优配置: {report.best_config['config']}")
    print(f"综合评分: {report.best_config['composite_score']:.4f}")
    print(f"\n报告已保存到: {output_path}")


if __name__ == "__main__":
    main()
