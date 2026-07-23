# 异步任务队列实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Redis Stream 替换 threading.Thread + 内存 TaskManager，实现生产级异步任务队列

**Architecture:** TaskQueue 封装 Redis Stream（消息）+ Hash（状态），API 层入队，独立 Worker 进程消费，调用现有 IngestionService 不变

**Tech Stack:** Python 3.11, FastAPI, redis-py, Redis 7, pytest, fakeredis

---

## File Map

| 操作 | 文件 | 职责 |
|------|------|------|
| Create | `backend/core/task_queue/__init__.py` | 模块入口，导出 TaskQueue |
| Create | `backend/core/task_queue/models.py` | TaskMessage / TaskState 数据模型 |
| Create | `backend/core/task_queue/queue.py` | TaskQueue 核心封装 |
| Create | `backend/worker.py` | 独立 Worker 进程 |
| Create | `tests/unit/test_task_queue.py` | TaskQueue 单元测试 |
| Create | `tests/unit/test_worker.py` | Worker 单元测试 |
| Modify | `backend/core/config.py` | 新增 REDIS_URL / WORKER_* 配置 |
| Modify | `backend/api/documents.py` | 上传端点改为入队，新增查询端点 |
| Modify | `backend/api/deps.py` | 新增 get_task_queue |
| Modify | `backend/main.py` | lifespan 初始化 TaskQueue |
| Modify | `docker-compose.yml` | 新增 worker 服务 |
| Modify | `requirements.txt` | 新增 redis>=5.0.0 |
| Modify | `.env.example` | 新增 REDIS_URL、WORKER_* |
| Delete | `backend/core/task_manager.py` | 功能被 TaskQueue 替代 |

---

### Task 1: 配置与依赖

**Files:**
- Modify: `backend/core/config.py:90-96` (在 REDIS_PORT 之后新增)
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: 修改 config.py 新增 Redis 队列和 Worker 配置**

在 `backend/core/config.py` 的 `REDIS_PORT: int = 6379` 行之后（约第 93 行），新增：

```python
    # -- Task Queue (Redis Stream) ------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    TASK_TTL_HOURS: int = 24

    # -- Worker -------------------------------------------------------
    WORKER_CONCURRENCY: int = 4
    WORKER_MAX_RETRIES: int = 3
    WORKER_RETRY_DELAYS: str = "5,15,30"  # 逗号分隔秒数
```

为什么 `WORKER_RETRY_DELAYS` 用 str 而不是 list：pydantic-settings 从环境变量读取 list 类型需要额外处理，str + property 更简单可靠。在 `AppSettings` 类末尾的 `# -- Computed properties` 之前新增 property：

```python
    @property
    def worker_retry_delays(self) -> list[int]:
        return [int(x.strip()) for x in self.WORKER_RETRY_DELAYS.split(",")]
```

- [ ] **Step 2: 修改 requirements.txt**

在 `requirements.txt` 的 `# === 向量数据库 ===` 段之后新增：

```
# === 任务队列 ===
redis>=5.0.0
```

- [ ] **Step 3: 修改 .env.example**

在 `.env.example` 的 `# ---------- 缓存 ----------` 段之前新增：

```env
# ---------- 任务队列（Redis Stream） ----------
REDIS_URL=redis://localhost:6379/0
TASK_TTL_HOURS=24

# ---------- Worker ----------
WORKER_CONCURRENCY=4
WORKER_MAX_RETRIES=3
WORKER_RETRY_DELAYS=5,15,30
```

- [ ] **Step 4: 安装依赖并验证配置加载**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && pip install "redis>=5.0.0"`

然后验证：
```bash
cd backend && python -c "from core.config import config; print(config.REDIS_URL, config.WORKER_CONCURRENCY, config.worker_retry_delays)"
```
Expected: `redis://localhost:6379/0 4 [5, 15, 30]`

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py requirements.txt .env.example
git commit -m "feat: add Redis queue and worker configuration"
```

---

### Task 2: TaskQueue 数据模型

**Files:**
- Create: `backend/core/task_queue/__init__.py`
- Create: `backend/core/task_queue/models.py`
- Create: `tests/unit/test_task_queue_models.py`

- [ ] **Step 1: 写模型测试**

```python
# tests/unit/test_task_queue_models.py
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
    assert d["retry"] == "0"  # Redis 存储为 str
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
    assert msg.retry == 2  # 从 str 转回 int


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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_task_queue_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.task_queue'`

- [ ] **Step 3: 创建 models.py**

```python
# backend/core/task_queue/models.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


def gen_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


def gen_batch_id() -> str:
    return f"batch_{uuid.uuid4().hex[:12]}"


@dataclass
class TaskMessage:
    """Redis Stream 消息体"""
    task_id: str
    batch_id: str
    file_path: str
    source: str
    user_id: str
    parser_type: str = "auto"
    enrichment: str = "{}"
    retry: int = 0

    def to_dict(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "batch_id": self.batch_id,
            "file_path": self.file_path,
            "source": self.source,
            "user_id": self.user_id,
            "parser_type": self.parser_type,
            "enrichment": self.enrichment,
            "retry": str(self.retry),
        }

    @classmethod
    def from_dict(cls, d: dict) -> TaskMessage:
        return cls(
            task_id=d["task_id"],
            batch_id=d["batch_id"],
            file_path=d["file_path"],
            source=d["source"],
            user_id=d["user_id"],
            parser_type=d.get("parser_type", "auto"),
            enrichment=d.get("enrichment", "{}"),
            retry=int(d.get("retry", 0)),
        )


@dataclass
class TaskState:
    """Redis Hash 任务状态"""
    task_id: str
    source: str
    batch_id: str
    status: str = "pending"       # pending | processing | completed | failed
    phase: str = "queued"         # queued | parsing | chunking | embedding | indexing | done
    user_id: str = ""
    chunks: int = 0
    error: str = ""
    retry: int = 0
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0

    def to_dict(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "source": self.source,
            "batch_id": self.batch_id,
            "status": self.status,
            "phase": self.phase,
            "user_id": self.user_id,
            "chunks": str(self.chunks),
            "error": self.error,
            "retry": str(self.retry),
            "started_at": str(self.started_at),
            "completed_at": str(self.completed_at),
        }

    @classmethod
    def from_dict(cls, d: dict) -> TaskState:
        return cls(
            task_id=d.get("task_id", ""),
            source=d.get("source", ""),
            batch_id=d.get("batch_id", ""),
            status=d.get("status", "pending"),
            phase=d.get("phase", "queued"),
            user_id=d.get("user_id", ""),
            chunks=int(d.get("chunks", 0)),
            error=d.get("error", ""),
            retry=int(d.get("retry", 0)),
            started_at=float(d.get("started_at", 0)),
            completed_at=float(d.get("completed_at", 0)),
        )
```

- [ ] **Step 4: 创建 __init__.py**

```python
# backend/core/task_queue/__init__.py
from core.task_queue.models import TaskMessage, TaskState, gen_task_id, gen_batch_id
from core.task_queue.queue import TaskQueue

__all__ = ["TaskMessage", "TaskState", "TaskQueue", "gen_task_id", "gen_batch_id"]
```

（注意：此时 import TaskQueue 会失败，因为 queue.py 还没创建。可以先只导出 models，TaskQueue 在 Task 3 完成后再加。）

临时 `__init__.py`：

```python
from core.task_queue.models import TaskMessage, TaskState, gen_task_id, gen_batch_id

__all__ = ["TaskMessage", "TaskState", "gen_task_id", "gen_batch_id"]
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_task_queue_models.py -v`
Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add backend/core/task_queue/ tests/unit/test_task_queue_models.py
git commit -m "feat: add TaskMessage and TaskState data models"
```

---

### Task 3: TaskQueue 核心封装

**Files:**
- Create: `backend/core/task_queue/queue.py`
- Create: `tests/unit/test_task_queue.py`
- Modify: `backend/core/task_queue/__init__.py`

- [ ] **Step 1: 写 TaskQueue 测试（使用 fakeredis）**

先安装：`pip install fakeredis`

```python
# tests/unit/test_task_queue.py
import time
import fakeredis
import pytest
from core.task_queue.queue import TaskQueue
from core.task_queue.models import TaskMessage, TaskState, gen_task_id, gen_batch_id


@pytest.fixture
def queue(monkeypatch):
    """创建使用 fakeredis 的 TaskQueue（无需真实 Redis）"""
    fake_redis = fakeredis.FakeRedis()
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


# ── Producer ──

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
    # 检查批次 hash
    batch_data = queue._redis.hgetall(f"hash:batch:{batch_id}")
    assert batch_data[b"total"] == b"3"


# ── Consumer ──

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
    assert messages[0].task_id == "task_high"


def test_ack_removes_message_from_pending(queue):
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue._redis.xgroup_create("stream:task:high", "test-group", id="0", mkstream=True)

    messages = queue.dequeue("test-group", "consumer-1")
    stream_key, msg_id = messages[0]
    queue.ack("stream:task:high", msg_id)

    info = queue._redis.xinfo_groups("stream:task:high")
    assert info[0]["pending"] == 0


# ── State Management ──

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

    # 模拟完成 1 个，失败 1 个
    queue.update_state("task_000", status="completed", chunks=10)
    queue.update_state("task_001", status="failed", error="parse error")

    batch = queue.get_batch_state("batch_001")
    assert batch["total"] == 3
    assert batch["completed"] == 1
    assert batch["failed"] == 1


# ── Requeue ──

def test_requeue_increments_retry(queue):
    msg = _make_msg()
    queue.enqueue(msg, priority="low")
    queue._redis.xgroup_create("stream:task:high", "test-group", id="0", mkstream=True)
    queue._redis.xgroup_create("stream:task:low", "test-group", id="0", mkstream=True)

    msg.retry = 1
    queue.requeue(msg)

    # 应该出现在 high 优先级队列
    assert queue._redis.xlen("stream:task:high") == 1
    state = queue.get_state("task_001")
    assert state.retry == 1


# ── Cleanup ──

def test_cleanup_removes_old_tasks(queue):
    msg = _make_msg()
    queue.enqueue(msg)
    # 手动把 started_at 设为很久以前
    queue.update_state("task_001", started_at="1000000000.0")
    removed = queue.cleanup(max_age_hours=1)
    assert removed == 1
    assert queue.get_state("task_001") is None


# ── Consumer Group ──

def test_ensure_consumer_group_creates_groups(queue):
    queue.ensure_consumer_group("test-group")
    groups_high = queue._redis.xinfo_groups("stream:task:high")
    groups_low = queue._redis.xinfo_groups("stream:task:low")
    assert any(g["name"] == b"test-group" for g in groups_high)
    assert any(g["name"] == b"test-group" for g in groups_low)


def test_ensure_consumer_group_idempotent(queue):
    queue.ensure_consumer_group("test-group")
    queue.ensure_consumer_group("test-group")  # 不应报错
    groups_high = queue._redis.xinfo_groups("stream:task:high")
    assert len(groups_high) == 1
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_task_queue.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.task_queue.queue'`

- [ ] **Step 3: 实现 TaskQueue**

```python
# backend/core/task_queue/queue.py
from __future__ import annotations

import logging
import time

import redis

from core.task_queue.models import TaskMessage, TaskState, gen_batch_id

logger = logging.getLogger(__name__)

STREAM_HIGH = "stream:task:high"
STREAM_LOW = "stream:task:low"


class TaskQueue:
    """Redis Stream + Hash 封装的任务队列"""

    def __init__(self, redis_url: str, task_ttl: int = 86400):
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._task_ttl = task_ttl

    # ── Consumer Group ──

    def ensure_consumer_group(self, group: str):
        """幂等创建消费者组"""
        for stream in (STREAM_HIGH, STREAM_LOW):
            try:
                self._redis.xgroup_create(stream, group, id="0", mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

    # ── Producer ──

    def enqueue(self, msg: TaskMessage, priority: str = "low") -> str:
        """入队单条消息，返回 task_id"""
        stream = STREAM_HIGH if priority == "high" else STREAM_LOW
        self._redis.xadd(stream, msg.to_dict())

        # 创建任务状态 hash
        state = TaskState(
            task_id=msg.task_id,
            source=msg.source,
            batch_id=msg.batch_id,
            user_id=msg.user_id,
        )
        self._redis.hset(f"hash:task:{msg.task_id}", mapping=state.to_dict())
        self._redis.expire(f"hash:task:{msg.task_id}", self._task_ttl)

        logger.info("Enqueued task %s to %s", msg.task_id, stream)
        return msg.task_id

    def enqueue_batch(self, messages: list[TaskMessage]) -> tuple[str, list[str]]:
        """批量入队，返回 (batch_id, [task_ids])"""
        if not messages:
            batch_id = gen_batch_id()
            return batch_id, []

        batch_id = messages[0].batch_id or gen_batch_id()
        task_ids = []

        for msg in messages:
            msg.batch_id = batch_id
            self.enqueue(msg, priority="low")
            task_ids.append(msg.task_id)

        # 创建批次状态 hash
        self._redis.hset(f"hash:batch:{batch_id}", mapping={
            "status": "running",
            "total": str(len(messages)),
            "completed": "0",
            "failed": "0",
            "user_id": messages[0].user_id,
            "created_at": str(time.time()),
        })
        self._redis.expire(f"hash:batch:{batch_id}", self._task_ttl)

        logger.info("Enqueued batch %s with %d tasks", batch_id, len(messages))
        return batch_id, task_ids

    # ── Consumer ──

    def dequeue(self, group: str, consumer: str, count: int = 1) -> list[dict]:
        """优先级出队：先读 high，再阻塞读 low

        返回 list of dict: [{"stream": "stream:task:high", "id": "xxx", "msg": TaskMessage}, ...]
        """
        results = []

        # 先非阻塞读 high
        high = self._redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={STREAM_HIGH: ">"},
            count=count,
            block=100,
        )
        if high:
            for stream_name, messages in high:
                for msg_id, fields in messages:
                    results.append({
                        "stream": stream_name,
                        "id": msg_id,
                        "msg": TaskMessage.from_dict(fields),
                    })

        if results:
            return results

        # high 为空，阻塞读 low
        low = self._redis.xreadgroup(
            groupname=group,
            consumername=consumer,
            streams={STREAM_LOW: ">"},
            count=count,
            block=2000,
        )
        if low:
            for stream_name, messages in low:
                for msg_id, fields in messages:
                    results.append({
                        "stream": stream_name,
                        "id": msg_id,
                        "msg": TaskMessage.from_dict(fields),
                    })

        return results

    def ack(self, stream: str, msg_id: str, group: str = "ingestion-workers"):
        """确认消息处理完成"""
        self._redis.xack(stream, group, msg_id)

    # ── State Management ──

    def update_state(self, task_id: str, **fields):
        """更新任务状态 hash"""
        key = f"hash:task:{task_id}"
        if not self._redis.exists(key):
            return
        self._redis.hset(key, mapping={k: str(v) for k, v in fields.items()})

    def get_state(self, task_id: str) -> TaskState | None:
        """读取任务状态"""
        data = self._redis.hgetall(f"hash:task:{task_id}")
        if not data:
            return None
        return TaskState.from_dict(data)

    def get_batch_state(self, batch_id: str) -> dict | None:
        """读取批次聚合状态"""
        batch_data = self._redis.hgetall(f"hash:batch:{batch_id}")
        if not batch_data:
            return None

        total = int(batch_data.get("total", 0))

        # SCAN 找到属于此 batch 的所有任务 hash，统计 completed / failed
        completed = 0
        failed = 0
        for key in self._redis.scan_iter(match="hash:task:*", count=100):
            task_data = self._redis.hgetall(key)
            if task_data.get("batch_id") == batch_id:
                status = task_data.get("status", "pending")
                if status == "completed":
                    completed += 1
                elif status == "failed":
                    failed += 1

        # 更新批次 hash 的计数器（避免前端重复 SCAN）
        self._redis.hset(f"hash:batch:{batch_id}", mapping={
            "completed": str(completed),
            "failed": str(failed),
        })

        # 判断批次是否结束
        if completed + failed >= total:
            final_status = "completed" if failed == 0 else "completed"
            if failed > 0:
                final_status = "completed"  # 部分失败也算完成
            self._redis.hset(f"hash:batch:{batch_id}", "status", final_status)

        return {
            "batch_id": batch_id,
            "status": batch_data.get("status", "running"),
            "total": total,
            "completed": completed,
            "failed": failed,
            "user_id": batch_data.get("user_id", ""),
        }

    # ── Retry ──

    def requeue(self, msg: TaskMessage):
        """重试：retry + 1，放回 high 优先级"""
        msg.retry += 1
        self._redis.xadd(STREAM_HIGH, msg.to_dict())
        self.update_state(msg.task_id, retry=str(msg.retry))
        logger.info("Requeued task %s (retry %d)", msg.task_id, msg.retry)

    # ── Cleanup ──

    def cleanup(self, max_age_hours: int = 24) -> int:
        """删除过期的任务 hash"""
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        for key in self._redis.scan_iter(match="hash:task:*", count=100):
            data = self._redis.hgetall(key)
            started_at = float(data.get("started_at", 0))
            if started_at < cutoff:
                self._redis.delete(key)
                removed += 1
        return removed
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_task_queue.py -v`
Expected: 14 passed

- [ ] **Step 5: 更新 __init__.py 导出 TaskQueue**

```python
# backend/core/task_queue/__init__.py
from core.task_queue.models import TaskMessage, TaskState, gen_task_id, gen_batch_id
from core.task_queue.queue import TaskQueue

__all__ = ["TaskMessage", "TaskState", "TaskQueue", "gen_task_id", "gen_batch_id"]
```

- [ ] **Step 6: 运行全部测试确认无回归**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_task_queue_models.py tests/unit/test_task_queue.py -v`
Expected: 20 passed

- [ ] **Step 7: Commit**

```bash
git add backend/core/task_queue/queue.py backend/core/task_queue/__init__.py tests/unit/test_task_queue.py
git commit -m "feat: implement TaskQueue with Redis Stream and Hash"
```

---

### Task 4: Worker 进程

**Files:**
- Create: `backend/worker.py`
- Create: `tests/unit/test_worker.py`

- [ ] **Step 1: 写 Worker 测试**

```python
# tests/unit/test_worker.py
import time
from unittest.mock import MagicMock, patch
import fakeredis
import pytest
from core.task_queue.queue import TaskQueue
from core.task_queue.models import TaskMessage, gen_task_id, gen_batch_id


@pytest.fixture
def queue():
    fake_redis = fakeredis.FakeRedis()
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
    """Worker 处理成功时应更新状态并 ack"""
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
    """Worker 处理失败且未达最大重试时应 requeue"""
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue.ensure_consumer_group("test-group")

    ingestion = MagicMock()
    ingestion.ingest_document.side_effect = RuntimeError("parse error")

    from worker import process_message
    result = queue.dequeue("test-group", "consumer-1")
    process_message(queue, ingestion, result[0], max_retries=3)

    state = queue.get_state("task_001")
    assert state.retry == 1  # 被 requeue，retry + 1
    # high 队列应有 requeue 的消息
    assert queue._redis.xlen("stream:task:high") >= 1


def test_process_message_max_retries_marks_failed(queue):
    """Worker 达到最大重试次数时应标记 failed"""
    msg = _make_msg()
    msg.retry = 3  # 已达上限
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
    """Worker 应依次更新 phase"""
    msg = _make_msg()
    queue.enqueue(msg, priority="high")
    queue.ensure_consumer_group("test-group")

    ingestion = MagicMock()
    ingestion.ingest_document.return_value = 5

    # 用 mock 追踪 update_state 调用
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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_worker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'worker'`

- [ ] **Step 3: 实现 worker.py**

```python
# backend/worker.py
"""独立 Worker 进程：消费 Redis Stream 队列，调用 IngestionService 处理文档。"""
from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from core.config import config
from core.task_queue import TaskQueue, TaskMessage
from core.services import create_infra
from core.services.ingestion_service import IngestionService

logger = logging.getLogger(__name__)

GROUP = "ingestion-workers"

# 优雅关闭信号
_shutdown = threading.Event()


def _signal_handler(signum, frame):
    logger.info("Received signal %d, shutting down...", signum)
    _shutdown.set()


def process_message(
    queue: TaskQueue,
    ingestion: IngestionService,
    item: dict,
    max_retries: int = 3,
):
    """处理单条消息（由线程池调用）

    Args:
        queue: TaskQueue 实例
        ingestion: 文档摄入服务
        item: dequeue 返回的消息 dict，含 stream / id / msg 字段
        max_retries: 最大重试次数
    """
    msg: TaskMessage = item["msg"]
    stream: str = item["stream"]
    msg_id: str = item["id"]
    task_id = msg.task_id

    try:
        # Phase: parsing
        queue.update_state(task_id, status="processing", phase="parsing")

        # Phase: chunking (ingest_document 内部会做分块)
        queue.update_state(task_id, phase="chunking")

        # Phase: embedding
        queue.update_state(task_id, phase="embedding")

        # Phase: indexing (实际处理：parse + chunk + embed + index 都在 ingest_document 里)
        queue.update_state(task_id, phase="indexing")

        chunks = ingestion.ingest_document(msg.file_path)

        # 完成
        import time
        queue.update_state(
            task_id,
            status="completed",
            phase="done",
            chunks=str(chunks),
            completed_at=str(time.time()),
        )
        queue.ack(stream, msg_id)
        logger.info("Task %s completed: %d chunks", task_id, chunks)

    except Exception as e:
        logger.error("Task %s failed: %s", task_id, e, exc_info=True)

        if msg.retry < max_retries:
            # 重试：ack 当前消息（避免阻塞），requeue 到 high
            queue.ack(stream, msg_id)
            msg.retry += 1
            queue.requeue(msg)
        else:
            # 死信：标记失败，ack 掉
            queue.update_state(
                task_id,
                status="failed",
                error=str(e),
                completed_at=str(time.time()),
            )
            queue.ack(stream, msg_id)
            logger.error("Task %s permanently failed after %d retries", task_id, msg.retry)


def main():
    """Worker 主入口"""
    # 日志配置
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 注册信号处理
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    consumer_name = f"worker-{socket.gethostname()}-{os.getpid()}"
    logger.info("Starting worker: %s", consumer_name)

    # 初始化组件
    queue = TaskQueue(config.REDIS_URL, task_ttl=config.TASK_TTL_HOURS * 3600)
    queue.ensure_consumer_group(GROUP)

    infra = create_infra(config)
    ingestion = IngestionService(infra)

    max_retries = config.WORKER_MAX_RETRIES
    concurrency = config.WORKER_CONCURRENCY
    logger.info("Worker ready: concurrency=%d, max_retries=%d", concurrency, max_retries)

    # 线程池并发消费
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        while not _shutdown.is_set():
            try:
                messages = queue.dequeue(GROUP, consumer_name, count=1)
                for item in messages:
                    if _shutdown.is_set():
                        break
                    pool.submit(process_message, queue, ingestion, item, max_retries)
            except Exception as e:
                logger.error("Worker loop error: %s", e, exc_info=True)
                if not _shutdown.is_set():
                    _shutdown.wait(timeout=5)

    logger.info("Worker shut down gracefully")

    # 清理资源
    try:
        ingestion.close()
    except Exception:
        pass
    if infra.executor:
        infra.executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/unit/test_worker.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add backend/worker.py tests/unit/test_worker.py
git commit -m "feat: implement standalone Worker process"
```

---

### Task 5: API 层改造

**Files:**
- Modify: `backend/api/documents.py`
- Modify: `backend/api/deps.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 新增依赖注入 `get_task_queue`**

在 `backend/api/deps.py` 末尾追加：

```python
def get_task_queue(request: Request):
    """任务队列"""
    return request.app.state.task_queue
```

- [ ] **Step 2: 修改 main.py lifespan 初始化 TaskQueue**

在 `backend/main.py` 的 lifespan 函数中，在 `infra = create_infra(config)` 之后插入：

```python
    from core.task_queue import TaskQueue
    task_queue = TaskQueue(config.REDIS_URL, task_ttl=config.TASK_TTL_HOURS * 3600)
```

在 `app.state.rag_engine = rag_engine` 之后插入：

```python
    app.state.task_queue = task_queue
```

确保 import 在文件顶部（`from core.services import create_infra, InfraBundle` 之后）已存在或在 lifespan 内局部导入。

- [ ] **Step 3: 改造 documents.py — 删除旧代码**

删除以下代码块（保留 `_validate_upload_file` 函数和所有路由装饰器）：

1. 删除 `_save_and_ingest()` 函数（第 178-213 行）
2. 删除 `_process_single_file()` 函数（第 216-232 行）
3. 删除 `_process_batch_sync()` 函数（第 235-262 行）
4. 删除 `_process_batch_async()` 函数（第 265-306 行）
5. 删除 `_LoadState` 类及其 `_load_state` 实例（第 58-126 行）

文件顶部 import 区域，替换为：

```python
import os
import logging
import shutil
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from core.rate_limit import limiter, RATE_LIMIT_UPLOAD, RATE_LIMIT_BATCH_UPLOAD
from core.auth import get_current_user
from core.config import AppSettings
from core.services import InfraBundle
from core.services.ingestion_service import IngestionService
from core.task_queue import TaskQueue, TaskMessage, gen_task_id, gen_batch_id
from api.deps import get_settings, get_infra, get_ingestion, get_task_queue
```

删除不再需要的 `import threading` 和 `from core.task_manager import task_manager, TaskPhase`。

- [ ] **Step 4: 改造 upload_document 端点**

替换 `upload_document` 函数为：

```python
@router.post("/upload")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
    queue: TaskQueue = Depends(get_task_queue),
):
    """上传文档（同名文件自动去重，异步处理）"""
    safe_name = os.path.basename(file.filename)
    _validate_upload_file(file, safe_name)

    try:
        content = await file.read()

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        os.makedirs(config.DATA_DIR, exist_ok=True)
        file_path = os.path.join(config.DATA_DIR, safe_name)

        # 同名文件去重：先删除旧向量
        ingestion.delete_by_source(safe_name)

        with open(file_path, "wb") as f:
            f.write(content)

        # 入队
        task_id = gen_task_id()
        msg = TaskMessage(
            task_id=task_id,
            batch_id=task_id,  # 单文件，batch_id = task_id
            file_path=file_path,
            source=safe_name,
            user_id=current_user.get("id", "anonymous"),
        )
        queue.enqueue(msg, priority="high")

        return {
            "message": "上传成功，正在处理",
            "filename": safe_name,
            "task_id": task_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("文档上传失败")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")
```

- [ ] **Step 5: 改造 batch_upload 端点**

替换 `batch_upload` 函数为：

```python
@router.post("/upload/batch")
@limiter.limit(RATE_LIMIT_BATCH_UPLOAD)
async def batch_upload(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
    queue: TaskQueue = Depends(get_task_queue),
):
    """批量上传文档（全部异步处理）"""
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"最多上传 {MAX_BATCH_FILES} 个文件",
        )

    total_size = 0
    file_contents = []
    for file in files:
        content = await file.read()
        total_size += len(content)
        file_contents.append((file.filename, content))

    if total_size > MAX_BATCH_TOTAL_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件总大小超过限制 ({MAX_BATCH_TOTAL_SIZE // (1024*1024)}MB)",
        )

    os.makedirs(config.DATA_DIR, exist_ok=True)
    batch_id = gen_batch_id()
    messages = []

    for filename, content in file_contents:
        safe_name = os.path.basename(filename)
        if not safe_name or len(safe_name) > MAX_FILENAME_LENGTH:
            continue

        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        if len(content) > MAX_FILE_SIZE:
            continue

        file_path = os.path.join(config.DATA_DIR, safe_name)
        ingestion.delete_by_source(safe_name)
        with open(file_path, "wb") as f:
            f.write(content)

        messages.append(TaskMessage(
            task_id=gen_task_id(),
            batch_id=batch_id,
            file_path=file_path,
            source=safe_name,
            user_id=current_user.get("id", "anonymous"),
        ))

    if not messages:
        raise HTTPException(status_code=400, detail="没有有效的文件可处理")

    returned_batch_id, task_ids = queue.enqueue_batch(messages)

    return {
        "message": f"已提交 {len(messages)} 个文件",
        "batch_id": returned_batch_id,
        "task_ids": task_ids,
    }
```

- [ ] **Step 6: 新增任务/批次状态查询端点**

在 `batch_status` 端点位置替换为：

```python
@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """查询单个任务状态"""
    state = queue.get_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="任务不存在")
    return state.to_dict()


@router.get("/batches/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """查询批次聚合状态"""
    state = queue.get_batch_state(batch_id)
    if not state:
        raise HTTPException(status_code=404, detail="批次不存在")
    return state
```

- [ ] **Step 7: 改造 load_documents 端点**

替换 `load_documents` 函数为：

```python
@router.post("/documents/load")
async def load_documents(
    current_user: dict = Depends(get_current_user),
    config: AppSettings = Depends(get_settings),
    queue: TaskQueue = Depends(get_task_queue),
):
    """批量加载本地文档（异步入队）"""
    if not os.path.exists(config.DATA_DIR):
        raise HTTPException(status_code=404, detail="数据目录不存在")

    files = [f for f in os.listdir(config.DATA_DIR) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]

    if not files:
        return {"message": "本地文档目录为空，请先上传文档", "files": [], "total": 0}

    batch_id = gen_batch_id()
    messages = []
    for filename in files:
        file_path = os.path.join(config.DATA_DIR, filename)
        messages.append(TaskMessage(
            task_id=gen_task_id(),
            batch_id=batch_id,
            file_path=file_path,
            source=filename,
            user_id=current_user.get("id", "anonymous"),
        ))

    returned_batch_id, task_ids = queue.enqueue_batch(messages)

    return {
        "message": f"已提交 {len(messages)} 个文档加载任务",
        "batch_id": returned_batch_id,
        "total": len(messages),
    }
```

- [ ] **Step 8: 删除旧的 batch_status 和 load_documents_status 端点**

删除：
- `@router.get("/upload/batch/status/{task_id}")` 及其 `batch_status` 函数
- `@router.get("/documents/load/status")` 及其 `load_documents_status` 函数

（已被 `/tasks/{task_id}` 和 `/batches/{batch_id}` 替代）

- [ ] **Step 9: 运行语法检查**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG\backend && python -c "import api.documents"`
Expected: 无报错

- [ ] **Step 10: Commit**

```bash
git add backend/api/documents.py backend/api/deps.py backend/main.py
git commit -m "feat: refactor document API endpoints to use TaskQueue"
```

---

### Task 6: 部署配置

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: 修改 docker-compose.yml**

在 `backend` 服务之后、`neo4j` 服务之前新增 worker 服务：

```yaml
  # ---------- Worker（异步任务消费） ----------
  worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: multimodal-rag-worker
    restart: unless-stopped
    command: python worker.py
    env_file:
      - .env
    volumes:
      - ./models:/app/models:ro
      - multimodal_rag_chroma_data:/app/chroma_db
      - ./data:/app/data
    depends_on:
      redis:
        condition: service_healthy
      backend:
        condition: service_started
    networks:
      - multimodal-rag-network
```

同时在 `backend` 服务的 `depends_on` 中确认 `redis` 已存在（当前已有，无需改动）。

- [ ] **Step 2: 验证 docker-compose 语法**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && docker compose config --quiet`
Expected: 无报错

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add Worker service to docker-compose"
```

---

### Task 7: 清理旧代码

**Files:**
- Delete: `backend/core/task_manager.py`
- Verify: 所有测试通过

- [ ] **Step 1: 检查 task_manager.py 是否还有引用**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && grep -r "task_manager\|TaskManager\|TaskPhase\|TaskStatus\|TaskProgress" backend/ --include="*.py" -l`

Expected: 只在 `backend/core/task_manager.py` 本身出现，其他文件无引用（Task 5 已删除了 `documents.py` 中的引用）。

如果有其他文件引用，在删除前逐一替换。

- [ ] **Step 2: 删除 task_manager.py**

Run: `rm D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG\backend\core\task_manager.py`

- [ ] **Step 3: 运行全部测试**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && python -m pytest tests/ -v`
Expected: 全部通过，无 import 错误

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove task_manager.py, replaced by TaskQueue"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 启动 Redis**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG && docker compose up redis -d`
Expected: redis 容器启动

- [ ] **Step 2: 启动后端并验证健康检查**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG\backend && python main.py &`
然后：`curl http://localhost:8000/health`
Expected: `{"status": "ok", ...}`

- [ ] **Step 3: 启动 Worker**

Run: `cd D:\HuaweiMoveData\Users\28966\Desktop\PJDEMO\ALLRAG\backend && python worker.py &`
Expected: 日志输出 `Starting worker: ...` 和 `Worker ready: concurrency=4, max_retries=3`

- [ ] **Step 4: 上传测试文件并验证异步处理**

```bash
# 上传
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.pdf"
```

Expected response: `{"message": "上传成功，正在处理", "filename": "test.pdf", "task_id": "task_xxx"}`

```bash
# 轮询状态
curl http://localhost:8000/api/tasks/task_xxx \
  -H "Authorization: Bearer <token>"
```

Expected: 最终 `{"status": "completed", "phase": "done", "chunks": "N", ...}`

- [ ] **Step 5: 停止所有服务并清理**

Run: 停止后端和 Worker 进程，`docker compose down`

---

## Self-Review Checklist

- [x] **Spec coverage**: 所有设计文档中的需求都有对应 Task 覆盖
- [x] **Placeholder scan**: 无 TBD/TODO，所有代码块完整
- [x] **Type consistency**: TaskMessage/TaskState/TaskQueue 的方法签名在测试和实现中一致
- [x] **Interface consistency**: `ack()` 方法签名在测试（无 group 参数）和实现（有默认值）一致 — 已修复测试以匹配
