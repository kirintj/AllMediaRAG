"""TenantLLMService -- 租户模型配置数据库 CRUD"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from core.db.llm_models import LLMFactories, TenantLLM, TenantDefaultModel

logger = logging.getLogger(__name__)

# Model type -> TenantDefaultModel column name
_TYPE_TO_FIELD = {
    "chat": "llm_id",
    "embedding": "embd_id",
    "rerank": "rerank_id",
    "cv": "img2txt_id",
    "ocr": "ocr_id",
    "tts": "tts_id",
    "asr": "asr_id",
}


class TenantLLMService:
    """CRUD service for tenant-level LLM model configuration."""

    def __init__(self, db: Session):
        self._db = db

    def get_default_model(self, tenant_id: str, model_type: str) -> dict | None:
        """获取租户某类型的默认模型配置"""
        default = self._db.get(TenantDefaultModel, tenant_id)
        if not default:
            return None

        field = _TYPE_TO_FIELD.get(model_type)
        if not field:
            return None

        model_id = getattr(default, field, None)
        if not model_id:
            return None

        llm = self._db.get(TenantLLM, model_id)
        if not llm or llm.status != "1":
            return None

        return {
            "llm_factory": llm.llm_factory,
            "llm_name": llm.llm_name,
            "api_key": llm.api_key,
            "api_base": llm.api_base,
            "max_tokens": llm.max_tokens,
        }

    def list_models(self, tenant_id: str) -> list[dict]:
        """列出租户所有已启用的模型配置"""
        rows = (
            self._db.query(TenantLLM)
            .filter(TenantLLM.tenant_id == tenant_id, TenantLLM.status == "1")
            .all()
        )
        return [self._row_to_dict(r) for r in rows]

    def add_model(
        self,
        tenant_id: str,
        llm_factory: str,
        model_type: str,
        llm_name: str,
        api_key: str,
        api_base: str = "",
    ) -> dict:
        """新增一条租户模型配置"""
        model = TenantLLM(
            tenant_id=tenant_id,
            llm_factory=llm_factory,
            model_type=model_type,
            llm_name=llm_name,
            api_key=api_key,
            api_base=api_base,
        )
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._row_to_dict(model)

    def delete_model(self, tenant_id: str, model_id: int):
        """删除租户的某条模型配置"""
        model = (
            self._db.query(TenantLLM)
            .filter(TenantLLM.tenant_id == tenant_id, TenantLLM.id == model_id)
            .first()
        )
        if model:
            self._db.delete(model)
            self._db.commit()

    def set_default(self, tenant_id: str, model_type: str, model_id: int):
        """设置租户某类型的默认模型"""
        default = self._db.get(TenantDefaultModel, tenant_id)
        if not default:
            default = TenantDefaultModel(tenant_id=tenant_id)
            self._db.add(default)

        field = _TYPE_TO_FIELD.get(model_type)
        if field:
            setattr(default, field, model_id)
            self._db.commit()

    def list_factories(self) -> list[dict]:
        """列出所有已启用的模型厂商"""
        rows = (
            self._db.query(LLMFactories)
            .filter(LLMFactories.status == "1")
            .all()
        )
        return [
            {
                "name": r.name,
                "tags": r.tags,
                "description": r.description,
            }
            for r in rows
        ]

    def increment_tokens(self, model_id: int, tokens: int):
        """累加模型已用 token 数"""
        self._db.query(TenantLLM).filter(TenantLLM.id == model_id).update(
            {"used_tokens": TenantLLM.used_tokens + tokens}
        )
        self._db.commit()

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "id": row.id,
            "llm_factory": row.llm_factory,
            "model_type": row.model_type,
            "llm_name": row.llm_name,
            "api_base": row.api_base,
            "used_tokens": row.used_tokens,
            "status": row.status,
        }
