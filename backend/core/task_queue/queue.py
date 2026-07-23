from __future__ import annotations

import logging
import time

import redis

from core.task_queue.models import TaskMessage, TaskState, gen_batch_id

logger = logging.getLogger(__name__)

STREAM_HIGH = "stream:task:high"
STREAM_LOW = "stream:task:low"


class TaskQueue:
    """Redis Stream + Hash task queue"""

    def __init__(self, redis_url: str, task_ttl: int = 86400):
        self._redis = redis.from_url(redis_url, decode_responses=True)
        self._task_ttl = task_ttl

    # -- Consumer Group --

    def ensure_consumer_group(self, group: str):
        """Idempotent consumer group creation"""
        for stream in (STREAM_HIGH, STREAM_LOW):
            try:
                self._redis.xgroup_create(stream, group, id="0", mkstream=True)
            except redis.ResponseError as e:
                if "BUSYGROUP" not in str(e):
                    raise

    # -- Producer --

    def enqueue(self, msg: TaskMessage, priority: str = "low") -> str:
        """Enqueue a single message, return task_id"""
        stream = STREAM_HIGH if priority == "high" else STREAM_LOW
        self._redis.xadd(stream, msg.to_dict())

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
        """Batch enqueue, returns (batch_id, [task_ids])"""
        if not messages:
            batch_id = gen_batch_id()
            return batch_id, []

        batch_id = messages[0].batch_id or gen_batch_id()
        task_ids = []

        for msg in messages:
            msg.batch_id = batch_id
            self.enqueue(msg, priority="low")
            task_ids.append(msg.task_id)

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

    # -- Consumer --

    def dequeue(self, group: str, consumer: str, count: int = 1) -> list[dict]:
        """Priority dequeue: read high first, then block on low

        Returns list of dicts: [{"stream": "...", "id": "...", "msg": TaskMessage}, ...]
        """
        results = []

        # Non-blocking read from high
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

        # Block on low
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
        """Acknowledge message processed"""
        self._redis.xack(stream, group, msg_id)

    # -- State Management --

    def update_state(self, task_id: str, **fields):
        """Update task state hash"""
        key = f"hash:task:{task_id}"
        if not self._redis.exists(key):
            return
        self._redis.hset(key, mapping={k: str(v) for k, v in fields.items()})

    def get_state(self, task_id: str) -> TaskState | None:
        """Read task state"""
        data = self._redis.hgetall(f"hash:task:{task_id}")
        if not data:
            return None
        return TaskState.from_dict(data)

    def get_batch_state(self, batch_id: str) -> dict | None:
        """Read batch aggregate state"""
        batch_data = self._redis.hgetall(f"hash:batch:{batch_id}")
        if not batch_data:
            return None

        total = int(batch_data.get("total", 0))
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

        self._redis.hset(f"hash:batch:{batch_id}", mapping={
            "completed": str(completed),
            "failed": str(failed),
        })

        if completed + failed >= total:
            self._redis.hset(f"hash:batch:{batch_id}", "status", "completed")

        return {
            "batch_id": batch_id,
            "status": batch_data.get("status", "running"),
            "total": total,
            "completed": completed,
            "failed": failed,
            "user_id": batch_data.get("user_id", ""),
        }

    # -- Retry --

    def requeue(self, msg: TaskMessage):
        """Re-enqueue with retry + 1 to high priority"""
        msg.retry += 1
        self._redis.xadd(STREAM_HIGH, msg.to_dict())
        self.update_state(msg.task_id, retry=str(msg.retry))
        logger.info("Requeued task %s (retry %d)", msg.task_id, msg.retry)

    # -- Cleanup --

    def cleanup(self, max_age_hours: int = 24) -> int:
        """Remove expired task hashes"""
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        for key in self._redis.scan_iter(match="hash:task:*", count=100):
            data = self._redis.hgetall(key)
            started_at = float(data.get("started_at", 0))
            if started_at < cutoff:
                self._redis.delete(key)
                removed += 1
        return removed
