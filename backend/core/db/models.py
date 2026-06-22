"""ORM 模型定义

两张表：
- documents: 文件级元数据（同时替代 index_state.json）
- document_chunks: chunk 文本 + 向量
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Integer, Text, DateTime, ForeignKey, Index, TypeDecorator
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _gen_uuid():
    return uuid.uuid4()


class Vector(TypeDecorator):
    """pgvector 向量类型（不依赖 pgvector Python 包）

    将 Python list 存储为 PostgreSQL 的 vector 类型。
    使用 ::vector 类型转换实现。
    """
    impl = Text
    cache_ok = True

    def __init__(self, dimensions=None):
        self.dimensions = dimensions
        super().__init__()

    def process_bind_param(self, value, dialect):
        """Python list -> PostgreSQL vector 字符串"""
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        """PostgreSQL vector 字符串 -> Python list"""
        if value is None:
            return None
        # pgvector 返回格式: "[0.1,0.2,...]"
        value = value.strip("[]")
        return [float(x) for x in value.split(",")]

    def column_expression(self, col):
        """在 SELECT 中将 vector 列转换为字符串"""
        return col.cast(Text)

    def bind_expression(self, bindvalue):
        """在 INSERT/UPDATE 中将字符串转换为 vector"""
        from sqlalchemy import cast, text
        return cast(bindvalue, text("vector"))


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

    # 关系
    chunks = relationship("DocumentChunkModel", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_file_hash", "file_hash"),
        {"comment": "文件级元数据表"},
    )

    def __repr__(self):
        return f"<Document(id={self.id}, source='{self.source}', chunks={self.chunk_count})>"


class DocumentChunkModel(Base):
    """文档 chunk 表（含向量）

    存储每个文档的文本分块及其对应的 embedding 向量。
    source 字段冗余存储，便于 delete_by_source 和 get_all_sources 高频操作。
    """
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=_gen_uuid
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属文件 ID"
    )
    source: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="文件名（冗余，避免 JOIN）"
    )
    section: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", comment="章节标题"
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="chunk 在文件中的序号"
    )
    text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="chunk 文本内容"
    )
    embedding = mapped_column(
        Vector(1024), nullable=False, comment="BGE-M3 1024 维向量"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, comment="创建时间"
    )

    # 关系
    document = relationship("DocumentModel", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_source", "source"),
        # HNSW 索引在 Alembic 迁移中创建（需要 CONCURRENTLY 语法）
        {"comment": "文档 chunk 表（含向量）"},
    )

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, source='{self.source}', section='{self.section}')>"
