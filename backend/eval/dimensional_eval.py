"""分维度RAG评估脚本

按查询类型、难度级别等维度分析RAG效果
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

# 添加项目路径
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


def run_dimensional_eval(dataset_path: str, top_k: int = 5):
    """运行分维度评估"""

    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print("正在初始化 RAG 引擎...")
    engine = RAGEngine(config)
    llm_client = LLMClient(config.MIMO_API_KEY, config.MIMO_API_BASE, config.MIMO_MODEL)
    evaluator = RAGEvaluator(engine, llm_client)

    # 按维度存储结果
    results_by_type = defaultdict(list)
    results_by_difficulty = defaultdict(list)

    print(f"正在评估 {len(dataset)} 个问题...")
    print()

    for i, sample in enumerate(dataset, 1):
        question = sample["question"]
        qtype = sample.get("query_type", "unknown")
        difficulty = sample.get("difficulty", "unknown")

        print(f"[{i}/{len(dataset)}] 评估: {question[:50]}...")

        # 检索评估
        expected_sources = sample.get("expected_sources", [])
        retrieval_result = evaluator.evaluate_retrieval(question, expected_sources, top_k)

        # 关键词覆盖
        expected_keywords = sample.get("expected_keywords", [])
        rag_result = engine.retrieve(question, top_k=top_k)
        answer = llm_client.generate(engine.build_prompt(question, [
            {"text": doc, "metadata": meta}
            for doc, meta in zip(rag_result["documents"], rag_result["metadatas"])
        ]))

        keyword_hits = sum(1 for kw in expected_keywords if kw in answer)
        keyword_coverage = keyword_hits / len(expected_keywords) if expected_keywords else None

        # 存储结果
        result = {
            "question": question,
            "retrieval": retrieval_result,
            "keyword_coverage": keyword_coverage
        }

        results_by_type[qtype].append(result)
        results_by_difficulty[difficulty].append(result)

    # 计算分维度指标
    print("\n" + "=" * 60)
    print("分维度评估结果")
    print("=" * 60)

    # 按查询类型
    print("\n【按查询类型】")
    print("-" * 60)
    print(f"{'类型':<15} {'样本数':<8} {'Recall@K':<12} {'MRR':<10} {'Precision':<12} {'关键词覆盖':<10}")
    print("-" * 60)

    for qtype in ["factoid", "analytical", "procedural", "exploratory"]:
        if qtype in results_by_type:
            results = results_by_type[qtype]
            recalls = [r["retrieval"]["recall"] for r in results if r["retrieval"]["recall"] is not None]
            mrrs = [r["retrieval"]["mrr"] for r in results if r["retrieval"]["mrr"] is not None]
            precisions = [r["retrieval"]["precision"] for r in results if r["retrieval"]["precision"] is not None]
            kw_coverages = [r["keyword_coverage"] for r in results if r["keyword_coverage"] is not None]

            avg_recall = sum(recalls) / len(recalls) if recalls else 0
            avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0
            avg_precision = sum(precisions) / len(precisions) if precisions else 0
            avg_kw = sum(kw_coverages) / len(kw_coverages) if kw_coverages else 0

            print(f"{qtype:<15} {len(results):<8} {avg_recall:<12.2f} {avg_mrr:<10.2f} {avg_precision:<12.2f} {avg_kw:<10.2f}")

    # 按难度级别
    print("\n【按难度级别】")
    print("-" * 60)
    print(f"{'难度':<15} {'样本数':<8} {'Recall@K':<12} {'MRR':<10} {'Precision':<12} {'关键词覆盖':<10}")
    print("-" * 60)

    for difficulty in ["easy", "medium", "hard"]:
        if difficulty in results_by_difficulty:
            results = results_by_difficulty[difficulty]
            recalls = [r["retrieval"]["recall"] for r in results if r["retrieval"]["recall"] is not None]
            mrrs = [r["retrieval"]["mrr"] for r in results if r["retrieval"]["mrr"] is not None]
            precisions = [r["retrieval"]["precision"] for r in results if r["retrieval"]["precision"] is not None]
            kw_coverages = [r["keyword_coverage"] for r in results if r["keyword_coverage"] is not None]

            avg_recall = sum(recalls) / len(recalls) if recalls else 0
            avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0
            avg_precision = sum(precisions) / len(precisions) if precisions else 0
            avg_kw = sum(kw_coverages) / len(kw_coverages) if kw_coverages else 0

            print(f"{difficulty:<15} {len(results):<8} {avg_recall:<12.2f} {avg_mrr:<10.2f} {avg_precision:<12.2f} {avg_kw:<10.2f}")

    print("\n" + "=" * 60)

    # 返回完整结果
    return {
        "by_type": dict(results_by_type),
        "by_difficulty": dict(results_by_difficulty)
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="分维度RAG评估")
    parser.add_argument(
        "--dataset",
        default="eval/eval_dataset_extended.json",
        help="评估数据集路径"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="检索返回的文档数量"
    )

    args = parser.parse_args()

    dataset_path = project_root / args.dataset
    if not dataset_path.exists():
        print(f"错误: 数据集不存在: {dataset_path}")
        sys.exit(1)

    results = run_dimensional_eval(str(dataset_path), args.top_k)

    # 保存详细结果
    output_path = project_root / "eval" / "dimensional_report.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n详细结果已保存到: {output_path}")


if __name__ == "__main__":
    main()
