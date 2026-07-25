"""ORM 模型定义

- documents: 文件级元数据（同时替代 index_state.json）

注：chunk 文本 + 向量已迁移至 Elasticsearch，不再使用 document_chunks 表。
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, DateTime, Index, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base

def _utcnow():
    return datetime.now(timezone.utc)


def _gen_uuid():
    return uuid.uuid4()


class DocumentModel(Base):
    """文件级元数据表

    记录每个已索引文件的信息，同时替代原有的 index_state.json。
    """
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_gen_uuid
    )
    source: Mapped[str] = mapped_column(
        String(500), nullable=False, unique=True, comment="文件名"
    )
    file_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="SHA-256 文件哈希"
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="chunk 数量"
    )
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, comment="索引时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, comment="更新时间"
    )

    __table_args__ = (
        Index("idx_documents_file_hash", "file_hash"),
        {"comment": "文件级元数据表"},
    )

    def __repr__(self):
        return f"<Document(id={self.id}, source='{self.source}', chunks={self.chunk_count})>"
