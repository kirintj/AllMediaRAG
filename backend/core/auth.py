"""JWT 认证核心模块

提供用户管理、密码哈希、Token 签发与验证功能。
用户数据存储在 JSON 文件中（与对话存储模式一致）。
"""
import os
import json
import time
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 提取器
security = HTTPBearer(auto_error=False)

# 配置（从环境变量读取，带默认值）
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-to-a-random-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() in ("true", "1", "yes")

# 用户数据文件路径
_users_file: Optional[str] = None


def _get_users_file() -> str:
    """获取用户数据文件路径"""
    global _users_file
    if _users_file is None:
        from core.config import config
        data_parent = os.path.dirname(config.DATA_DIR)
        _users_file = os.path.join(data_parent, "users.json")
    return _users_file


def _load_users() -> dict:
    """加载用户数据"""
    path = _get_users_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_users(users: dict):
    """保存用户数据"""
    path = _get_users_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """创建 JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def register_user(username: str, password: str) -> dict:
    """注册新用户

    Returns:
        用户信息（不含密码）

    Raises:
        ValueError: 用户名已存在或不允许注册
    """
    if not ALLOW_REGISTRATION:
        raise ValueError("当前不允许注册新用户")

    users = _load_users()

    if username in users:
        raise ValueError("用户名已存在")

    if len(username) < 2 or len(username) > 32:
        raise ValueError("用户名长度需在 2-32 个字符之间")

    if len(password) < 6:
        raise ValueError("密码长度至少 6 个字符")

    user_data = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": time.time(),
    }
    users[username] = user_data
    _save_users(users)

    logger.info("新用户注册: %s", username)
    return {"username": username, "created_at": user_data["created_at"]}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """验证用户名密码

    Returns:
        用户信息（不含密码），验证失败返回 None
    """
    users = _load_users()
    user = users.get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return {"username": user["username"], "created_at": user["created_at"]}


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI 依赖：从 Authorization header 解析当前用户

    所有需要认证的端点通过 Depends(get_current_user) 使用。
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证用户是否仍存在
    users = _load_users()
    if username not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"username": username}
