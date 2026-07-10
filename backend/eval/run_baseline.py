"""快速生成 Baseline 评估

通过临时禁用优化特性来生成 baseline 数据

用法：
    cd backend
    python eval/run_baseline.py --output eval/baseline_report.json
"""

import json
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

import os
os.chdir(project_root)

from core.config import config


def create_baseline_config():
    """创建 baseline 配置（禁用高级优化特性）"""

    # 保存原始配置
    original_config = {
        "USE_HYDE": config.USE_HYDE,
        "MULTI_QUERY_ENABLED": config.MULTI_QUERY_ENABLED,
        "RERANK_STRATEGY": config.RERANK_STRATEGY,
        "CITATION_VERIFY_ENABLED": config.CITATION_VERIFY_ENABLED,
        "RETRIEVAL_REFETCH_ENABLED": config.RETRIEVAL_REFETCH_ENABLED,
        "SELF_RAG_ENABLED": config.SELF_RAG_ENABLED,
        "USE_CACHE": config.USE_CACHE,
        "SEMANTIC_CACHE_ENABLED": config.SEMANTIC_CACHE_ENABLED,
    }

    # Baseline 配置（禁用高级特性）
    baseline_config = {
        "USE_HYDE": False,           # 禁用 HyDE 查询改写
        "MULTI_QUERY_ENABLED": False, # 禁用多查询扩展
        "RERANK_STRATEGY": "none",    # 禁用 Rerank
        "CITATION_VERIFY_ENABLED": False,  # 禁用引用核查
        "RETRIEVAL_REFETCH_ENABLED": False, # 禁用二次检索
        "SELF_RAG_ENABLED": False,    # 禁用 Self-RAG
        "USE_CACHE": False,           # 禁用缓存
        "SEMANTIC_CACHE_ENABLED": False,
    }

    return original_config, baseline_config


def main():
    import argparse

    parser = argparse.ArgumentParser(description="生成 Baseline 评估")
    parser.add_argument("--output", default="eval/baseline_report.json", help="输出路径")
    parser.add_argument("--dataset", default="extended", help="数据集")
    parser.add_argument("--framework", default="custom", help="评估框架")

    args = parser.parse_args()

    print("=" * 60)
    print("    Baseline 评估生成器")
    print("=" * 60)

    # 创建 baseline 配置
    original, baseline = create_baseline_config()

    print("\n📋 Baseline 配置（禁用高级优化）:")
    print(f"  - HyDE 查询改写: ❌")
    print(f"  - 多查询扩展: ❌")
    print(f"  - Rerank 精排: ❌")
    print(f"  - 引用核查: ❌")
    print(f"  - 二次检索: ❌")
    print(f"  - Self-RAG: ❌")
    print(f"  - 缓存: ❌")

    print("\n⚠️  注意: 此脚本需要手动修改配置运行")
    print("   请参考以下步骤:\n")

    print("方法 1: 使用环境变量（推荐）")
    print("-" * 40)
    print("USE_HYDE=false \\")
    print("MULTI_QUERY_ENABLED=false \\")
    print("RERANK_STRATEGY=none \\")
    print("CITATION_VERIFY_ENABLED=false \\")
    print("RETRIEVAL_REFETCH_ENABLED=false \\")
    print("SELF_RAG_ENABLED=false \\")
    print("USE_CACHE=false \\")
    print("SEMANTIC_CACHE_ENABLED=false \\")
    print(f"python eval/run_eval.py --dataset {args.dataset} --framework {args.framework} --output {args.output}")

    print("\n\n方法 2: 创建 .env.baseline 文件")
    print("-" * 40)

    # 生成 baseline env 文件
    env_content = """# Baseline 配置（禁用高级优化特性）
USE_HYDE=false
MULTI_QUERY_ENABLED=false
RERANK_STRATEGY=none
CITATION_VERIFY_ENABLED=false
RETRIEVAL_REFETCH_ENABLED=false
SELF_RAG_ENABLED=false
USE_CACHE=false
SEMANTIC_CACHE_ENABLED=false
"""

    env_path = backend_dir / ".env.baseline"
    with open(env_path, "w") as f:
        f.write(env_content)

    print(f"✅ 已生成: {env_path}")
    print(f"\n运行命令:")
    print(f"  cp .env.baseline .env")
    print(f"  python eval/run_eval.py --dataset {args.dataset} --framework {args.framework} --output {args.output}")
    print(f"  cp .env.backup .env  # 恢复原配置")

    print("\n\n方法 3: 使用简化 RAG 引擎")
    print("-" * 40)
    print("创建一个 SimplifiedRAGEngine，只保留基础检索功能")

    print("\n" + "=" * 60)
    print("运行完成后，使用以下命令生成对比报告:")
    print("=" * 60)
    print(f"python eval/ab_comparison.py \\")
    print(f"  --baseline {args.output} \\")
    print(f"  --optimized eval/optimized_report.json \\")
    print(f"  --output eval/ab_comparison.md")


if __name__ == "__main__":
    main()
