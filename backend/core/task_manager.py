"""Task Manager for batch upload progress tracking.

Provides thread-safe task lifecycle management including progress tracking,
failure recording, and cleanup of stale tasks.
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPhase(Enum):
    """Current processing phase of a batch task."""
    UPLOADING = "uploading"
    INDEXING = "indexing"


@dataclass
class FailedItem:
    """Record of a single failed item during processing."""
    filename: str
    error: str
    retries: int = 0


@dataclass
class TaskProgress:
    """Tracks progress and failures for a batch task.

    Attributes:
        task_id: Unique identifier for this task.
        total: Total number of items to process.
        status: Current task status.
        phase: Current processing phase.
        upload_current: Number of items uploaded so far.
        upload_failed: List of items that failed during upload.
        index_current: Number of items indexed so far.
        index_success: Number of items successfully indexed.
        index_failed: List of items that failed during indexing.
        started_at: Unix timestamp when the task was created.
        error: Error message if the task failed.
    """
    task_id: str
    total: int
    status: TaskStatus = TaskStatus.PENDING
    phase: TaskPhase = TaskPhase.UPLOADING
    upload_current: int = 0
    upload_failed: list = field(default_factory=list)
    index_current: int = 0
    index_success: int = 0
    index_failed: list = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    error: Optional[str] = None

    def snapshot(self) -> dict:
        """Generate a serializable snapshot of the current progress.

        Returns:
            Dictionary containing all task progress fields.
        """
        elapsed = round(time.time() - self.started_at, 1) if self.started_at else 0
        estimated_remaining = None
        if self.status == TaskStatus.RUNNING and self.upload_current > 0:
            # 基于上传阶段进度估算剩余时间
            progress = self.upload_current / self.total if self.total > 0 else 0
            if progress > 0:
                estimated_remaining = round(elapsed * (1 - progress) / progress, 1)

        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "phase": self.phase.value,
            "total": self.total,
            "upload": {
                "current": self.upload_current,
                "total": self.total,
                "failed": [
                    {"name": f.filename, "reason": f.error}
                    for f in self.upload_failed
                ],
            },
            "index": {
                "current": self.index_current,
                "total": self.total,
                "success": self.index_success,
                "failed": [
                    {"name": f.filename, "reason": f.error}
                    for f in self.index_failed
                ],
            },
            "elapsed_seconds": elapsed,
            "estimated_remaining": estimated_remaining,
            "started_at": self.started_at,
            "error": self.error,
        }


class TaskManager:
    """Thread-safe manager for batch upload tasks.

    Maintains an in-memory registry of active tasks and provides methods
    to create, update, query, and clean up tasks.
    """

    def __init__(self):
        self._tasks: dict[str, TaskProgress] = {}
        self._lock = threading.Lock()

    def create_task(self, total: int) -> str:
        """Create a new batch task.

        Args:
            total: Total number of items to process.

        Returns:
            The unique task ID (prefixed with "batch_").
        """
        task_id = f"batch_{uuid.uuid4().hex[:12]}"
        task = TaskProgress(task_id=task_id, total=total)
        with self._lock:
            self._tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """Retrieve a task by ID.

        Args:
            task_id: The task identifier.

        Returns:
            The TaskProgress if found, otherwise None.
        """
        with self._lock:
            return self._tasks.get(task_id)

    def update_upload_progress(self, task_id: str, current: int) -> None:
        """Update the upload progress counter.

        Args:
            task_id: The task identifier.
            current: Current number of uploaded items.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.upload_current = current

    def add_upload_failure(self, task_id: str, filename: str, error: str) -> None:
        """Record an upload failure.

        Args:
            task_id: The task identifier.
            filename: Name of the file that failed.
            error: Description of the failure.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.upload_failed.append(FailedItem(filename=filename, error=error))

    def set_phase(self, task_id: str, phase: TaskPhase) -> None:
        """Transition the task to a new processing phase.

        Args:
            task_id: The task identifier.
            phase: The target phase.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.phase = phase

    def update_index_progress(
        self, task_id: str, current: int, success: int
    ) -> None:
        """Update the indexing progress counters.

        Args:
            task_id: The task identifier.
            current: Current number of items processed for indexing.
            success: Number of items successfully indexed.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.index_current = current
                task.index_success = success

    def add_index_failure(
        self, task_id: str, filename: str, error: str, retries: int = 0
    ) -> None:
        """Record an indexing failure.

        Args:
            task_id: The task identifier.
            filename: Name of the file that failed.
            error: Description of the failure.
            retries: Number of retry attempts made.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.index_failed.append(
                    FailedItem(filename=filename, error=error, retries=retries)
                )

    def complete_task(self, task_id: str) -> None:
        """Mark a task as completed.

        Args:
            task_id: The task identifier.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed with an error message.

        Args:
            task_id: The task identifier.
            error: Description of the failure.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED
                task.error = error

    def start_task(self, task_id: str):
        """标记任务开始运行（线程安全）

        Args:
            task_id: The task identifier.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.RUNNING

    def has_running_task(self) -> bool:
        """检查是否有运行中的任务

        Returns:
            是否有运行中的任务
        """
        with self._lock:
            return any(
                task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
                for task in self._tasks.values()
            )

    def cleanup_old_tasks(self, max_age_hours: float = 24) -> int:
        """Remove tasks older than the specified age.

        Args:
            max_age_hours: Maximum task age in hours before cleanup.

        Returns:
            Number of tasks removed.
        """
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        with self._lock:
            stale_ids = [
                tid
                for tid, task in self._tasks.items()
                if task.started_at < cutoff
            ]
            for tid in stale_ids:
                del self._tasks[tid]
                removed += 1
        return removed


# Global singleton instance
task_manager = TaskManager()
