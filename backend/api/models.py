"""模型管理 API"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.auth import get_current_user
from core.db.engine import get_db
from core.models.tenant_llm_service import TenantLLMService
from core.models import _infer_factory

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AddModelRequest(BaseModel):
    llm_factory: str | None = None  # 自动推断，留空即可
    model_type: str  # chat/embedding/rerank/cv/ocr/tts/asr
    llm_name: str
    api_key: str
    api_base: str = ""


class UpdateModelRequest(BaseModel):
    llm_factory: str | None = None
    model_type: str | None = None
    llm_name: str | None = None
    api_key: str | None = None
    api_base: str | None = None
    max_tokens: int | None = None


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
    """新增模型配置（llm_factory 留空则自动推断）"""
    tenant_id = current_user.get("username", "default")
    llm_factory = body.llm_factory or _infer_factory(body.api_base or "", body.model_type)
    model = service.add_model(
        tenant_id,
        llm_factory,
        body.model_type,
        body.llm_name,
        body.api_key,
        body.api_base,
    )
    return {"message": "模型添加成功", "model": model}


@router.get("/models/defaults")
async def get_default_models(
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """获取当前租户所有类型的默认模型 ID"""
    tenant_id = current_user.get("username", "default")
    return {"defaults": service.get_defaults(tenant_id)}


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


@router.get("/models/{model_id}")
async def get_model(
    model_id: int,
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """获取单条模型配置详情"""
    tenant_id = current_user.get("username", "default")
    model = service.get_model(tenant_id, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"model": model}


@router.put("/models/{model_id}")
async def update_model(
    model_id: int,
    body: UpdateModelRequest,
    current_user: dict = Depends(get_current_user),
    service: TenantLLMService = Depends(_get_service),
):
    """更新模型配置"""
    tenant_id = current_user.get("username", "default")
    model = service.update_model(
        tenant_id,
        model_id,
        llm_factory=body.llm_factory,
        model_type=body.model_type,
        llm_name=body.llm_name,
        api_key=body.api_key,
        api_base=body.api_base,
        max_tokens=body.max_tokens,
    )
    if not model:
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"message": "模型配置已更新", "model": model}
