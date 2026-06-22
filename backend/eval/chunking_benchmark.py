"""切分策略批量对比评测脚本

自动遍历多种切分策略，量化不同策略对检索和生成质量的影响，
输出 Markdown 对比报告。

运行方式：
    cd backend && python eval/chunking_benchmark.py \
        --dataset eval/eval_dataset.json \
        --strategies fixed_size,recursive,semantic,parent_child \
        --output chunking_report.md
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


# 每种策略的推荐默认参数
STRATEGY_DEFAULTS = {
    "fixed_size": {"CHUNKING_STRATEGY": "fixed_size", "CHUNK_SIZE": 512, "CHUNK_OVERLAP": 50},
    "recursive": {"CHUNKING_STRATEGY": "recursive", "CHUNK_SIZE": 512, "CHUNK_OVERLAP": 50},
    "semantic": {"CHUNKING_STRATEGY": "semantic", "SEMANTIC_CHUNK_PERCENTILE": 25},
    "parent_child": {"CHUNKING_STRATEGY": "parent_child", "PC_CHILD_SENTENCES": 3, "PC_PARENT_GROUPS": 4},
}


def _apply_config_to_settings(settings: AppSettings, overrides: dict) -> AppSettings:
    """创建 AppSettings 副本并应用覆盖参数"""
    # 从当前 settings 构造 env 覆盖
    env_overrides = {k: str(v) for k, v in overrides.items()}
    original_env = {}
    for k, v in env_overrides.items():
        original_env[k] = os.environ.get(k)
        os.environ[k] = v
    new_settings = AppSettings()
    # 恢复环境
    for k, orig in original_env.items():
        if orig is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = orig
    return new_settings


def _compute_chunk_stats(engine, dataset_path: str) -> dict:
    """计算当前切分策略下的块统计信息（块数量、平均大小）"""
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    chunk_counts = []
    chunk_sizes = []
    for sample in dataset[:5]:  # 采样前 5 条以减少耗时
        question = sample["question"]
        results = engine.retrieve(question, top_k=10)
        docs = results.get("documents", [])
        chunk_counts.append(len(docs))
        chunk_sizes.extend(len(d) for d in docs)

    return {
        "avg_chunks_retrieved": sum(chunk_counts) / len(chunk_counts) if chunk_counts else 0,
        "avg_chunk_size": sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0,
    }


def run_chunking_benchmark(
    dataset_path: str,
    strategies: list[str],
    top_k: int = 5,
) -> dict:
    """运行切分策略批量对比

    Args:
        dataset_path: 评估数据集路径
        strategies: 待比较的策略名称列表
        top_k: 检索返回文档数

    Returns:
        包含各策略评估结果和对比表的字典
    """
    results = []

    for strategy in strategies:
        if strategy not in STRATEGY_DEFAULTS:
            print(f"  [跳过] 未知策略: {strategy}")
            continue

        params = STRATEGY_DEFAULTS[strategy]
        print(f"\n{'='*40}")
        print(f"策略: {strategy}")
        print(f"参数: {params}")
        print(f"{'='*40}")

        # 应用策略参数到环境变量
        env_backup = {}
        for k, v in params.items():
            env_backup[k] = os.environ.get(k)
            os.environ[k] = str(v)

        try:
            settings = AppSettings()
            print(f"  初始化引擎（策略={strategy}）...")
            engine = RAGEngine(settings)
            llm_client = LLMClient(settings.MIMO_API_KEY, settings.MIMO_API_BASE, settings.MIMO_MODEL)
            evaluator = RAGEvaluator(engine, llm_client)

            # 运行评估
            print(f"  运行评估...")
            t0 = time.perf_counter()
            report = evaluator.run(dataset_path, top_k=top_k)
            elapsed = time.perf_counter() - t0

            # 计算额外指标（NDCG、MAP）需要逐样本数据
            details = report.get("details", [])
            ndcg_values = []
            map_values = []
            for detail in details:
                retrieved = detail.get("retrieval", {}).get("retrieved_sources", [])
                expected = detail.get("question", "")  # 占位，下面从数据集读取
                # 从数据集读取 expected_sources
                # evaluator.run 已计算过，这里从 details 中取
                # 注意：details 中没有 expected_sources，需要重新加载
                pass

            # 重新加载数据集获取 expected_sources
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
            for i, detail in enumerate(details):
                retrieved = detail.get("retrieval", {}).get("retrieved_sources", [])
                expected_set = set(dataset[i].get("expected_sources", []))
                ndcg_values.append(ndcg_at_k(retrieved, expected_set, k=top_k))
                map_values.append(map_score(retrieved, expected_set))

            avg_ndcg = sum(ndcg_values) / len(ndcg_values) if ndcg_values else 0.0
            avg_map = sum(map_values) / len(map_values) if map_values else 0.0

            # 块统计
            chunk_stats = _compute_chunk_stats(engine, dataset_path)

            entry = {
                "strategy": strategy,
                "params": params,
                "retrieval": report.get("retrieval", {}),
                "generation": report.get("generation", {}),
                "ndcg_at_k": avg_ndcg,
                "map": avg_map,
                "chunk_stats": chunk_stats,
                "eval_time_sec": round(elapsed, 2),
            }
            results.append(entry)

            retrieval = report.get("retrieval", {})
            generation = report.get("generation", {})
            print(f"  MRR={retrieval.get('mrr', 'N/A'):.4f}  "
                  f"Recall={retrieval.get('recall_at_k', 'N/A'):.4f}  "
                  f"NDCG={avg_ndcg:.4f}  "
                  f"Faithfulness={generation.get('faithfulness', 'N/A')}  "
                  f"耗时={elapsed:.1f}s")

        finally:
            # 恢复环境变量
            for k, orig in env_backup.items():
                if orig is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = orig

    return {"results": results}


def generate_report(benchmark: dict) -> str:
    """生成 Markdown 对比报告"""
    results = benchmark["results"]

    lines = ["# 切分策略对比报告\n"]

    # 主对比表
    lines.append("| 策略 | MRR | Recall@K | NDCG@K | MAP | Faithfulness | 平均块大小 | 耗时(s) |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")

    for r in results:
        ret = r["retrieval"]
        gen = r["generation"]
        cs = r["chunk_stats"]
        mrr = f"{ret.get('mrr', 0) or 0:.4f}"
        recall = f"{ret.get('recall_at_k', 0) or 0:.4f}"
        ndcg = f"{r['ndcg_at_k']:.4f}"
        map_val = f"{r['map']:.4f}"
        faith = f"{gen.get('faithfulness', 'N/A')}"
        avg_size = f"{cs['avg_chunk_size']:.0f}"
        t = f"{r['eval_time_sec']:.1f}"
        lines.append(f"| {r['strategy']} | {mrr} | {recall} | {ndcg} | {map_val} | {faith} | {avg_size} | {t} |")

    lines.append("")

    # 参数详情
    lines.append("## 参数配置\n")
    for r in results:
        lines.append(f"### {r['strategy']}")
        for k, v in r["params"].items():
            lines.append(f"- `{k}`: {v}")
        cs = r["chunk_stats"]
        lines.append(f"- 平均召回块数: {cs['avg_chunks_retrieved']:.1f}")
        lines.append(f"- 平均块大小: {cs['avg_chunk_size']:.0f} 字符")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="切分策略批量对比评测")
    parser.add_argument("--dataset", type=str, required=True, help="评估数据集路径")
    parser.add_argument("--strategies", type=str, default="fixed_size,recursive,semantic,parent_child",
                        help="待比较策略，逗号分隔 (default: all)")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回文档数 (default: 5)")
    parser.add_argument("--output", type=str, default="chunking_report.md", help="输出报告路径")

    args = parser.parse_args()
    strategies = [s.strip() for s in args.strategies.split(",")]

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"错误: 数据集不存在: {dataset_path}")
        sys.exit(1)

    print("=" * 50)
    print("    切分策略批量对比评测")
    print("=" * 50)
    print(f"数据集:   {args.dataset}")
    print(f"策略:     {strategies}")
    print(f"Top-K:    {args.top_k}")

    benchmark = run_chunking_benchmark(str(args.dataset), strategies, top_k=args.top_k)

    if not benchmark["results"]:
        print("错误: 没有成功的评估结果")
        sys.exit(1)

    # 生成报告
    report_md = generate_report(benchmark)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    # 保存 JSON 详情
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(report_md)
    print(f"\n报告已保存到: {output_path}")
    print(f"详细数据已保存到: {json_path}")


if __name__ == "__main__":
    main()
