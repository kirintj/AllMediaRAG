"""生成简历可用的量化数据

汇总 A/B 对比和性能测试结果，输出简历可用的格式化数据

用法：
    cd backend
    python eval/generate_resume_data.py \
      --eval-report eval/ab_comparison.md \
      --perf-report eval/performance_report.json \
      --output eval/resume_metrics.md
"""

import json
import argparse
from pathlib import Path


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_markdown(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate_resume_data(eval_report: str, perf_report: dict) -> str:
    """生成简历可用数据"""

    lines = []
    lines.append("# 简历量化数据汇总\n")
    lines.append("---\n")

    # ========== 检索效果 ==========
    lines.append("## 1. 检索效果优化\n")
    lines.append("### 可写入简历的指标\n")

    # 从性能报告提取
    if perf_report:
        retrieval = perf_report.get("retrieval_latency", {})
        e2e = perf_report.get("e2e_latency", {})
        cache = perf_report.get("cache_performance", {})

        lines.append("#### 响应时间")
        if e2e.get("mean_ms"):
            mean_s = e2e["mean_ms"] / 1000
            lines.append(f"- 平均端到端响应时间: **{mean_s:.2f}s**")
            lines.append(f"- P95 响应时间: **{e2e.get('p95_ms', 0)/1000:.2f}s**")

        if retrieval.get("mean_ms"):
            lines.append(f"- 纯检索延迟: **{retrieval['mean_ms']:.0f}ms**")

        lines.append("\n#### 缓存性能")
        if cache.get("hit_rate") is not None:
            lines.append(f"- 缓存命中率: **{cache['hit_rate']*100:.1f}%**")
        if cache.get("speedup"):
            lines.append(f"- 缓存加速比: **{cache['speedup']:.1f}x**")

    lines.append("\n")
    lines.append(eval_report)

    # ========== 生成简历模板 ==========
    lines.append("\n---\n")
    lines.append("## 2. 简历写法模板\n")

    lines.append("### 模板 A: 有 Baseline 对比（最推荐）\n")
    lines.append("```markdown")
    lines.append("多模态 RAG 知问系统 | 核心开发者")
    lines.append("")
    lines.append("• 设计离线-在线全链路 RAG 系统，支持 PDF/MD/图文等多模态文档解析与索引")
    lines.append("")
    lines.append("• 优化检索链路（多路召回 + Rerank + 引用核查 + 低置信度二次检索），")
    lines.append("  MRR@10 提升 X%，Hit Rate 提升 Y%")
    lines.append("")
    lines.append("• 基于 RAGAS 搭建自动化评估框架，Faithfulness 达到 X.XX，")
    lines.append("  Answer Relevancy 达到 X.XX")
    lines.append("")
    lines.append("• 实现分层缓存 + 增量索引机制，平均响应时间 X.Xs，")
    lines.append("  缓存命中率 XX%，支持 N+ 文档热更新")
    lines.append("```\n")

    lines.append("### 模板 B: 仅绝对值\n")
    lines.append("```markdown")
    lines.append("多模态 RAG 知问系统 | 核心开发者")
    lines.append("")
    lines.append("• 实现多路召回（向量 + BM25）+ Rerank 精排 + 引用核查机制，")
    lines.append("  MRR@10 达到 0.XX，Hit Rate 达到 XX%")
    lines.append("")
    lines.append("• RAGAS 评估：Faithfulness 0.XX，Answer Relevancy 0.XX，")
    lines.append("  Context Precision 0.XX")
    lines.append("")
    lines.append("• 分层缓存机制：重复查询响应 <100ms，缓存命中率 XX%")
    lines.append("• 增量索引：支持 N+ 文档实时同步，单文档更新 <5s")
    lines.append("```\n")

    lines.append("### 模板 C: 技术关键词版本（适合 ATS 筛选）\n")
    lines.append("```markdown")
    lines.append("• RAG / Retrieval-Augmented Generation 全链路优化")
    lines.append("• 多路召回（Dense Retrieval + BM25）、Cross-Encoder Reranking")
    lines.append("• ChromaDB 向量数据库、FAISS 索引优化")
    lines.append("• OCR + VLM 多模态文档解析")
    lines.append("• RAGAS 评估框架、自动化 A/B 测试")
    lines.append("• 分布式缓存、增量索引、流式响应")
    lines.append("```\n")

    # ========== 数据填写指南 ==========
    lines.append("---\n")
    lines.append("## 3. 数据填写指南\n")
    lines.append("运行以下命令获取填入数据：\n")
    lines.append("```bash")
    lines.append("# 1. 运行 baseline 评估")
    lines.append("python eval/run_eval.py --dataset extended --framework both --output eval/baseline.json")
    lines.append("")
    lines.append("# 2. 运行优化后评估")
    lines.append("python eval/run_eval.py --dataset extended --framework both --output eval/optimized.json")
    lines.append("")
    lines.append("# 3. 生成对比数据")
    lines.append("python eval/ab_comparison.py --baseline eval/baseline.json --optimized eval/optimized.json")
    lines.append("")
    lines.append("# 4. 运行性能测试")
    lines.append("python eval/performance_benchmark.py --dataset eval/eval_dataset_extended.json")
    lines.append("```\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="生成简历量化数据")
    parser.add_argument("--eval-report", help="A/B 对比报告路径")
    parser.add_argument("--perf-report", help="性能测试报告路径")
    parser.add_argument("--output", default="eval/resume_metrics.md", help="输出路径")

    args = parser.parse_args()

    # 加载报告
    eval_report = load_markdown(args.eval_report) if args.eval_report else ""
    perf_report = load_json(args.perf_report) if args.perf_report else {}

    # 生成数据
    resume_data = generate_resume_data(eval_report, perf_report)

    # 保存
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(resume_data)

    print(f"✅ 简历数据已生成: {output_path}")
    print("\n" + "="*60)
    print(resume_data)


if __name__ == "__main__":
    main()
