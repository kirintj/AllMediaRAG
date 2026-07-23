import json
from core.task_queue.models import TaskMessage, TaskState


def test_task_message_defaults():
    msg = TaskMessage(
        task_id="task_001",
        batch_id="batch_001",
        file_path="/data/test.pdf",
        source="test.pdf",
        user_id="user_001",
    )
    assert msg.parser_type == "auto"
    assert msg.enrichment == "{}"
    assert msg.retry == 0


def test_task_message_to_dict():
    msg = TaskMessage(
        task_id="task_001",
        batch_id="batch_001",
        file_path="/data/test.pdf",
        source="test.pdf",
        user_id="user_001",
    )
    d = msg.to_dict()
    assert d["task_id"] == "task_001"
    assert d["retry"] == "0"  # Redis stores as str
    assert isinstance(d, dict)


def test_task_message_from_dict():
    raw = {
        "task_id": "task_001",
        "batch_id": "batch_001",
        "file_path": "/data/test.pdf",
        "source": "test.pdf",
        "user_id": "user_001",
        "parser_type": "auto",
        "enrichment": "{}",
        "retry": "2",
    }
    msg = TaskMessage.from_dict(raw)
    assert msg.task_id == "task_001"
    assert msg.retry == 2  # converted from str to int


def test_task_state_defaults():
    state = TaskState(task_id="task_001", source="test.pdf", batch_id="batch_001")
    assert state.status == "pending"
    assert state.phase == "queued"
    assert state.chunks == 0
    assert state.error == ""
    assert state.retry == 0


def test_task_state_to_dict():
    state = TaskState(task_id="task_001", source="test.pdf", batch_id="batch_001")
    d = state.to_dict()
    assert d["status"] == "pending"
    assert d["chunks"] == "0"


def test_task_state_from_dict():
    raw = {
        "task_id": "task_001",
        "status": "completed",
        "phase": "done",
        "source": "test.pdf",
        "batch_id": "batch_001",
        "chunks": "42",
        "error": "",
        "retry": "0",
    }
    state = TaskState.from_dict(raw)
    assert state.status == "completed"
    assert state.chunks == 42
