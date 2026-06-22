"""RAG A/B 测试框架

对两组配置在同一数据集上并行评估，使用配对 t 检验判断指标差异是否显著。
支持任意配置参数对比（切分策略、重排序模型、召回参数等）。

运行方式：
    cd backend && python eval/ab_runner.py \\
        --dataset eval/eval_dataset.json \\
        --config-a "rerank_strategy:cohere" \\
        --config-b "rerank_strategy:bge" \\
        --output ab_report.md
"""

import sys
import json
import os
import argparse
from pathlib import Path
from scipy import stats

project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

os.chdir(project_root)

from core.config import AppSettings
from core.rag_engine import RAGEngine
from core.llm_client import LLMClient
from eval.evaluator import RAGEvaluator
from eval.metrics import ndcg_at_k, map_score


def _parse_config_arg(arg: str) -> tuple:
    """解析 key:value 格式的配置参数"""
    if ":" not in arg:
        raise ValueError(f"无效格式: {arg}，应为 key:value")
    key, value = arg.split(":", 1)
    value = value.strip()
    # 类型转换
    try:
        value = int(value)
    except ValueError:
        try:
            value = float(value)
        except ValueError:
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
    return key.strip(), value


def _build_settings_with_overrides(overrides: dict) -> AppSettings:
    """通过环境变量注入覆盖参数，构建新的 AppSettings"""
    env_backup = {}
    for k, v in overrides.items():
        env_backup[k] = os.environ.get(k)
        os.environ[k] = str(v)
    settings = AppSettings()
    for k, orig in env_backup.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig
    return settings


def _eval_single_config(dataset: list, overrides: dict, top_k: int) -> list[dict]:
    """用指定配置运行评估，返回逐样本指标列表"""
    settings = _build_settings_with_overrides(overrides)
    engine = RAGEngine(settings)
    llm_client = LLMClient(settings.MIMO_API_KEY, settings.MIMO_API_BASE, settings.MIMO_MODEL)
    evaluator = RAGEvaluator(engine, llm_client)

    per_sample = []
    for sample in dataset:
        question = sample["question"]
        expected_sources = sample.get("expected_sources", [])
        expected_keywords = sample.get("expected_keywords", [])
        reference_answer = sample.get("reference_answer", "")

        rag_result = engine.full_retrieve(question)
        contexts = rag_result["documents"]
        contexts_meta = rag_result["metadatas"]

        # 检索指标
        ret = evaluator.evaluate_retrieval(question, expected_sources, top_k, retrieval_results=rag_result)

        # 生成回答 + 评估
        prompt = engine.build_prompt(question, [
            {"text": doc, "metadata": meta} for doc, meta in zip(contexts, contexts_meta)
        ])
        answer = llm_client.generate(prompt)
        gen = evaluator.evaluate_generation(question, answer, contexts, reference_answer)

        # 额外指标
        retrieved = ret.get("retrieved_sources", [])
        expected_set = set(expected_sources)
        keyword_hits = sum(1 for kw in expected_keywords if kw in answer)
        kw_coverage = keyword_hits / len(expected_keywords) if expected_keywords else None

        per_sample.append({
            "mrr": ret.get("mrr") or 0.0,
            "recall": ret.get("recall") or 0.0,
            "ndcg": ndcg_at_k(retrieved, expected_set, k=top_k),
            "map": map_score(retrieved, expected_set),
            "faithfulness": gen.get("faithfulness") or 0,
            "relevancy": gen.get("relevancy") or 0,
            "keyword_coverage": kw_coverage or 0.0,
        })

    return per_sample


def run_ab_test(
    dataset_path: str,
    config_a: dict,
    config_b: dict,
    top_k: int = 5,
) -> dict:
    """运行 A/B 测试

    对两组配置在同一数据集上评估，使用配对 t 检验判断差异显著性。

    Args:
        dataset_path: 评估数据集路径
        config_a: A 组配置覆盖 {key: value}
        config_b: B 组配置覆盖 {key: value}
        top_k: 检索返回文档数

    Returns:
        包含逐指标对比、p 值、显著性判定的报告
    """
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"正在运行 A 组评估: {config_a}")
    samples_a = _eval_single_config(dataset, config_a, top_k)

    print(f"正在运行 B 组评估: {config_b}")
    samples_b = _eval_single_config(dataset, config_b, top_k)

    # 配对 t 检验
    metrics_to_test = ["mrr", "recall", "ndcg", "map", "faithfulness", "relevancy", "keyword_coverage"]
    comparison = {}

    for metric in metrics_to_test:
        values_a = [s[metric] for s in samples_a]
        values_b = [s[metric] for s in samples_b]

        mean_a = sum(values_a) / len(values_a)
        mean_b = sum(values_b) / len(values_b)
        diff = mean_b - mean_a

        # 配对 t 检验
        if all(a == b for a, b in zip(values_a, values_b)):
            # 所有差值为 0，无法做 t 检验
            p_value = 1.0
            significant = False
        else:
            t_stat, p_value = stats.ttest_rel(values_a, values_b)
            significant = p_value < 0.05

        comparison[metric] = {
            "mean_a": round(mean_a, 4),
            "mean_b": round(mean_b, 4),
            "diff": round(diff, 4),
            "diff_pct": round(diff / mean_a * 100, 2) if mean_a != 0 else None,
            "p_value": round(p_value, 4),
            "significant": significant,
        }

    return {
        "config_a": config_a,
        "config_b": config_b,
        "sample_count": len(dataset),
        "comparison": comparison,
        "per_sample_a": samples_a,
        "per_sample_b": samples_b,
    }


def generate_report(result: dict) -> str:
    """生成 Markdown 报告"""
    comp = result["comparison"]
    cfg_a = result["config_a"]
    cfg_b = result["config_b"]

    lines = ["# A/B 测试报告\n"]

    lines.append(f"- **A 组配置**: {cfg_a}")
    lines.append(f"- **B 组配置**: {cfg_b}")
    lines.append(f"- **样本数**: {result['sample_count']}")
    lines.append(f"- **显著性阈值**: p < 0.05\n")

    # 对比表
    lines.append("## 指标对比\n")
    lines.append("| 指标 | A 组均值 | B 组均值 | 差异 | 差异% | p 值 | 显著 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    for metric, data in comp.items():
        sig_mark = "**是**" if data["significant"] else "否"
        diff_pct = f"{data['diff_pct']:.1f}%" if data["diff_pct"] is not None else "N/A"
        lines.append(
            f"| {metric} | {data['mean_a']:.4f} | {data['mean_b']:.4f} | "
            f"{data['diff']:+.4f} | {diff_pct} | {data['p_value']:.4f} | {sig_mark} |"
        )

    lines.append("")

    # 显著性总结
    sig_metrics = [m for m, d in comp.items() if d["significant"]]
    if sig_metrics:
        lines.append("## 显著性总结\n")
        lines.append(f"B 组在以下指标上与 A 组有**统计显著差异**：{', '.join(sig_metrics)}\n")
    else:
        lines.append("## 显著性总结\n")
        lines.append("两组配置在所有指标上均无统计显著差异（p >= 0.05）。\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="RAG A/B 测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python eval/ab_runner.py \\
      --dataset eval/eval_dataset.json \\
      --config-a "rerank_strategy:cohere" \\
      --config-b "rerank_strategy:bge"

  python eval/ab_runner.py \\
      --dataset eval/eval_dataset.json \\
      --config-a "top_k:3" \\
      --config-b "top_k:10"

  python eval/ab_runner.py \\
      --dataset eval/eval_dataset.json \\
      --config-a "chunking_strategy:fixed_size" \\
      --config-b "chunking_strategy:semantic"
""",
    )
    parser.add_argument("--dataset", type=str, required=True, help="评估数据集路径")
    parser.add_argument("--config-a", type=str, required=True, action="append",
                        help="A 组配置 key:value（可重复指定多参数）")
    parser.add_argument("--config-b", type=str, required=True, action="append",
                        help="B 组配置 key:value（可重复指定多参数）")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回文档数 (default: 5)")
    parser.add_argument("--output", type=str, default="ab_report.md", help="输出报告路径")

    args = parser.parse_args()

    # 解析配置
    config_a = dict(_parse_config_arg(a) for a in args.config_a)
    config_b = dict(_parse_config_arg(b) for b in args.config_b)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"错误: 数据集不存在: {dataset_path}")
        sys.exit(1)

    print("=" * 50)
    print("    RAG A/B 测试")
    print("=" * 50)
    print(f"数据集: {args.dataset}")
    print(f"A 组:   {config_a}")
    print(f"B 组:   {config_b}")
    print(f"Top-K:  {args.top_k}")
    print()

    result = run_ab_test(str(args.dataset), config_a, config_b, top_k=args.top_k)

    # 生成报告
    report_md = generate_report(result)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 保存 JSON 详情
    json_output = {
        "config_a": result["config_a"],
        "config_b": result["config_b"],
        "sample_count": result["sample_count"],
        "comparison": result["comparison"],
    }
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(report_md)
    print(f"\n报告已保存到: {output_path}")
    print(f"详细数据已保存到: {json_path}")


if __name__ == "__main__":
    main()
