import time
from unittest.mock import MagicMock, patch
import fakeredis
import pytest
from core.task_queue.queue import TaskQueue
from core.task_queue.models import TaskMessage, gen_task_id, gen_batch_id


@pytest.fixture
def queue():
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    q = TaskQueue.__new__(TaskQueue)
    q._redis = fake_redis
    q._task_ttl = 86400
    return q


def _make_msg(task_id="task_001", batch_id="batch_001", source="test.pdf") -> TaskMessage:
    return TaskMessage(
        task_id=task_id,
        batch_id=batch_id,
        file_path=f"/data/{source}",
        source=source,
        user_id="user_001",
    )


def test_process_message_success(queue):
    """Worker should update state and ack on success"""
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue.ensure_consumer_group("test-group")

    ingestion = MagicMock()
    ingestion.ingest_document.return_value = 42

    from worker import process_message
    result = queue.dequeue("test-group", "consumer-1")
    process_message(queue, ingestion, result[0], max_retries=3)

    state = queue.get_state("task_001")
    assert state.status == "completed"
    assert state.chunks == 42
    assert state.phase == "done"


def test_process_message_failure_retries(queue):
    """Worker should requeue on failure when under max retries"""
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue.ensure_consumer_group("test-group")

    ingestion = MagicMock()
    ingestion.ingest_document.side_effect = RuntimeError("parse error")

    from worker import process_message
    result = queue.dequeue("test-group", "consumer-1")
    process_message(queue, ingestion, result[0], max_retries=3)

    state = queue.get_state("task_001")
    assert state.retry == 1
    assert queue._redis.xlen("stream:task:high") >= 1


def test_process_message_max_retries_marks_failed(queue):
    """Worker should mark failed when max retries reached"""
    msg = _make_msg()
    msg.retry = 3
    queue.enqueue(msg, priority="high")
    queue.ensure_consumer_group("test-group")

    ingestion = MagicMock()
    ingestion.ingest_document.side_effect = RuntimeError("parse error")

    from worker import process_message
    result = queue.dequeue("test-group", "consumer-1")
    process_message(queue, ingestion, result[0], max_retries=3)

    state = queue.get_state("task_001")
    assert state.status == "failed"
    assert "parse error" in state.error


def test_process_message_updates_phases(queue):
    """Worker should update phase sequentially"""
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue.ensure_consumer_group("test-group")

    ingestion = MagicMock()
    ingestion.ingest_document.return_value = 5

    phases_seen = []
    original_update = queue.update_state

    def tracking_update(task_id, **fields):
        if "phase" in fields:
            phases_seen.append(fields["phase"])
        original_update(task_id, **fields)

    queue.update_state = tracking_update

    from worker import process_message
    result = queue.dequeue("test-group", "consumer-1")
    process_message(queue, ingestion, result[0], max_retries=3)

    assert "parsing" in phases_seen
    assert "done" in phases_seen
