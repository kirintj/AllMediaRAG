"""团队管理 API

提供团队成员的查看、邀请、角色修改和移除功能。
所有端点都需要 JWT 认证（通过 get_current_user）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.auth import get_current_user
from core.db.engine import get_db_session
from core.db.user_models import UserModel
from core.db.tenant_models import UserTenant, Tenant

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class InviteRequest(BaseModel):
    username: str


class UpdateMemberRequest(BaseModel):
    role: str  # owner / normal


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/team/members")
async def list_members(current_user: dict = Depends(get_current_user)):
    """列出团队成员"""
    tenant_id = current_user["tenant_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        members = (
            session.query(UserTenant)
            .filter(UserTenant.tenant_id == tenant_id)
            .all()
        )
        result = []
        for m in members:
            user = session.query(UserModel).get(m.user_id)
            if user:
                result.append({
                    "user_id": str(m.user_id),
                    "username": user.username,
                    "role": m.role,
                    "status": m.status,
                })
        return {"members": result}


@router.post("/team/invite")
async def invite_member(
    body: InviteRequest,
    current_user: dict = Depends(get_current_user),
):
    """邀请成员加入团队"""
    tenant_id = current_user["tenant_id"]
    inviter_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        # 查找目标用户
        target_user = (
            session.query(UserModel)
            .filter(UserModel.username == body.username)
            .first()
        )
        if not target_user:
            raise HTTPException(404, f"用户 {body.username} 不存在")

        # 检查是否已是成员
        existing = (
            session.query(UserTenant)
            .filter(
                UserTenant.user_id == target_user.id,
                UserTenant.tenant_id == tenant_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(409, "该用户已是团队成员")

        # 创建邀请
        user_tenant = UserTenant(
            user_id=str(target_user.id),
            tenant_id=tenant_id,
            role="normal",
            invited_by=inviter_id,
            status="pending",
        )
        session.add(user_tenant)
        session.commit()

    return {"message": f"已邀请 {body.username}"}


@router.put("/team/members/{user_id}")
async def update_member(
    user_id: str,
    body: UpdateMemberRequest,
    current_user: dict = Depends(get_current_user),
):
    """修改成员角色"""
    tenant_id = current_user["tenant_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        ut = (
            session.query(UserTenant)
            .filter(
                UserTenant.user_id == user_id,
                UserTenant.tenant_id == tenant_id,
            )
            .first()
        )
        if not ut:
            raise HTTPException(404, "成员不存在")
        ut.role = body.role
        session.commit()

    return {"message": "角色已更新"}


@router.delete("/team/members/{user_id}")
async def remove_member(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """移除成员"""
    tenant_id = current_user["tenant_id"]

    if user_id == current_user["user_id"]:
        raise HTTPException(400, "不能移除自己")

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        ut = (
            session.query(UserTenant)
            .filter(
                UserTenant.user_id == user_id,
                UserTenant.tenant_id == tenant_id,
            )
            .first()
        )
        if not ut:
            raise HTTPException(404, "成员不存在")
        session.delete(ut)
        session.commit()

    return {"message": "成员已移除"}
