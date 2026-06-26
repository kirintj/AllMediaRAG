"""工程性能采集器 — 线程安全的运行时指标聚合

采集检索管线各阶段延迟、LLM 生成延迟、缓存命中率和请求统计，
供 /api/metrics 和 /health 端点消费。

使用方式：
    from core.observability.metrics_collector import metrics_collector
    metrics_collector.record_retrieval({"classify_ms": 50, "search_ms": 120, ...})
"""

import logging
import threading
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)


def _percentile(sorted_data: list[float], p: float) -> Optional[float]:
    """计算分位数（输入必须已排序）"""
    if not sorted_data:
        return None
    k = (len(sorted_data) - 1) * p
    f = int(k)
    c = f + 1
    if c >= len(sorted_data):
        return sorted_data[f]
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def _safe_stats(values: deque) -> dict:
    """从 deque 计算 p50/p95/avg"""
    if not values:
        return {"avg": None, "p50": None, "p95": None}
    data = sorted(values)
    return {
        "avg": round(sum(data) / len(data), 1),
        "p50": round(_percentile(data, 0.5), 1),
        "p95": round(_percentile(data, 0.95), 1),
    }


class MetricsCollector:
    """线程安全的运行时指标采集器"""

    def __init__(self, maxlen: int = 1000):
        self._lock = threading.Lock()
        # 各阶段延迟
        self._classify_latencies: deque[float] = deque(maxlen=maxlen)
        self._search_latencies: deque[float] = deque(maxlen=maxlen)
        self._rerank_latencies: deque[float] = deque(maxlen=maxlen)
        self._total_latencies: deque[float] = deque(maxlen=maxlen)
        self._generation_latencies: deque[float] = deque(maxlen=maxlen)
        # 请求计数
        self._total_requests: int = 0
        self._success_requests: int = 0
        # 缓存统计
        self._cache_hits: int = 0
        self._cache_misses: int = 0

    # ── 记录方法 ─────────────────────────────────────────────────────────

    def record_retrieval(self, stages: dict) -> None:
        """记录一次检索的各阶段延迟 (ms)

        Args:
            stages: {"classify_ms": 50, "search_ms": 120, "rerank_ms": 80, "total_ms": 250}
        """
        with self._lock:
            if "classify_ms" in stages:
                self._classify_latencies.append(stages["classify_ms"])
            if "search_ms" in stages:
                self._search_latencies.append(stages["search_ms"])
            if "rerank_ms" in stages:
                self._rerank_latencies.append(stages["rerank_ms"])
            if "total_ms" in stages:
                self._total_latencies.append(stages["total_ms"])

    def record_generation(self, duration_ms: float) -> None:
        """记录一次 LLM 生成延迟"""
        with self._lock:
            self._generation_latencies.append(duration_ms)

    def record_request(self, success: bool, duration_ms: float = 0) -> None:
        """记录一次请求（成功/失败）

        为什么同时检查告警：每次请求后立即评估错误率，
        比定时任务更及时发现问题。最低样本量 20 避免早期请求误报。
        """
        with self._lock:
            self._total_requests += 1
            if success:
                self._success_requests += 1
            # 错误率告警（每 10 个请求检查一次，避免频繁计算）
            if self._total_requests >= 20 and self._total_requests % 10 == 0:
                self._check_error_rate_alert()

    def record_cache_hit(self, hit: bool) -> None:
        """记录缓存命中/未命中"""
        with self._lock:
            if hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1

    # ── 查询方法 ─────────────────────────────────────────────────────────

    def _check_error_rate_alert(self) -> None:
        """评估错误率是否超过阈值，超过则记录告警日志

        为什么用日志而非告警系统：项目当前无 AlertManager/PagerDuty 集成，
        日志是最基础但最可靠的告警通道——会被 ELK/Loki 采集并触发告警规则。
        阈值 5% 是经验值：低于此值通常是偶发错误，高于此值说明系统性问题。
        """
        if self._total_requests == 0:
            return
        error_rate = 1.0 - (self._success_requests / self._total_requests)
        threshold = 0.05  # 5%
        if error_rate >= threshold:
            logger.warning(
                "Error rate alert: %.1f%% (threshold: %.1f%%, total: %d, failed: %d)",
                error_rate * 100, threshold * 100,
                self._total_requests,
                self._total_requests - self._success_requests,
            )

    def get_stats(self) -> dict:
        """返回完整的性能统计（供 /api/metrics）"""
        with self._lock:
            total = self._cache_hits + self._cache_misses
            return {
                "requests": {
                    "total": self._total_requests,
                    "success": self._success_requests,
                    "success_rate": round(self._success_requests / self._total_requests, 3)
                    if self._total_requests > 0 else None,
                },
                "latency": {
                    "classify": _safe_stats(self._classify_latencies),
                    "search": _safe_stats(self._search_latencies),
                    "rerank": _safe_stats(self._rerank_latencies),
                    "total": _safe_stats(self._total_latencies),
                    "generation": _safe_stats(self._generation_latencies),
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate": round(self._cache_hits / total, 3) if total > 0 else None,
                },
            }

    def get_health(self) -> dict:
        """精简健康检查数据（供 /health）"""
        with self._lock:
            total = self._cache_hits + self._cache_misses
            total_sorted = sorted(self._total_latencies)
            return {
                "status": "ok",
                "request_count": self._total_requests,
                "latency_p95_ms": round(_percentile(total_sorted, 0.95), 1)
                if total_sorted else None,
                "cache_hit_rate": round(self._cache_hits / total, 3)
                if total > 0 else None,
            }


# 模块级单例
metrics_collector = MetricsCollector()
