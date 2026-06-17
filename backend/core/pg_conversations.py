"""PostgreSQL 对话管理模块"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from core.db.engine import get_db_session
from core.db.user_models import UserModel, ConversationModel, MessageModel

logger = logging.getLogger(__name__)


def get_user_conversations(username: str) -> List[dict]:
    """获取用户的所有对话"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return []

        conversations = (
            session.query(ConversationModel)
            .filter_by(user_id=user.id)
            .order_by(ConversationModel.updated_at.desc())
            .all()
        )

        return [conv.to_dict(include_messages=False) for conv in conversations]


def get_conversation(conversation_id: str, username: str) -> Optional[dict]:
    """获取单个对话详情"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return None

        conversation = (
            session.query(ConversationModel)
            .filter_by(id=conversation_id, user_id=user.id)
            .first()
        )

        if not conversation:
            return None

        return conversation.to_dict(include_messages=True)


def create_conversation(username: str, title: str = "新对话", mode: str = "rag") -> dict:
    """创建新对话"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            raise ValueError("用户不存在")

        conversation = ConversationModel(
            user_id=user.id,
            title=title,
            mode=mode,
        )
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation.to_dict(include_messages=False)


def update_conversation(conversation_id: str, username: str, **kwargs) -> Optional[dict]:
    """更新对话"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return None

        conversation = (
            session.query(ConversationModel)
            .filter_by(id=conversation_id, user_id=user.id)
            .first()
        )

        if not conversation:
            return None

        for key, value in kwargs.items():
            if hasattr(conversation, key):
                setattr(conversation, key, value)

        conversation.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(conversation)
        return conversation.to_dict(include_messages=False)


def delete_conversation(conversation_id: str, username: str) -> bool:
    """删除对话"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return False

        conversation = (
            session.query(ConversationModel)
            .filter_by(id=conversation_id, user_id=user.id)
            .first()
        )

        if not conversation:
            return False

        session.delete(conversation)
        session.commit()
        return True


def add_message(conversation_id: str, username: str, role: str, content: str,
                sources: list = None, metadata: dict = None) -> Optional[dict]:
    """添加消息到对话"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return None

        conversation = (
            session.query(ConversationModel)
            .filter_by(id=conversation_id, user_id=user.id)
            .first()
        )

        if not conversation:
            return None

        message = MessageModel(
            conversation_id=conversation.id,
            role=role,
            content=content,
            sources=sources,
            extra_metadata=metadata,
        )
        session.add(message)

        # 更新对话的更新时间
        conversation.updated_at = datetime.now(timezone.utc)

        # 如果是第一条用户消息，更新对话标题
        if role == "user" and not conversation.messages:
            conversation.title = content[:50] + ("..." if len(content) > 50 else "")

        session.commit()
        session.refresh(message)
        return message.to_dict()


def get_conversation_messages(conversation_id: str, username: str) -> List[dict]:
    """获取对话的所有消息"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return []

        conversation = (
            session.query(ConversationModel)
            .filter_by(id=conversation_id, user_id=user.id)
            .first()
        )

        if not conversation:
            return []

        messages = (
            session.query(MessageModel)
            .filter_by(conversation_id=conversation.id)
            .order_by(MessageModel.created_at)
            .all()
        )

        return [msg.to_dict() for msg in messages]


def clear_user_conversations(username: str) -> int:
    """清空用户的所有对话"""
    with get_db_session() as session:
        user = session.query(UserModel).filter_by(username=username).first()
        if not user:
            return 0

        count = (
            session.query(ConversationModel)
            .filter_by(user_id=user.id)
            .delete()
        )

        session.commit()
        return count
