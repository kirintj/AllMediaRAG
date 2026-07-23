import time
import fakeredis
import pytest
from core.task_queue.queue import TaskQueue
from core.task_queue.models import TaskMessage, TaskState, gen_task_id, gen_batch_id


@pytest.fixture
def queue(monkeypatch):
    """Create TaskQueue with fakeredis (no real Redis needed)"""
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


# -- Producer --

def test_enqueue_returns_task_id(queue):
    msg = _make_msg()
    task_id = queue.enqueue(msg, priority="high")
    assert task_id == "task_001"


def test_enqueue_writes_to_stream(queue):
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    length = queue._redis.xlen("stream:task:high")
    assert length == 1


def test_enqueue_creates_state_hash(queue):
    msg = _make_msg()
    queue.enqueue(msg)
    state = queue.get_state("task_001")
    assert state is not None
    assert state.status == "pending"
    assert state.phase == "queued"


def test_enqueue_low_priority(queue):
    msg = _make_msg()
    queue.enqueue(msg, priority="low")
    assert queue._redis.xlen("stream:task:low") == 1
    assert queue._redis.xlen("stream:task:high") == 0


def test_enqueue_batch(queue):
    msgs = [_make_msg(task_id=f"task_{i}", source=f"f{i}.pdf") for i in range(3)]
    batch_id, task_ids = queue.enqueue_batch(msgs)
    assert len(task_ids) == 3
    assert batch_id.startswith("batch_")
    batch_data = queue._redis.hgetall(f"hash:batch:{batch_id}")
    assert batch_data["total"] == "3"


# -- Consumer --

def test_dequeue_returns_empty_when_no_messages(queue):
    queue._redis.xgroup_create("stream:task:high", "test-group", id="0", mkstream=True)
    queue._redis.xgroup_create("stream:task:low", "test-group", id="0", mkstream=True)
    messages = queue.dequeue("test-group", "consumer-1")
    assert messages == []


def test_dequeue_reads_from_high_first(queue):
    msg_low = _make_msg(task_id="task_low", source="low.pdf")
    msg_high = _make_msg(task_id="task_high", source="high.pdf")
    queue.enqueue(msg_low, priority="low")
    queue.enqueue(msg_high, priority="high")

    queue._redis.xgroup_create("stream:task:high", "test-group", id="0", mkstream=True)
    queue._redis.xgroup_create("stream:task:low", "test-group", id="0", mkstream=True)

    messages = queue.dequeue("test-group", "consumer-1")
    assert len(messages) == 1
    assert messages[0]["msg"].task_id == "task_high"


def test_ack_removes_message_from_pending(queue):
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue._redis.xgroup_create("stream:task:high", "test-group", id="0", mkstream=True)

    messages = queue.dequeue("test-group", "consumer-1")
    stream_key = messages[0]["stream"]
    msg_id = messages[0]["id"]
    queue.ack(stream_key, msg_id, group="test-group")

    info = queue._redis.xinfo_groups("stream:task:high")
    assert info[0]["pending"] == 0


# -- State Management --

def test_update_state(queue):
    msg = _make_msg()
    queue.enqueue(msg)
    queue.update_state("task_001", status="processing", phase="parsing")
    state = queue.get_state("task_001")
    assert state.status == "processing"
    assert state.phase == "parsing"


def test_get_state_returns_none_for_missing(queue):
    assert queue.get_state("nonexistent") is None


def test_get_batch_state(queue):
    msgs = [_make_msg(task_id=f"task_{i}", batch_id="batch_001") for i in range(3)]
    queue.enqueue_batch(msgs)

    # Simulate completing 1, failing 1
    queue.update_state("task_0", status="completed", chunks=10)
    queue.update_state("task_1", status="failed", error="parse error")

    batch = queue.get_batch_state("batch_001")
    assert batch["total"] == 3
    assert batch["completed"] == 1
    assert batch["failed"] == 1


# -- Requeue --

def test_requeue_increments_retry(queue):
    msg = _make_msg()
    queue.enqueue(msg, priority="low")
    queue._redis.xgroup_create("stream:task:high", "test-group", id="0", mkstream=True)
    queue._redis.xgroup_create("stream:task:low", "test-group", id="0", mkstream=True)

    msg.retry = 0
    queue.requeue(msg)

    assert queue._redis.xlen("stream:task:high") >= 1
    state = queue.get_state("task_001")
    assert state.retry == 1


# -- Cleanup --

def test_cleanup_removes_old_tasks(queue):
    msg = _make_msg()
    queue.enqueue(msg)
    queue.update_state("task_001", started_at="1000000000.0")
    removed = queue.cleanup(max_age_hours=1)
    assert removed == 1
    assert queue.get_state("task_001") is None


# -- Consumer Group --

def test_ensure_consumer_group_creates_groups(queue):
    queue.ensure_consumer_group("test-group")
    groups_high = queue._redis.xinfo_groups("stream:task:high")
    groups_low = queue._redis.xinfo_groups("stream:task:low")
    assert any(g["name"] == "test-group" for g in groups_high)
    assert any(g["name"] == "test-group" for g in groups_low)


def test_ensure_consumer_group_idempotent(queue):
    queue.ensure_consumer_group("test-group")
    queue.ensure_consumer_group("test-group")  # should not error
    groups_high = queue._redis.xinfo_groups("stream:task:high")
    assert len(groups_high) == 1
