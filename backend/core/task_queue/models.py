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
    """Redis Stream message body"""
    task_id: str
    batch_id: str
    file_path: str
    source: str
    user_id: str
    tenant_id: str = "default"  # NEW: 租户隔离
    kb_id: str = ""             # NEW: 知识库 ID
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
            "tenant_id": self.tenant_id,
            "kb_id": self.kb_id,
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
            tenant_id=d.get("tenant_id", "default"),
            kb_id=d.get("kb_id", ""),
            parser_type=d.get("parser_type", "auto"),
            enrichment=d.get("enrichment", "{}"),
            retry=int(d.get("retry", 0)),
        )


@dataclass
class TaskState:
    """Redis Hash task state"""
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
