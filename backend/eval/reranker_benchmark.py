"""重排序模型批量对比评测脚本

自动遍历多种重排序策略，量化不同重排序器对检索和生成质量的影响，
同时采集重排序延迟，输出 Markdown 对比报告。

运行方式：
    cd backend && python eval/reranker_benchmark.py \
        --dataset eval/eval_dataset.json \
        --strategies cohere,bge,hybrid,siliconflow \
        --output reranker_report.md
"""

import sys
import json
import time
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

import os
os.chdir(project_root)

from core.config import AppSettings
from core.rag_engine import RAGEngine
from core.llm_client import LLMClient
from eval.evaluator import RAGEvaluator
from eval.metrics import ndcg_at_k, map_score


def run_reranker_benchmark(
    dataset_path: str,
    strategies: list[str],
    top_k: int = 5,
) -> dict:
    """运行重排序策略批量对比

    Args:
        dataset_path: 评估数据集路径
        strategies: 待比较的重排序策略列表
        top_k: 检索返回文档数

    Returns:
        包含各策略评估结果和延迟数据的字典
    """
    results = []

    for strategy in strategies:
        print(f"\n{'='*40}")
        print(f"重排序策略: {strategy}")
        print(f"{'='*40}")

        # 设置重排序策略到环境变量
        env_backup = os.environ.get("RERANK_STRATEGY")
        os.environ["RERANK_STRATEGY"] = strategy

        try:
            settings = AppSettings()
            print(f"  初始化引擎（rerank={strategy}）...")
            engine = RAGEngine(settings)
            llm_client = LLMClient(settings.MIMO_API_KEY, settings.MIMO_API_BASE, settings.MIMO_MODEL)
            evaluator = RAGEvaluator(engine, llm_client)

            # 逐样本评估并采集延迟
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)

            retrieval_latencies = []
            sample_results = []
            total_start = time.perf_counter()

            for i, sample in enumerate(dataset, 1):
                question = sample["question"]
                expected_sources = sample.get("expected_sources", [])

                # 测量检索延迟（含重排序）
                t0 = time.perf_counter()
                rag_result = engine.full_retrieve(question)
                latency_ms = (time.perf_counter() - t0) * 1000
                retrieval_latencies.append(latency_ms)

                # 检索指标
                retrieval_result = evaluator.evaluate_retrieval(
                    question, expected_sources, top_k, retrieval_results=rag_result
                )

                # 生成回答
                contexts = rag_result["documents"]
                contexts_meta = rag_result["metadatas"]
                prompt = engine.build_prompt(question, [
                    {"text": doc, "metadata": meta}
                    for doc, meta in zip(contexts, contexts_meta)
                ])
                answer = llm_client.generate(prompt)

                # 生成评估
                gen_result = evaluator.evaluate_generation(question, answer, contexts,
                                                           sample.get("reference_answer", ""))

                sample_results.append({
                    "question": question,
                    "retrieval": retrieval_result,
                    "generation": gen_result,
                    "latency_ms": latency_ms,
                })

                print(f"  [{i}/{len(dataset)}] {question[:40]}... "
                      f"MRR={retrieval_result.get('mrr', 0):.2f} "
                      f"延迟={latency_ms:.0f}ms")

            total_elapsed = time.perf_counter() - total_start

            # 计算 NDCG、MAP
            ndcg_values = []
            map_values = []
            for i, sr in enumerate(sample_results):
                retrieved = sr["retrieval"].get("retrieved_sources", [])
                expected_set = set(dataset[i].get("expected_sources", []))
                ndcg_values.append(ndcg_at_k(retrieved, expected_set, k=top_k))
                map_values.append(map_score(retrieved, expected_set))

            # 汇总指标
            recalls = [sr["retrieval"]["recall"] for sr in sample_results if sr["retrieval"]["recall"] is not None]
            mrrs = [sr["retrieval"]["mrr"] for sr in sample_results if sr["retrieval"]["mrr"] is not None]
            faith_scores = [sr["generation"]["faithfulness"] for sr in sample_results if sr["generation"]["faithfulness"] is not None]
            relevancy_scores = [sr["generation"]["relevancy"] for sr in sample_results if sr["generation"]["relevancy"] is not None]

            entry = {
                "strategy": strategy,
                "retrieval": {
                    "recall_at_k": sum(recalls) / len(recalls) if recalls else None,
                    "mrr": sum(mrrs) / len(mrrs) if mrrs else None,
                    "ndcg_at_k": sum(ndcg_values) / len(ndcg_values) if ndcg_values else None,
                    "map": sum(map_values) / len(map_values) if map_values else None,
                },
                "generation": {
                    "faithfulness": sum(faith_scores) / len(faith_scores) if faith_scores else None,
                    "relevancy": sum(relevancy_scores) / len(relevancy_scores) if relevancy_scores else None,
                },
                "latency": {
                    "avg_ms": sum(retrieval_latencies) / len(retrieval_latencies),
                    "p50_ms": sorted(retrieval_latencies)[len(retrieval_latencies) // 2],
                    "p95_ms": sorted(retrieval_latencies)[int(len(retrieval_latencies) * 0.95)],
                    "total_sec": round(total_elapsed, 2),
                },
                "details": sample_results,
            }
            results.append(entry)

            ret = entry["retrieval"]
            lat = entry["latency"]
            print(f"  => MRR={ret['mrr'] or 0:.4f}  "
                  f"Recall={ret['recall_at_k'] or 0:.4f}  "
                  f"NDCG={ret['ndcg_at_k'] or 0:.4f}  "
                  f"延迟avg={lat['avg_ms']:.0f}ms  "
                  f"总耗时={lat['total_sec']:.1f}s")

        finally:
            # 恢复环境变量
            if env_backup is None:
                os.environ.pop("RERANK_STRATEGY", None)
            else:
                os.environ["RERANK_STRATEGY"] = env_backup

    return {"results": results}


def generate_report(benchmark: dict) -> str:
    """生成 Markdown 对比报告"""
    results = benchmark["results"]

    lines = ["# 重排序模型对比报告\n"]

    # 主对比表
    lines.append("| 策略 | MRR | Recall@K | NDCG@K | MAP | Faithfulness | 延迟avg(ms) | 延迟P95(ms) |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    for r in results:
        ret = r["retrieval"]
        gen = r["generation"]
        lat = r["latency"]
        mrr = f"{ret.get('mrr', 0) or 0:.4f}"
        recall = f"{ret.get('recall_at_k', 0) or 0:.4f}"
        ndcg = f"{ret.get('ndcg_at_k', 0) or 0:.4f}"
        map_val = f"{ret.get('map', 0) or 0:.4f}"
        faith = f"{gen.get('faithfulness', 'N/A')}"
        avg_lat = f"{lat['avg_ms']:.0f}"
        p95_lat = f"{lat['p95_ms']:.0f}"
        lines.append(f"| {r['strategy']} | {mrr} | {recall} | {ndcg} | {map_val} | {faith} | {avg_lat} | {p95_lat} |")

    lines.append("")

    # 延迟详情
    lines.append("## 延迟统计\n")
    for r in results:
        lat = r["latency"]
        lines.append(f"### {r['strategy']}")
        lines.append(f"- 平均延迟: {lat['avg_ms']:.1f}ms")
        lines.append(f"- P50 延迟: {lat['p50_ms']:.1f}ms")
        lines.append(f"- P95 延迟: {lat['p95_ms']:.1f}ms")
        lines.append(f"- 总耗时: {lat['total_sec']:.1f}s")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="重排序模型批量对比评测")
    parser.add_argument("--dataset", type=str, required=True, help="评估数据集路径")
    parser.add_argument("--strategies", type=str, default="cohere,bge,hybrid,siliconflow",
                        help="待比较策略，逗号分隔 (default: all)")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回文档数 (default: 5)")
    parser.add_argument("--output", type=str, default="reranker_report.md", help="输出报告路径")

    args = parser.parse_args()
    strategies = [s.strip() for s in args.strategies.split(",")]

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"错误: 数据集不存在: {dataset_path}")
        sys.exit(1)

    print("=" * 50)
    print("    重排序模型批量对比评测")
    print("=" * 50)
    print(f"数据集:   {args.dataset}")
    print(f"策略:     {strategies}")
    print(f"Top-K:    {args.top_k}")

    benchmark = run_reranker_benchmark(str(args.dataset), strategies, top_k=args.top_k)

    if not benchmark["results"]:
        print("错误: 没有成功的评估结果")
        sys.exit(1)

    # 生成报告
    report_md = generate_report(benchmark)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 保存 JSON 详情（不含 details 中的大量数据，只保留汇总）
    json_summary = {
        "results": [
            {k: v for k, v in r.items() if k != "details"}
            for r in benchmark["results"]
        ]
    }
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_summary, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(report_md)
    print(f"\n报告已保存到: {output_path}")
    print(f"详细数据已保存到: {json_path}")


if __name__ == "__main__":
    main()
