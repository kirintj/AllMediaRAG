import pytest
import json
from unittest.mock import Mock

def test_logger_logs_retrieval_event():
    """测试日志记录检索事件"""
    from core.observability.logger import StructuredLogger

    logger = StructuredLogger("test")

    event_data = {
        "query_id": "test-123",
        "query": "测试查询",
        "total_duration_ms": 250,
        "results_count": 5
    }

    # 应该不抛出异常
    logger.log_retrieval_event(event_data)

def test_logger_logs_error_event():
    """测试日志记录错误事件"""
    from core.observability.logger import StructuredLogger

    logger = StructuredLogger("test")

    error = ValueError("测试错误")
    context = {"query_id": "test-123"}

    # 应该不抛出异常
    logger.log_error_event(error, context)

def test_logger_logs_performance_warning():
    """测试日志记录性能警告"""
    from core.observability.logger import StructuredLogger

    logger = StructuredLogger("test")

    # 应该不抛出异常
    logger.log_performance_warning("latency", 500, 300)
