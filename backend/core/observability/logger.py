import json
import logging
from datetime import datetime
from typing import Optional, Any


class StructuredLogger:
    """结构化日志器"""

    def __init__(self, logger_name: str, log_level: str = "INFO"):
        """
        Args:
            logger_name: 日志器名称
            log_level: 日志级别
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # 避免重复添加handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_retrieval_event(self, event_data: dict) -> None:
        """
        记录检索事件

        Args:
            event_data: 事件数据
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "retrieval",
            "query_id": event_data.get("query_id"),
            "query": event_data.get("query"),
            "total_duration_ms": event_data.get("total_duration_ms"),
            "results_count": event_data.get("results_count"),
            "stages": event_data.get("stages", {})
        }

        self.logger.info(json.dumps(log_entry, ensure_ascii=False))

    def log_error_event(self, error: Exception, context: dict) -> None:
        """
        记录错误事件

        Args:
            error: 异常对象
            context: 上下文信息
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }

        self.logger.error(json.dumps(log_entry, ensure_ascii=False))

    def log_performance_warning(self, metric_name: str,
                                current_value: float,
                                threshold: float) -> None:
        """
        记录性能警告

        Args:
            metric_name: 指标名称
            current_value: 当前值
            threshold: 阈值
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "performance_warning",
            "metric": metric_name,
            "current_value": current_value,
            "threshold": threshold
        }

        self.logger.warning(json.dumps(log_entry, ensure_ascii=False))
