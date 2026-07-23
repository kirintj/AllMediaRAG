"""模型管理 API"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.auth import get_current_user
from core.db.engine import get_db
from core.models.tenant_llm_service import TenantLLMService

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AddModelRequest(BaseModel):
    llm_factory: str
    model_type: str  # chat/embedding/rerank/cv/ocr/tts/asr
    llm_name: str
    api_key: str
    api_base: str = ""


class SetDefaultRequest(BaseModel):
    model_type: str
    model_id: int


# ---------------------------------------------------------------------------
# Dependency: database-backed service (gracefully handles missing DB)
# ---------------------------------------------------------------------------


def _get_service(db=Depends(get_db)):
    if db is None:
        raise HTTPException(status_code=503, detail="数据库不可用")
    return TenantLLMService(db)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/models/types")
async def list_model_types():
    """列出支持的模型类型（无需认证）"""
    return {
        "types": [
            {"value": "chat", "label": "对话模型"},
            {"value": "embedding", "label": "向量模型"},
            {"value": "rerank", "label": "重排序模型"},
            {"value": "cv", "label": "视觉模型"},
            {"value": "ocr", "label": "OCR 模型"},
            {"value": "tts", "label": "语音合成"},
            {"value": "asr", "label": "语音识别"},
        ]
    }


@router.get("/models/factories")
async def list_factories(
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """列出可用的模型厂商"""
    return {"factories": service.list_factories()}


@router.get("/models")
async def list_models(
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """列出租户已配置的模型"""
    tenant_id = current_user.get("username", "default")
    return {"models": service.list_models(tenant_id)}


@router.post("/models")
async def add_model(
    body: AddModelRequest,
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """新增模型配置"""
    tenant_id = current_user.get("username", "default")
    model = service.add_model(
        tenant_id,
        body.llm_factory,
        body.model_type,
        body.llm_name,
        body.api_key,
        body.api_base,
    )
    return {"message": "模型添加成功", "model": model}


@router.delete("/models/{model_id}")
async def delete_model(
    model_id: int,
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """删除模型配置"""
    tenant_id = current_user.get("username", "default")
    service.delete_model(tenant_id, model_id)
    return {"message": "模型已删除"}


@router.post("/models/default")
async def set_default_model(
    body: SetDefaultRequest,
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """设置默认模型"""
    tenant_id = current_user.get("username", "default")
    service.set_default(tenant_id, body.model_type, body.model_id)
    return {"message": f"默认 {body.model_type} 模型已设置"}
