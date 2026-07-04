"""系统配置 API"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.db import get_db
from core.auth import get_current_user
from core.settings_service import get_all_settings, update_settings, seed_defaults

logger = logging.getLogger(__name__)
router = APIRouter()


class UpdateSettingsRequest(BaseModel):
    group: str
    settings: dict[str, str]


@router.get("/settings")
def read_settings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """读取所有系统配置（按 group 分组）"""
    try:
        groups = get_all_settings(db)
        return {"groups": groups}
    except Exception as e:
        logger.error("读取配置失败: %s", e)
        raise HTTPException(status_code=500, detail="读取配置失败")


@router.put("/settings")
def write_settings(
    req: UpdateSettingsRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """更新某个 group 的配置（热更新生效）"""
    try:
        update_settings(db, req.group, req.settings)
        return {"ok": True, "message": f"{req.group} 配置已保存"}
    except Exception as e:
        logger.error("保存配置失败: %s", e)
        raise HTTPException(status_code=500, detail=f"保存配置失败: {e}")


@router.post("/settings/seed")
def seed_settings(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """手动触发 seed"""
    try:
        seed_defaults(db)
        return {"ok": True, "message": "配置 seed 完成"}
    except Exception as e:
        logger.error("Seed 失败: %s", e)
        raise HTTPException(status_code=500, detail=f"Seed 失败: {e}")
