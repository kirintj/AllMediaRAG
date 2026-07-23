"""LLM 模型配置表

三张表：
- llm_factories: 模型厂商元数据（预置数据）
- tenant_llm: 租户配置的模型实例
- tenant_default_models: 每租户每类型的默认模型
"""

from datetime import datetime, timezone

from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class LLMFactories(Base):
    """模型厂商元数据表"""

    __tablename__ = "llm_factories"

    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    logo: Mapped[str] = mapped_column(String(512), default="")
    tags: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(1), default="1")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    def __repr__(self):
        return f"<LLMFactory(name='{self.name}', tags='{self.tags}')>"


class TenantLLM(Base):
    """租户模型配置表"""

    __tablename__ = "tenant_llm"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        String(64), default="default", index=True
    )
    llm_factory: Mapped[str] = mapped_column(String(100), nullable=False)
    model_type: Mapped[str] = mapped_column(String(32), nullable=False)
    llm_name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(String(512), default="")
    api_base: Mapped[str] = mapped_column(String(512), default="")
    max_tokens: Mapped[int] = mapped_column(Integer, default=8192)
    used_tokens: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(1), default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self):
        return (
            f"<TenantLLM(tenant='{self.tenant_id}', "
            f"factory='{self.llm_factory}', model='{self.llm_name}')>"
        )


class TenantDefaultModel(Base):
    """租户默认模型表"""

    __tablename__ = "tenant_default_models"

    tenant_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default="default"
    )
    llm_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    embd_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rerank_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    img2txt_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    asr_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self):
        return f"<TenantDefaultModel(tenant='{self.tenant_id}')>"
