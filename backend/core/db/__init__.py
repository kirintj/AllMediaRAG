"""数据库基础设施包。

- Base: ORM 声明式基类
- DocumentModel / DocumentChunkModel: 文档与 chunk 元数据（向量存储）
- UserModel / ConversationModel / MessageModel: 用户与对话数据（业务存储）
"""
from .base import Base
from .models import DocumentModel, DocumentChunkModel
from .user_models import UserModel, ConversationModel, MessageModel
from .engine import get_db_session, get_db, engine, SessionLocal

__all__ = [
    "Base",
    "DocumentModel",
    "DocumentChunkModel",
    "UserModel",
    "ConversationModel",
    "MessageModel",
    "get_db_session",
    "get_db",
    "engine",
    "SessionLocal",
]
