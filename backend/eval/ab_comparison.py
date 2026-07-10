"""A/B 对比脚本：对比优化前后的 RAG 效果

用法：
    cd backend
    python eval/ab_comparison.py \
      --baseline eval/baseline_report.json \
      --optimized eval/optimized_report.json \
      --output eval/ab_comparison.md
"""

import json
import argparse
from pathlib import Path


def load_report(path: str) -> dict:
    """加载评估报告"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calc_improvement(baseline: float, optimized: float) -> tuple[float, str]:
    """计算提升幅度"""
    if baseline == 0:
        return 0.0, "N/A"
    improvement = (optimized - baseline) / baseline * 100
    if improvement > 0:
        return improvement, f"+{improvement:.1f}%"
    else:
        return improvement, f"{improvement:.1f}%"


def generate_comparison_table(baseline: dict, optimized: dict) -> str:
    """生成对比表格"""
    lines = []
    lines.append("# RAG 系统 A/B 对比报告\n")
    lines.append(f"**样本数**: {baseline.get('total_samples', 'N/A')}\n")

    # 检索指标对比
    lines.append("## 检索效果对比\n")
    lines.append("| 指标 | Baseline | Optimized | 提升 |")
    lines.append("|------|----------|-----------|------|")

    retrieval_metrics = [
        ("MRR@10", "mrr"),
        ("Hit Rate", "hit_rate"),
        ("Recall@K", "recall_at_k"),
        ("Precision", "precision"),
    ]

    baseline_ret = baseline.get("retrieval", {})
    optimized_ret = optimized.get("retrieval", {})

    for label, key in retrieval_metrics:
        base_val = baseline_ret.get(key)
        opt_val = optimized_ret.get(key)
        if base_val is not None and opt_val is not None:
            _, improvement_str = calc_improvement(base_val, opt_val)
            lines.append(f"| {label} | {base_val:.4f} | {opt_val:.4f} | **{improvement_str}** |")

    # 生成质量对比
    lines.append("\n## 生成质量对比\n")
    lines.append("| 指标 | Baseline | Optimized | 提升 |")
    lines.append("|------|----------|-----------|------|")

    generation_metrics = [
        ("Faithfulness", "faithfulness"),
        ("Answer Relevancy", "relevancy"),
    ]

    baseline_gen = baseline.get("generation", {})
    optimized_gen = optimized.get("generation", {})

    for label, key in generation_metrics:
        base_val = baseline_gen.get(key)
        opt_val = optimized_gen.get(key)
        if base_val is not None and opt_val is not None:
            _, improvement_str = calc_improvement(base_val, opt_val)
            lines.append(f"| {label} | {base_val:.2f}/5 | {opt_val:.2f}/5 | **{improvement_str}** |")

    # 关键词覆盖率
    base_kw = baseline.get("keyword_coverage")
    opt_kw = optimized.get("keyword_coverage")
    if base_kw is not None and opt_kw is not None:
        _, improvement_str = calc_improvement(base_kw, opt_kw)
        lines.append(f"\n**关键词覆盖率**: {base_kw:.2f} → {opt_kw:.2f} ({improvement_str})\n")

    return "\n".join(lines)


def generate_resume_metrics(baseline: dict, optimized: dict) -> str:
    """生成简历可用的量化数据"""
    lines = []
    lines.append("\n## 简历可用数据\n")

    baseline_ret = baseline.get("retrieval", {})
    optimized_ret = optimized.get("retrieval", {})
    baseline_gen = baseline.get("generation", {})
    optimized_gen = optimized.get("generation", {})

    # MRR 提升
    base_mrr = baseline_ret.get("mrr", 0)
    opt_mrr = optimized_ret.get("mrr", 0)
    if base_mrr and opt_mrr:
        _, mrr_improve = calc_improvement(base_mrr, opt_mrr)
        lines.append(f"- **MRR@10**: {base_mrr:.2f} → {opt_mrr:.2f} ({mrr_improve})")

    # Hit Rate 提升
    base_hit = baseline_ret.get("hit_rate", 0)
    opt_hit = optimized_ret.get("hit_rate", 0)
    if base_hit and opt_hit:
        _, hit_improve = calc_improvement(base_hit, opt_hit)
        lines.append(f"- **Hit Rate**: {base_hit*100:.0f}% → {opt_hit*100:.0f}% ({hit_improve})")

    # Faithfulness
    opt_faith = optimized_gen.get("faithfulness", 0)
    if opt_faith:
        lines.append(f"- **Faithfulness**: {opt_faith:.2f}/5")

    # Answer Relevancy
    opt_relevancy = optimized_gen.get("relevancy", 0)
    if opt_relevancy:
        lines.append(f"- **Answer Relevancy**: {opt_relevancy:.2f}/5")

    lines.append("\n### 推荐简历写法\n")
    lines.append("```")
    lines.append("• 优化检索链路（多路召回 + Rerank + 二次检索），"
                 f"MRR@10 提升 {mrr_improve if base_mrr and opt_mrr else 'X%'}，"
                 f"Hit Rate 提升 {hit_improve if base_hit and opt_hit else 'Y%'}")
    lines.append("```")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="RAG A/B 对比工具")
    parser.add_argument("--baseline", required=True, help="Baseline 报告路径")
    parser.add_argument("--optimized", required=True, help="Optimized 报告路径")
    parser.add_argument("--output", default="eval/ab_comparison.md", help="输出文件路径")

    args = parser.parse_args()

    baseline = load_report(args.baseline)
    optimized = load_report(args.optimized)

    # 生成对比报告
    report = generate_comparison_table(baseline, optimized)
    report += generate_resume_metrics(baseline, optimized)

    # 保存
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ A/B 对比报告已生成: {output_path}")
    print("\n" + "="*60)
    print(report)


if __name__ == "__main__":
    main()
