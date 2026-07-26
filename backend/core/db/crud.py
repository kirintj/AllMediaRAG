"""数据库 CRUD 操作层。

封装用户与对话的增删改查，供 auth.py 和 conversations.py 调用。
所有函数接收 SQLAlchemy Session，不自行管理事务。
"""
import uuid
import secrets
import logging
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.orm import selectinload

from .user_models import UserModel, ConversationModel, MessageModel
from .engine import get_db_session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 用户 CRUD
# ---------------------------------------------------------------------------

def get_user_by_username(db, username: str) -> Optional[UserModel]:
    """按用户名查找用户，未找到返回 None"""
    stmt = select(UserModel).where(UserModel.username == username)
    return db.execute(stmt).scalar_one_or_none()


def create_user(db, username: str, password_hash: str, email: str = None) -> UserModel:
    """创建新用户并返回实例（需调用方 commit）"""
    user = UserModel(username=username, password_hash=password_hash, email=email)
    db.add(user)
    db.flush()
    return user


def get_or_create_user_by_username(db, username: str, password_hash: str = "") -> UserModel:
    """按用户名查找，不存在则创建（用于 JSON→DB 迁移时自动补录用户）"""
    user = get_user_by_username(db, username)
    if user is None:
        user = create_user(db, username, password_hash)
        db.commit()
    return user


# ---------------------------------------------------------------------------
# 对话 CRUD
# ---------------------------------------------------------------------------

def list_conversations_by_user(db, user_id) -> list[dict]:
    """列出用户所有对话的元信息（不含消息体），按 updated_at 降序"""
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.user_id == user_id)
        .order_by(ConversationModel.updated_at.desc())
    )
    rows = db.execute(stmt).scalars().all()
    return [
        {
            "id": str(c.id),
            "title": c.title,
            "mode": c.mode,
            "is_archived": c.is_archived,
            "is_favorite": c.is_favorite,
            "created_at": c.created_at.timestamp() if c.created_at else None,
            "updated_at": c.updated_at.timestamp() if c.updated_at else None,
            "message_count": len(c.messages) if c.messages else 0,
        }
        for c in rows
    ]


def get_conversation_by_id(db, conv_id: str, user_id) -> Optional[dict]:
    """获取单个对话详情（含消息），不存在或不属于该用户返回 None"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        return None
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.id == conv_uuid, ConversationModel.user_id == user_id)
        .options(selectinload(ConversationModel.messages))
    )
    conv = db.execute(stmt).scalar_one_or_none()
    if conv is None:
        return None
    return conv.to_dict(include_messages=True)


def save_conversation_db(db, conv_id: str, user_id, title: str,
                         messages: list[dict], mode: str) -> dict:
    """保存或更新对话。

    若 conv_id 对应的对话已存在，则更新消息和标题；
    否则创建新对话。返回对话字典。
    """
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        # conv_id 不是合法 UUID（旧数据可能用短 ID），生成新 UUID
        conv_uuid = uuid.uuid4()

    stmt = (
        select(ConversationModel)
        .where(ConversationModel.id == conv_uuid, ConversationModel.user_id == user_id)
        .options(selectinload(ConversationModel.messages))
    )
    conv = db.execute(stmt).scalar_one_or_none()

    if conv is not None:
        # 更新：删除旧消息，插入新消息
        for msg in conv.messages:
            db.delete(msg)
        db.flush()

        conv.title = title
        conv.mode = mode
        for i, m in enumerate(messages):
            msg_obj = MessageModel(
                conversation_id=conv.id,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                sources=m.get("sources"),
                extra_metadata=m.get("metadata") or m.get("verification"),
            )
            db.add(msg_obj)
        db.commit()
        db.refresh(conv)
        return conv.to_dict(include_messages=True)
    else:
        # 新建
        conv = ConversationModel(
            id=conv_uuid,
            user_id=user_id,
            title=title,
            mode=mode,
        )
        db.add(conv)
        db.flush()

        for m in messages:
            msg_obj = MessageModel(
                conversation_id=conv.id,
                role=m.get("role", "user"),
                content=m.get("content", ""),
                sources=m.get("sources"),
                extra_metadata=m.get("metadata") or m.get("verification"),
            )
            db.add(msg_obj)
        db.commit()
        db.refresh(conv)
        return conv.to_dict(include_messages=True)


def delete_conversation_db(db, conv_id: str, user_id) -> bool:
    """删除对话，成功返回 True，不存在返回 False"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        return False
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.id == conv_uuid, ConversationModel.user_id == user_id)
    )
    conv = db.execute(stmt).scalar_one_or_none()
    if conv is None:
        return False
    db.delete(conv)
    db.commit()
    return True


def clear_conversations_db(db, user_id) -> int:
    """清空用户所有对话，返回删除数量"""
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.user_id == user_id)
        .options(selectinload(ConversationModel.messages))
    )
    convs = db.execute(stmt).scalars().all()
    count = len(convs)
    for conv in convs:
        db.delete(conv)
    db.commit()
    return count


def update_conversation_fields(db, conv_id: str, user_id, **fields) -> Optional[dict]:
    """部分更新对话字段（title, is_favorite, is_archived 等）"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        return None
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.id == conv_uuid, ConversationModel.user_id == user_id)
        .options(selectinload(ConversationModel.messages))
    )
    conv = db.execute(stmt).scalar_one_or_none()
    if conv is None:
        return None
    for key, value in fields.items():
        if hasattr(conv, key) and key not in ('id', 'user_id', 'created_at'):
            setattr(conv, key, value)
    db.commit()
    db.refresh(conv)
    return conv.to_dict(include_messages=False)


def duplicate_conversation_db(db, conv_id: str, user_id) -> Optional[dict]:
    """复制对话及其所有消息"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        return None
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.id == conv_uuid, ConversationModel.user_id == user_id)
        .options(selectinload(ConversationModel.messages))
    )
    orig = db.execute(stmt).scalar_one_or_none()
    if orig is None:
        return None

    new_conv = ConversationModel(
        user_id=user_id,
        title=f"{orig.title} (副本)",
        mode=orig.mode,
    )
    db.add(new_conv)
    db.flush()

    for msg in orig.messages:
        new_msg = MessageModel(
            conversation_id=new_conv.id,
            role=msg.role,
            content=msg.content,
            sources=msg.sources,
            extra_metadata=msg.extra_metadata,
        )
        db.add(new_msg)
    db.commit()
    db.refresh(new_conv)
    return new_conv.to_dict(include_messages=False)


def share_conversation_db(db, conv_id: str, user_id) -> Optional[dict]:
    """为对话生成分享令牌，返回分享信息"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except ValueError:
        return None
    stmt = (
        select(ConversationModel)
        .where(ConversationModel.id == conv_uuid, ConversationModel.user_id == user_id)
    )
    conv = db.execute(stmt).scalar_one_or_none()
    if conv is None:
        return None

    if conv.shared_token is None:
        conv.shared_token = secrets.token_urlsafe(32)
        db.commit()
        db.refresh(conv)

    return {
        "id": str(conv.id),
        "shared_token": conv.shared_token,
        "share_url": f"/share/{conv.shared_token}",
    }
