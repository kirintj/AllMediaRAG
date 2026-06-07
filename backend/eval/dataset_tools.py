"""评估数据集生成工具

用于批量生成评估数据集的模板和辅助工具
"""

import json
from pathlib import Path
from typing import List, Dict


def create_eval_sample(
    id: int,
    question: str,
    query_type: str,
    difficulty: str,
    expected_sources: List[str],
    expected_keywords: List[str],
    reference_answer: str
) -> Dict:
    """创建单个评估样本"""
    return {
        "id": id,
        "question": question,
        "query_type": query_type,  # factoid, analytical, procedural, exploratory
        "difficulty": difficulty,  # easy, medium, hard
        "expected_sources": expected_sources,
        "expected_keywords": expected_keywords,
        "reference_answer": reference_answer
    }


def generate_batch_template(output_path: str, count: int = 10):
    """生成批量评估样本模板"""
    samples = []
    for i in range(1, count + 1):
        samples.append({
            "id": i,
            "question": f"问题{i}：在此填写问题",
            "query_type": "factoid",
            "difficulty": "medium",
            "expected_sources": ["source_doc.md"],
            "expected_keywords": ["关键词1", "关键词2"],
            "reference_answer": "在此填写参考答案"
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    print(f"已生成 {count} 个评估样本模板到: {output_path}")


def analyze_dataset(dataset_path: str):
    """分析评估数据集的统计信息"""
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"\n数据集分析: {dataset_path}")
    print("=" * 50)
    print(f"总样本数: {len(dataset)}")

    # 按查询类型统计
    by_type = {}
    for sample in dataset:
        qtype = sample.get("query_type", "unknown")
        by_type[qtype] = by_type.get(qtype, 0) + 1

    print("\n按查询类型:")
    for qtype, count in sorted(by_type.items()):
        print(f"  {qtype}: {count} ({count/len(dataset)*100:.1f}%)")

    # 按难度统计
    by_difficulty = {}
    for sample in dataset:
        diff = sample.get("difficulty", "unknown")
        by_difficulty[diff] = by_difficulty.get(diff, 0) + 1

    print("\n按难度级别:")
    for diff, count in sorted(by_difficulty.items()):
        print(f"  {diff}: {count} ({count/len(dataset)*100:.1f}%)")

    # 关键词覆盖统计
    all_keywords = []
    for sample in dataset:
        all_keywords.extend(sample.get("expected_keywords", []))

    unique_keywords = set(all_keywords)
    print(f"\n唯一关键词数: {len(unique_keywords)}")
    print(f"平均每个问题关键词数: {len(all_keywords)/len(dataset):.1f}")

    print("=" * 50)


def merge_datasets(dataset_paths: List[str], output_path: str):
    """合并多个数据集"""
    merged = []
    current_id = 1

    for path in dataset_paths:
        with open(path, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        for sample in dataset:
            sample["id"] = current_id
            merged.append(sample)
            current_id += 1

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"已合并 {len(dataset_paths)} 个数据集，共 {len(merged)} 个样本到: {output_path}")


def validate_dataset(dataset_path: str) -> List[str]:
    """验证数据集格式"""
    errors = []

    with open(dataset_path, "r", encoding="utf-8") as f:
        try:
            dataset = json.load(f)
        except json.JSONDecodeError as e:
            return [f"JSON解析错误: {e}"]

    if not isinstance(dataset, list):
        errors.append("数据集必须是数组格式")
        return errors

    required_fields = ["question", "expected_sources", "expected_keywords", "reference_answer"]

    for i, sample in enumerate(dataset):
        if not isinstance(sample, dict):
            errors.append(f"样本 {i+1}: 必须是对象格式")
            continue

        for field in required_fields:
            if field not in sample:
                errors.append(f"样本 {i+1}: 缺少必填字段 '{field}'")

        if "query_type" in sample:
            valid_types = ["factoid", "analytical", "procedural", "exploratory"]
            if sample["query_type"] not in valid_types:
                errors.append(f"样本 {i+1}: 无效的 query_type '{sample['query_type']}'")

        if "difficulty" in sample:
            valid_difficulties = ["easy", "medium", "hard"]
            if sample["difficulty"] not in valid_difficulties:
                errors.append(f"样本 {i+1}: 无效的 difficulty '{sample['difficulty']}'")

    return errors


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="评估数据集工具")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 生成模板
    gen_parser = subparsers.add_parser("generate", help="生成评估模板")
    gen_parser.add_argument("--output", required=True, help="输出文件路径")
    gen_parser.add_argument("--count", type=int, default=10, help="生成数量")

    # 分析数据集
    analyze_parser = subparsers.add_parser("analyze", help="分析数据集")
    analyze_parser.add_argument("dataset", help="数据集路径")

    # 合并数据集
    merge_parser = subparsers.add_parser("merge", help="合并数据集")
    merge_parser.add_argument("datasets", nargs="+", help="数据集路径列表")
    merge_parser.add_argument("--output", required=True, help="输出文件路径")

    # 验证数据集
    validate_parser = subparsers.add_parser("validate", help="验证数据集")
    validate_parser.add_argument("dataset", help="数据集路径")

    args = parser.parse_args()

    if args.command == "generate":
        generate_batch_template(args.output, args.count)
    elif args.command == "analyze":
        analyze_dataset(args.dataset)
    elif args.command == "merge":
        merge_datasets(args.datasets, args.output)
    elif args.command == "validate":
        errors = validate_dataset(args.dataset)
        if errors:
            print("验证失败:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("验证通过！")
    else:
        parser.print_help()
