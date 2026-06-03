import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """JSON格式化器，输出单行JSON日志"""

    # extra字段白名单，避免意外合并record的内部属性
    _EXTRA_KEYS = frozenset([
        "event_type", "query_id", "query", "total_duration_ms",
        "results_count", "stages", "error_type", "error_message",
        "context", "metric", "current_value", "threshold",
    ])

    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        # 合并通过extra参数传入的结构化字段
        for key in self._EXTRA_KEYS:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class StructuredLogger:
    """结构化日志器"""

    def __init__(self, logger_name: str, log_level: str = "INFO"):
        """
        Args:
            logger_name: 日志器名称
            log_level: 日志级别
        """
        self.logger = logging.getLogger(logger_name)

        # 验证日志级别
        try:
            level = getattr(logging, log_level.upper())
        except AttributeError:
            raise ValueError(f"Invalid log level: {log_level}")

        self.logger.setLevel(level)
        self.logger.propagate = False  # 防止重复输出

        # 避免重复添加handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)

    def log_retrieval_event(self, event_data: dict) -> None:
        """记录检索事件

        Args:
            event_data: 事件数据
        """
        self.logger.info(
            "retrieval_event",
            extra={
                "event_type": "retrieval",
                "query_id": event_data.get("query_id"),
                "query": event_data.get("query"),
                "total_duration_ms": event_data.get("total_duration_ms"),
                "results_count": event_data.get("results_count"),
                "stages": event_data.get("stages", {})
            }
        )

    def log_error_event(self, error: Exception, context: dict) -> None:
        """记录错误事件

        Args:
            error: 异常对象
            context: 上下文信息
        """
        self.logger.error(
            "error_event",
            extra={
                "event_type": "error",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context
            }
        )

    def log_performance_warning(self, metric_name: str,
                                current_value: float,
                                threshold: float) -> None:
        """记录性能警告

        Args:
            metric_name: 指标名称
            current_value: 当前值
            threshold: 阈值
        """
        self.logger.warning(
            "performance_warning",
            extra={
                "event_type": "performance_warning",
                "metric": metric_name,
                "current_value": current_value,
                "threshold": threshold
            }
        )
