"""用户和对话的 ORM 模型

三张表：
- users: 用户数据
- conversations: 对话记录
- messages: 对话消息
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, ForeignKey, JSON, Boolean, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _gen_uuid():
    return uuid.uuid4()


class UserModel(Base):
    """用户表"""
    __tablename__ = "users"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=_gen_uuid)
    username = mapped_column(String(50), nullable=False, unique=True, comment="用户名")
    password_hash = mapped_column(String(128), nullable=False, comment="密码哈希")
    email = mapped_column(String(100), nullable=True, comment="邮箱")
    is_active = mapped_column(Boolean, default=True, comment="是否激活")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, comment="创建时间")
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, comment="更新时间")

    # 关系
    conversations = relationship("ConversationModel", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        {"comment": "用户表"},
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
        }


class ConversationModel(Base):
    """对话表"""
    __tablename__ = "conversations"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=_gen_uuid)
    user_id = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID")
    title = mapped_column(String(200), nullable=False, default="新对话", comment="对话标题")
    mode = mapped_column(String(20), nullable=False, default="rag", comment="对话模式")
    is_archived = mapped_column(Boolean, default=False, comment="是否归档")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, comment="创建时间")
    updated_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, comment="更新时间")

    # 关系
    user = relationship("UserModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan", order_by="MessageModel.created_at")

    __table_args__ = (
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_updated_at", "updated_at"),
        {"comment": "对话表"},
    )

    def to_dict(self, include_messages=True):
        result = {
            "id": str(self.id),
            "title": self.title,
            "mode": self.mode,
            "is_archived": self.is_archived,
            "created_at": self.created_at.timestamp() if self.created_at else None,
            "updated_at": self.updated_at.timestamp() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0,
        }
        if include_messages:
            result["messages"] = [msg.to_dict() for msg in (self.messages or [])]
        return result


class MessageModel(Base):
    """消息表"""
    __tablename__ = "messages"

    id = mapped_column(UUID(as_uuid=True), primary_key=True, default=_gen_uuid)
    conversation_id = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, comment="所属对话 ID")
    role = mapped_column(String(20), nullable=False, comment="角色: user/assistant/system")
    content = mapped_column(Text, nullable=False, comment="消息内容")
    sources = mapped_column(JSON, nullable=True, comment="引用来源")
    extra_metadata = mapped_column("metadata", JSON, nullable=True, comment="额外元数据")
    created_at = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, comment="创建时间")

    # 关系
    conversation = relationship("ConversationModel", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "created_at"),
        {"comment": "消息表"},
    )

    def to_dict(self):
        return {
            "id": str(self.id),
            "role": self.role,
            "content": self.content,
            "sources": self.sources,
            "metadata": self.extra_metadata,
            "created_at": self.created_at.timestamp() if self.created_at else None,
        }
