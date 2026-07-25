"""数据库基础设施包。

- Base: ORM 声明式基类
- DocumentModel: 文档元数据
- UserModel / ConversationModel / MessageModel: 用户与对话数据（业务存储）
- LLMFactories / TenantLLM / TenantDefaultModel: LLM 模型配置（模型抽象层）
- Tenant / UserTenant / Knowledgebase / KBDocument: 多租户与知识库
"""
from .base import Base
from .models import DocumentModel
from .user_models import UserModel, ConversationModel, MessageModel
from .llm_models import LLMFactories, TenantLLM, TenantDefaultModel
from .tenant_models import Tenant, UserTenant, Knowledgebase, KBDocument
from .engine import get_db_session, get_db, engine, SessionLocal

__all__ = [
    "Base",
    "DocumentModel",
    "UserModel",
    "ConversationModel",
    "MessageModel",
    "LLMFactories",
    "TenantLLM",
    "TenantDefaultModel",
    "Tenant",
    "UserTenant",
    "Knowledgebase",
    "KBDocument",
    "get_db_session",
    "get_db",
    "engine",
    "SessionLocal",
]
