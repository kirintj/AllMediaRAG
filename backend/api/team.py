"""团队管理 API

提供团队的创建、成员的查看、邀请、接受/拒绝邀请、角色修改和移除功能。
邀请流程：发送邀请 → 被邀请方收到通知 → 确认接受/拒绝 → 权限生效。
所有端点都需要 JWT 认证（通过 get_current_user）。
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from core.auth import get_current_user
from core.db.engine import get_db_session
from core.db.user_models import UserModel
from core.db.tenant_models import UserTenant, Tenant

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CreateTeamRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="团队名称")


class InviteRequest(BaseModel):
    username: str


class UpdateMemberRequest(BaseModel):
    role: str  # owner / normal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _verify_owner(session, user_id: str, tenant_id: str) -> UserTenant:
    """验证当前用户是指定租户的 active owner，返回成员关系记录。

    Raises HTTPException(403) 如果不是 owner 或不是 active 成员。
    """
    ut = (
        session.query(UserTenant)
        .filter(
            UserTenant.user_id == user_id,
            UserTenant.tenant_id == tenant_id,
            UserTenant.status == "active",
            UserTenant.role == "owner",
        )
        .first()
    )
    if ut is None:
        raise HTTPException(403, "仅该团队的管理员可以执行此操作")
    return ut


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/team/create")
async def create_team(
    body: CreateTeamRequest,
    current_user: dict = Depends(get_current_user),
):
    """创建新团队（租户），创建者自动成为 owner"""
    user_id = current_user["user_id"]
    username = current_user["username"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        # 创建租户
        tenant = Tenant(name=body.name)
        session.add(tenant)
        session.flush()  # 确保 tenant.id 已生成

        # 创建者自动成为 owner
        user_tenant = UserTenant(
            user_id=user_id,
            tenant_id=tenant.id,
            role="owner",
            status="active",
        )
        session.add(user_tenant)
        session.commit()

        tenant_id = str(tenant.id)
        tenant_name = tenant.name

    logger.info("用户 %s 创建了团队: %s (%s)", username, tenant_name, tenant_id)
    return {
        "message": f"团队 '{tenant_name}' 创建成功",
        "team_id": tenant_id,
        "team_name": tenant_name,
    }


@router.get("/team/list")
async def list_teams(current_user: dict = Depends(get_current_user)):
    """列出当前用户所属的所有团队"""
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        memberships = (
            session.query(UserTenant)
            .filter(UserTenant.user_id == user_id, UserTenant.status == "active")
            .all()
        )

        teams = []
        for m in memberships:
            tenant = session.query(Tenant).get(m.tenant_id)
            if tenant:
                # 统计团队成员数
                member_count = (
                    session.query(UserTenant)
                    .filter(
                        UserTenant.tenant_id == tenant.id,
                        UserTenant.status == "active",
                    )
                    .count()
                )
                teams.append({
                    "tenant_id": str(tenant.id),
                    "name": tenant.name,
                    "role": m.role,
                    "member_count": member_count,
                    "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
                })

        return {"teams": teams}


@router.get("/team/members")
async def list_members(
    tenant_id: str = Query(..., description="团队 ID"),
    current_user: dict = Depends(get_current_user),
):
    """列出指定团队的成员（含 pending 和 active）。

    当前用户必须是该团队的 active 成员才能查看。
    """
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        # 验证当前用户是该团队的 active 成员
        membership = (
            session.query(UserTenant)
            .filter(
                UserTenant.user_id == user_id,
                UserTenant.tenant_id == tenant_id,
                UserTenant.status == "active",
            )
            .first()
        )
        if membership is None:
            raise HTTPException(403, "您不是该团队的成员")

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
                    "invited_by": m.invited_by,
                })
        return {"members": result}


@router.post("/team/invite")
async def invite_member(
    body: InviteRequest,
    tenant_id: str = Query(..., description="目标团队 ID"),
    current_user: dict = Depends(get_current_user),
):
    """邀请成员加入指定团队（创建 pending 状态的邀请，需被邀请方确认后才生效）"""
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        # 验证当前用户是该团队的 active owner
        _verify_owner(session, user_id, tenant_id)

        # 查找目标用户
        target_user = (
            session.query(UserModel)
            .filter(UserModel.username == body.username)
            .first()
        )
        if not target_user:
            raise HTTPException(404, f"用户 {body.username} 不存在")

        # 不能邀请自己
        if str(target_user.id) == user_id:
            raise HTTPException(400, "不能邀请自己")

        # 检查是否已有记录（pending 或 active）
        existing = (
            session.query(UserTenant)
            .filter(
                UserTenant.user_id == target_user.id,
                UserTenant.tenant_id == tenant_id,
            )
            .first()
        )
        if existing:
            if existing.status == "pending":
                raise HTTPException(409, "已向该用户发送过邀请，请等待对方确认")
            raise HTTPException(409, "该用户已是团队成员")

        # 获取租户名称（用于通知）
        tenant = session.query(Tenant).get(tenant_id)

        # 创建邀请（status=pending，被邀请方未确认前不享有任何权限）
        user_tenant = UserTenant(
            user_id=str(target_user.id),
            tenant_id=tenant_id,
            role="normal",
            invited_by=user_id,
            status="pending",
        )
        session.add(user_tenant)
        session.commit()

    logger.info(
        "用户 %s 邀请 %s 加入团队 %s",
        current_user["username"], body.username, tenant.name if tenant else tenant_id,
    )
    return {
        "message": f"已向 {body.username} 发送邀请，等待对方确认",
        "status": "pending",
    }


@router.get("/team/invitations")
async def list_invitations(current_user: dict = Depends(get_current_user)):
    """列出当前用户收到的所有待处理邀请"""
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        invitations = (
            session.query(UserTenant)
            .filter(UserTenant.user_id == user_id, UserTenant.status == "pending")
            .all()
        )

        result = []
        for inv in invitations:
            tenant = session.query(Tenant).get(inv.tenant_id)
            # 查找邀请人用户名
            inviter_name = None
            if inv.invited_by:
                inviter = session.query(UserModel).get(inv.invited_by)
                if inviter:
                    inviter_name = inviter.username

            result.append({
                "id": inv.id,
                "tenant_id": str(inv.tenant_id),
                "tenant_name": tenant.name if tenant else "未知团队",
                "invited_by": inviter_name,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            })

        return {"invitations": result}


@router.post("/team/invitations/{invitation_id}/accept")
async def accept_invitation(
    invitation_id: int,
    current_user: dict = Depends(get_current_user),
):
    """接受邀请，将 status 从 pending 改为 active，此时才真正获得权限"""
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        inv = (
            session.query(UserTenant)
            .filter(
                UserTenant.id == invitation_id,
                UserTenant.user_id == user_id,
                UserTenant.status == "pending",
            )
            .first()
        )
        if not inv:
            raise HTTPException(404, "邀请不存在或已处理")

        inv.status = "active"
        session.commit()

        tenant = session.query(Tenant).get(inv.tenant_id)
        tenant_name = tenant.name if tenant else str(inv.tenant_id)

    logger.info("用户 %s 接受了加入团队 %s 的邀请", current_user["username"], tenant_name)
    return {"message": f"已加入团队「{tenant_name}」"}


@router.post("/team/invitations/{invitation_id}/reject")
async def reject_invitation(
    invitation_id: int,
    current_user: dict = Depends(get_current_user),
):
    """拒绝邀请，删除 pending 记录"""
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        inv = (
            session.query(UserTenant)
            .filter(
                UserTenant.id == invitation_id,
                UserTenant.user_id == user_id,
                UserTenant.status == "pending",
            )
            .first()
        )
        if not inv:
            raise HTTPException(404, "邀请不存在或已处理")

        session.delete(inv)
        session.commit()

    return {"message": "已拒绝邀请"}


@router.put("/team/members/{user_id}")
async def update_member(
    user_id: str,
    body: UpdateMemberRequest,
    tenant_id: str = Query(..., description="目标团队 ID"),
    current_user: dict = Depends(get_current_user),
):
    """修改指定团队中某成员的角色（仅该团队 owner 可操作）"""
    current_uid = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        # 验证当前用户是该团队的 active owner
        _verify_owner(session, current_uid, tenant_id)

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
    tenant_id: str = Query(..., description="目标团队 ID"),
    current_user: dict = Depends(get_current_user),
):
    """移除指定团队中的成员（仅该团队 owner 可操作）"""
    current_uid = current_user["user_id"]

    if user_id == current_uid:
        raise HTTPException(400, "不能移除自己")

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "数据库不可用")

        # 验证当前用户是该团队的 active owner
        _verify_owner(session, current_uid, tenant_id)

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
