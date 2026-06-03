import pytest
import json
import logging
from io import StringIO
from core.observability.logger import StructuredLogger, JSONFormatter


@pytest.fixture
def log_stream():
    """创建日志捕获流"""
    return StringIO()


@pytest.fixture
def logger_with_capture(log_stream):
    """创建带捕获的logger，使用唯一名称避免handler污染"""
    logger_name = "test_capture_id47"
    logger = StructuredLogger(logger_name)
    # 清除现有handler
    logger.logger.handlers.clear()
    # 添加捕获handler
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(JSONFormatter())
    logger.logger.addHandler(handler)
    return logger, log_stream


def test_logger_retrieval_event_structure(logger_with_capture):
    """测试检索事件日志结构"""
    logger, stream = logger_with_capture

    event_data = {
        "query_id": "test-123",
        "query": "测试查询",
        "total_duration_ms": 250,
        "results_count": 5
    }

    logger.log_retrieval_event(event_data)

    stream.seek(0)
    log_output = stream.getvalue()
    log_data = json.loads(log_output)

    assert "timestamp" in log_data
    assert log_data["level"] == "INFO"
    assert log_data["event_type"] == "retrieval"
    assert log_data["query_id"] == "test-123"
    assert log_data["total_duration_ms"] == 250


def test_logger_error_event_structure(logger_with_capture):
    """测试错误事件日志结构"""
    logger, stream = logger_with_capture

    error = ValueError("测试错误")
    context = {"query_id": "test-123"}

    logger.log_error_event(error, context)

    stream.seek(0)
    log_output = stream.getvalue()
    log_data = json.loads(log_output)

    assert log_data["level"] == "ERROR"
    assert log_data["event_type"] == "error"
    assert log_data["error_type"] == "ValueError"
    assert log_data["error_message"] == "测试错误"


def test_logger_performance_warning_structure(logger_with_capture):
    """测试性能警告日志结构"""
    logger, stream = logger_with_capture

    logger.log_performance_warning("latency", 500, 300)

    stream.seek(0)
    log_output = stream.getvalue()
    log_data = json.loads(log_output)

    assert log_data["level"] == "WARNING"
    assert log_data["event_type"] == "performance_warning"
    assert log_data["metric"] == "latency"
    assert log_data["current_value"] == 500


def test_logger_invalid_level():
    """测试无效日志级别"""
    with pytest.raises(ValueError, match="Invalid log level"):
        StructuredLogger("test_invalid", log_level="INVALID")
