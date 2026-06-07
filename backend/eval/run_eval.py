"""RAG 评估入口脚本（支持指定数据集）

运行方式：
    cd backend && python eval/run_eval.py --dataset extended
    cd backend && python eval/run_eval.py --dataset original
    cd backend && python eval/run_eval.py --dataset custom --path path/to/dataset.json
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
    """终端打印评估报告"""
    print("\n" + "=" * 50)
    print("    RAG 评估报告")
    print("=" * 50)
    print(f"样本数: {report['total_samples']}")
    print()

    # 检索指标
    retrieval = report["retrieval"]
    print("检索指标:")
    if retrieval["recall_at_k"] is not None:
        print(f"  Recall@K:   {retrieval['recall_at_k']:.2f}")
        print(f"  MRR:        {retrieval['mrr']:.2f}")
        print(f"  Precision:  {retrieval['precision']:.2f}")
    else:
        print("  (数据集无 expected_sources，跳过)")
    print()

    # 生成指标
    generation = report["generation"]
    print("生成指标 (LLM-as-Judge):")
    if generation["faithfulness"] is not None:
        print(f"  Faithfulness:    {generation['faithfulness']:.1f}/5")
        print(f"  Answer Relevancy: {generation['relevancy']:.1f}/5")
    else:
        print("  (评估失败)")
    print()

    # 关键词覆盖率
    if report["keyword_coverage"] is not None:
        print(f"关键词覆盖率: {report['keyword_coverage']:.2f}")
        print()

    # 分类统计
    if verbose and "details" in report:
        print("\n分类统计:")
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
    print()

    print("正在初始化 RAG 引擎...")
    engine = RAGEngine(config)

    llm_client = LLMClient(
        config.MIMO_API_KEY,
        config.MIMO_API_BASE,
        config.MIMO_MODEL,
    )

    evaluator = RAGEvaluator(engine, llm_client)

    print(f"正在运行评估...")
    report = evaluator.run(str(dataset_path), top_k=args.top_k)

    # 保存详细报告
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print_report(report, verbose=args.verbose)
    print(f"\n详细结果已保存到: {report_path}")


if __name__ == "__main__":
    main()
