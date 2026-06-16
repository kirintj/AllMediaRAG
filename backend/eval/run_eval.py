"""RAG 评估入口脚本（支持指定数据集 + 多框架）

运行方式：
    cd backend && python eval/run_eval.py --dataset extended
    cd backend && python eval/run_eval.py --dataset original
    cd backend && python eval/run_eval.py --dataset custom --path path/to/dataset.json
    cd backend && python eval/run_eval.py --dataset extended --framework ragas
"""

import sys
import json
import os
import argparse
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

os.chdir(project_root)

from core.config import config
from core.rag_engine import RAGEngine
from core.llm_client import LLMClient
from eval.evaluator import RAGEvaluator


def print_report(report: dict, verbose: bool = False):
    """终端打印评估报告（支持自研和 RAGAS 两种格式）"""
    framework = report.get("framework", "custom")

    print("\n" + "=" * 50)
    if framework == "ragas":
        print("    RAG 评估报告 (RAGAS)")
    else:
        print("    RAG 评估报告")
    print("=" * 50)
    print(f"样本数: {report['total_samples']}")
    print()

    # 错误信息
    if "error" in report:
        print(f"[错误] {report['error']}")
        print("=" * 50)
        return

    # 检索指标
    retrieval = report["retrieval"]
    print("检索指标:")
    if framework == "ragas":
        if retrieval.get("context_precision") is not None:
            print(f"  Context Precision: {retrieval['context_precision']:.4f}")
        if retrieval.get("context_recall") is not None:
            print(f"  Context Recall:    {retrieval['context_recall']:.4f}")
    else:
        if retrieval.get("recall_at_k") is not None:
            print(f"  Recall@K:   {retrieval['recall_at_k']:.2f}")
            print(f"  MRR:        {retrieval['mrr']:.2f}")
            print(f"  Precision:  {retrieval['precision']:.2f}")
        else:
            print("  (数据集无 expected_sources，跳过)")
    print()

    # 生成指标
    generation = report["generation"]
    print("生成指标:")
    if framework == "ragas":
        if generation.get("faithfulness") is not None:
            print(f"  Faithfulness:      {generation['faithfulness']:.4f}")
        if generation.get("answer_relevancy") is not None:
            print(f"  Answer Relevancy:  {generation['answer_relevancy']:.4f}")
    else:
        if generation.get("faithfulness") is not None:
            print(f"  Faithfulness:    {generation['faithfulness']:.1f}/5")
            print(f"  Answer Relevancy: {generation['relevancy']:.1f}/5")
        else:
            print("  (评估失败)")
    print()

    # 关键词覆盖率（仅自研框架）
    if report.get("keyword_coverage") is not None:
        print(f"关键词覆盖率: {report['keyword_coverage']:.2f}")
        print()

    # 分类统计
    if verbose and "details" in report:
        print("\n分类统计:")
        if framework == "ragas":
            for i, detail in enumerate(report["details"]):
                metrics_str = ", ".join(
                    f"{k}={v:.4f}" for k, v in detail.items()
                    if v is not None
                )
                print(f"  样本 {i+1}: {metrics_str}")
        else:
            by_type = {}
            by_difficulty = {}

            for detail in report["details"]:
                # 假设数据集中有 query_type 和 difficulty 字段
                q = detail["question"]
                # 这里简化处理，实际可以从数据集读取
                pass

    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="RAG 系统评估工具")
    parser.add_argument(
        "--dataset",
        choices=["original", "extended", "custom"],
        default="original",
        help="选择评估数据集 (default: original)"
    )
    parser.add_argument(
        "--path",
        type=str,
        help="自定义数据集路径（当 --dataset=custom 时必填）"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="检索返回的文档数量 (default: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="输出报告路径 (default: eval/report.json)"
    )
    parser.add_argument(
        "--framework",
        choices=["custom", "ragas"],
        default="custom",
        help="评估框架: custom (自研) 或 ragas (RAGAS 标准) (default: custom)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="显示详细信息"
    )

    args = parser.parse_args()

    # 确定数据集路径
    eval_dir = Path(__file__).parent
    if args.dataset == "original":
        dataset_path = eval_dir / "eval_dataset.json"
    elif args.dataset == "extended":
        dataset_path = eval_dir / "eval_dataset_extended.json"
    elif args.dataset == "custom":
        if not args.path:
            print("错误: 使用 custom 数据集时必须指定 --path 参数")
            sys.exit(1)
        dataset_path = Path(args.path)
    else:
        dataset_path = eval_dir / "eval_dataset.json"

    # 确定输出路径
    if args.output:
        report_path = Path(args.output)
    else:
        report_path = eval_dir / f"report_{args.dataset}.json"

    if not dataset_path.exists():
        print(f"错误: 评估数据集不存在: {dataset_path}")
        sys.exit(1)

    print(f"数据集: {dataset_path}")
    print(f"Top-K: {args.top_k}")
    print(f"框架: {args.framework}")
    print()

    # 加载数据集（两种框架都需要）
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    if args.framework == "ragas":
        # ── RAGAS 标准评估 ──────────────────────────────────────
        from eval.ragas_evaluator import RAGASEvaluator

        # RAGAS 需要 contexts 字段；如果数据集没有，用引擎预填充
        needs_prefill = any("contexts" not in s for s in dataset)
        if needs_prefill:
            print("正在初始化 RAG 引擎（为 RAGAS 预填充 contexts）...")
            engine = RAGEngine(config)
            llm_client = LLMClient(
                config.MIMO_API_KEY,
                config.MIMO_API_BASE,
                config.MIMO_MODEL,
            )
            for sample in dataset:
                if "contexts" not in sample:
                    rag_result = engine.full_retrieve(sample["question"])
                    sample["contexts"] = rag_result["documents"]
                    metadatas = rag_result.get("metadatas", [])
                else:
                    metadatas = []
                if "answer" not in sample or not sample["answer"]:
                    prompt = engine.build_prompt(sample["question"], [
                        {"text": ctx, "metadata": meta}
                        for ctx, meta in zip(
                            sample.get("contexts", []),
                            metadatas if metadatas else [{}] * len(sample.get("contexts", []))
                        )
                    ])
                    sample["answer"] = llm_client.generate(prompt)
                # RAGAS 使用 ground_truth 字段
                if "ground_truth" not in sample:
                    sample["ground_truth"] = sample.get("reference_answer", "")

        print("正在运行 RAGAS 评估...")
        ragas_evaluator = RAGASEvaluator()
        report = ragas_evaluator.evaluate(dataset)

    else:
        # ── 自研评估器（原有流程，保持不变）──────────────────────
        print("正在初始化 RAG 引擎...")
        engine = RAGEngine(config)

        llm_client = LLMClient(
            config.MIMO_API_KEY,
            config.MIMO_API_BASE,
            config.MIMO_MODEL,
        )

        evaluator = RAGEvaluator(engine, llm_client)

        print("正在运行评估...")
        report = evaluator.run(str(dataset_path), top_k=args.top_k)

    # 保存详细报告
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_report(report, verbose=args.verbose)
    print(f"\n详细结果已保存到: {report_path}")


if __name__ == "__main__":
    main()
