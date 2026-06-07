"""认证 API 端点

提供用户注册、登录、获取当前用户信息的接口。
"""
import logging
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field

from core.auth import (
    register_user,
    authenticate_user,
    create_access_token,
    get_current_user,
    ALLOW_REGISTRATION,
)
from core.rate_limit import limiter, RATE_LIMIT_LOGIN, RATE_LIMIT_REGISTER

logger = logging.getLogger(__name__)

router = APIRouter()


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32, pattern=r"^[a-zA-Z0-9_一-鿿]+$")
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/auth/register", response_model=TokenResponse)
@limiter.limit(RATE_LIMIT_REGISTER)
async def register(request: Request, body: RegisterRequest):
    """用户注册

    注册成功后自动登录，返回 JWT Token。
    """
    if not ALLOW_REGISTRATION:
        raise HTTPException(status_code=403, detail="当前不允许注册新用户")

    try:
        user = register_user(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 注册成功自动登录
    token = create_access_token({"sub": user["username"]})
    logger.info("用户注册并登录: %s", body.username)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit(RATE_LIMIT_LOGIN)
async def login(request: Request, body: LoginRequest):
    """用户登录

    验证用户名密码，返回 JWT Token。
    """
    user = authenticate_user(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    token = create_access_token({"sub": user["username"]})
    logger.info("用户登录: %s", body.username)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息（用于验证 Token 有效性）"""
    return {
        "username": current_user["username"],
        "message": "认证有效",
    }
