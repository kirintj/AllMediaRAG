"""多租户数据模型

四张表：
- tenants: 租户（工作空间/组织）
- user_tenants: 用户-租户关联（团队）
- knowledgebases: 知识库
- kb_documents: 知识库文档
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _gen_uuid():
    return uuid.uuid4()


class Tenant(Base):
    """租户表（工作空间）

    设计原则：一个用户注册时自动创建一个同 ID 的租户。
    用户 ID = 租户 ID（与 RAGFlow 一致）。
    """
    __tablename__ = "tenants"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=_gen_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # 默认模型配置（FK 到 TenantLLM.id）
    llm_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embd_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rerank_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    img2txt_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asr_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    members = relationship("UserTenant", back_populates="tenant", cascade="all, delete-orphan")
    knowledgebases = relationship("Knowledgebase", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}')>"


class UserTenant(Base):
    """用户-租户关联表（团队成员）

    当用户注册时，自动创建一条 role=owner 的记录。
    被邀请加入其他租户时，创建 role=normal 的记录。
    """
    __tablename__ = "user_tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), default="normal")  # owner / normal
    invited_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active / pending
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="members")

    def __repr__(self):
        return f"<UserTenant(user={self.user_id}, tenant={self.tenant_id}, role={self.role})>"


class Knowledgebase(Base):
    """知识库表

    每个租户可创建多个知识库，每个知识库独立管理文档和配置。
    permission 控制可见性：me=仅创建者，team=同一租户所有成员。
    """
    __tablename__ = "knowledgebases"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=_gen_uuid)
    tenant_id = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    permission: Mapped[str] = mapped_column(String(16), default="me")  # me / team
    embd_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # KB 级别 Embedding
    language: Mapped[str] = mapped_column(String(10), default="zh")
    description: Mapped[str] = mapped_column(String(512), default="")
    created_by = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="knowledgebases")
    documents = relationship("KBDocument", back_populates="knowledgebase", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Knowledgebase(id={self.id}, name='{self.name}')>"


class KBDocument(Base):
    """知识库文档表

    记录每个文档的元数据和 MinIO 存储位置。
    status 跟踪摄入进度：pending -> parsing -> completed / failed。
    """
    __tablename__ = "kb_documents"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=_gen_uuid)
    kb_id = mapped_column(UUID(as_uuid=True), ForeignKey("knowledgebases.id"), nullable=False, index=True)
    tenant_id = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_key: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO 对象键
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_type: Mapped[str] = mapped_column(String(32), default="")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/parsing/completed/failed
    error: Mapped[str] = mapped_column(String(1024), default="")
    created_by = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Relationships
    knowledgebase = relationship("Knowledgebase", back_populates="documents")

    def __repr__(self):
        return f"<KBDocument(id={self.id}, name='{self.name}', status={self.status})>"
