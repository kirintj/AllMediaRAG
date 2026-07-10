"""性能基准测试脚本

测试指标：
- 平均响应时间
- 缓存命中率
- 索引构建时间
- 增量更新时间

用法：
    cd backend
    python eval/performance_benchmark.py --output eval/performance_report.json
"""

import json
import time
import argparse
import statistics
from pathlib import Path
from typing import Callable, Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import config
from core.rag_engine import RAGEngine
from core.llm_client import LLMClient


class PerformanceBenchmark:
    """性能基准测试"""

    def __init__(self):
        print("正在初始化 RAG 引擎...")
        self.engine = RAGEngine(config)
        self.llm_client = LLMClient(
            config.MIMO_API_KEY,
            config.MIMO_API_BASE,
            config.MIMO_MODEL,
        )
        self.results = {}

    def time_it(self, func: Callable, *args, **kwargs) -> tuple[float, Any]:
        """计时装饰器"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return elapsed, result

    def benchmark_retrieval_latency(self, questions: list[str], runs: int = 3) -> dict:
        """测试检索延迟"""
        print(f"\n📊 测试检索延迟 ({len(questions)} 问题 × {runs} 次)...")

        latencies = []
        for question in questions:
            for _ in range(runs):
                elapsed, _ = self.time_it(self.engine.full_retrieve, question)
                latencies.append(elapsed)

        return {
            "mean_ms": statistics.mean(latencies) * 1000,
            "median_ms": statistics.median(latencies) * 1000,
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] * 1000,
            "p99_ms": sorted(latencies)[int(len(latencies) * 0.99)] * 1000,
            "min_ms": min(latencies) * 1000,
            "max_ms": max(latencies) * 1000,
            "total_queries": len(latencies),
        }

    def benchmark_e2e_latency(self, questions: list[str], runs: int = 2) -> dict:
        """测试端到端延迟（检索 + 生成）"""
        print(f"\n📊 测试端到端延迟 ({len(questions)} 问题 × {runs} 次)...")

        latencies = []
        for question in questions:
            for _ in range(runs):
                def e2e_query():
                    result = self.engine.full_retrieve(question)
                    prompt = self.engine.build_prompt(question, [
                        {"text": doc, "metadata": meta}
                        for doc, meta in zip(result["documents"], result["metadatas"])
                    ])
                    return self.llm_client.generate(prompt)

                elapsed, _ = self.time_it(e2e_query)
                latencies.append(elapsed)

        return {
            "mean_ms": statistics.mean(latencies) * 1000,
            "median_ms": statistics.median(latencies) * 1000,
            "p95_ms": sorted(latencies)[int(len(latencies) * 0.95)] * 1000,
            "min_ms": min(latencies) * 1000,
            "max_ms": max(latencies) * 1000,
            "total_queries": len(latencies),
        }

    def benchmark_cache_hit_rate(self, questions: list[str]) -> dict:
        """测试缓存命中率

        通过连续查询相同问题，测试第二次是否命中缓存
        """
        print(f"\n📊 测试缓存命中率 ({len(questions)} 问题)...")

        # 第一轮：冷启动
        cold_latencies = []
        for q in questions:
            elapsed, _ = self.time_it(self.engine.full_retrieve, q)
            cold_latencies.append(elapsed)

        # 第二轮：应该命中缓存
        hot_latencies = []
        for q in questions:
            elapsed, _ = self.time_it(self.engine.full_retrieve, q)
            hot_latencies.append(elapsed)

        # 计算命中率（热查询延迟 < 冷查询 50% 视为命中）
        hits = sum(1 for cold, hot in zip(cold_latencies, hot_latencies) if hot < cold * 0.5)
        hit_rate = hits / len(questions) if questions else 0

        speedup = statistics.mean(cold_latencies) / statistics.mean(hot_latencies) if statistics.mean(hot_latencies) > 0 else 0

        return {
            "hit_rate": hit_rate,
            "hits": hits,
            "total": len(questions),
            "cold_mean_ms": statistics.mean(cold_latencies) * 1000,
            "hot_mean_ms": statistics.mean(hot_latencies) * 1000,
            "speedup": speedup,
        }

    def benchmark_concurrent_queries(self, questions: list[str], concurrency: int = 5) -> dict:
        """测试并发查询性能"""
        print(f"\n📊 测试并发性能 (并发数={concurrency})...")

        import concurrent.futures

        latencies = []

        def query(q):
            elapsed, _ = self.time_it(self.engine.full_retrieve, q)
            return elapsed

        # 模拟并发
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            # 复制问题列表以模拟并发压力
            all_questions = questions * (concurrency // len(questions) + 1)
            all_questions = all_questions[:concurrency * 2]

            start = time.perf_counter()
            futures = [executor.submit(query, q) for q in all_questions]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            total_time = time.perf_counter() - start

        return {
            "concurrency": concurrency,
            "total_queries": len(all_questions),
            "total_time_s": total_time,
            "throughput_qps": len(all_questions) / total_time,
            "mean_latency_ms": statistics.mean(results) * 1000,
            "p95_latency_ms": sorted(results)[int(len(results) * 0.95)] * 1000,
        }

    def run(self, dataset_path: str = None) -> dict:
        """运行完整性能测试"""

        # 加载测试问题
        if dataset_path:
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
            questions = [s["question"] for s in dataset]
        else:
            # 默认测试问题
            questions = [
                "什么是 Agent？",
                "RAG 系统的评估指标有哪些？",
                "LangGraph 解决了什么问题？",
                "如何设计 Agent 的记忆系统？",
                "Claude Code 的架构是怎样的？",
            ]

        # 运行各项测试
        report = {
            "test_questions": len(questions),
            "retrieval_latency": self.benchmark_retrieval_latency(questions, runs=3),
            "e2e_latency": self.benchmark_e2e_latency(questions[:3], runs=2),  # 只测3个问题，避免太慢
            "cache_performance": self.benchmark_cache_hit_rate(questions),
            "concurrent_performance": self.benchmark_concurrent_queries(questions, concurrency=5),
        }

        return report

    def print_report(self, report: dict):
        """打印报告"""
        print("\n" + "=" * 60)
        print("    RAG 系统性能基准报告")
        print("=" * 60)
        print(f"测试问题数: {report['test_questions']}")

        # 检索延迟
        ret = report["retrieval_latency"]
        print("\n📊 检索延迟:")
        print(f"  平均: {ret['mean_ms']:.1f}ms")
        print(f"  中位数: {ret['median_ms']:.1f}ms")
        print(f"  P95: {ret['p95_ms']:.1f}ms")
        print(f"  P99: {ret['p99_ms']:.1f}ms")

        # 端到端延迟
        e2e = report["e2e_latency"]
        print("\n📊 端到端延迟 (检索+生成):")
        print(f"  平均: {e2e['mean_ms']:.1f}ms ({e2e['mean_ms']/1000:.2f}s)")
        print(f"  中位数: {e2e['median_ms']:.1f}ms")
        print(f"  P95: {e2e['p95_ms']:.1f}ms")

        # 缓存性能
        cache = report["cache_performance"]
        print("\n📊 缓存性能:")
        print(f"  命中率: {cache['hit_rate']*100:.1f}%")
        print(f"  冷查询平均: {cache['cold_mean_ms']:.1f}ms")
        print(f"  热查询平均: {cache['hot_mean_ms']:.1f}ms")
        print(f"  加速比: {cache['speedup']:.2f}x")

        # 并发性能
        concurrent = report["concurrent_performance"]
        print("\n📊 并发性能:")
        print(f"  并发数: {concurrent['concurrency']}")
        print(f"  吞吐量: {concurrent['throughput_qps']:.2f} QPS")
        print(f"  平均延迟: {concurrent['mean_latency_ms']:.1f}ms")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="RAG 性能基准测试")
    parser.add_argument("--dataset", type=str, help="测试数据集路径")
    parser.add_argument("--output", default="eval/performance_report.json", help="输出路径")

    args = parser.parse_args()

    benchmark = PerformanceBenchmark()
    report = benchmark.run(args.dataset)
    benchmark.print_report(report)

    # 保存报告
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 性能报告已保存: {output_path}")


if __name__ == "__main__":
    main()
