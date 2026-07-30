"""JWT 认证核心模块

存储策略：优先使用 PostgreSQL（UserModel），数据库不可用时降级到 JSON 文件。
JWT 签发/验证逻辑不受存储层影响。
"""
import os
import json
import time
import logging
from typing import Optional

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


# ---------------------------------------------------------------------------
# JSON 文件降级存储（数据库不可用时的后备方案）
# ---------------------------------------------------------------------------
_users_file: Optional[str] = None


def _get_users_file() -> str:
    global _users_file
    if _users_file is None:
        from core.config import config
        data_parent = os.path.dirname(config.DATA_DIR)
        _users_file = os.path.join(data_parent, "users.json")
    return _users_file


def _load_users() -> dict:
    path = _get_users_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_users(users: dict):
    path = _get_users_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 密码与 Token 工具
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    """签发 JWT access token"""
    from datetime import datetime, timedelta, timezone
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# 用户注册 / 验证（DB 优先，JSON 降级）
# ---------------------------------------------------------------------------

def register_user(username: str, password: str) -> dict:
    """注册新用户。数据库可用时写入 DB，否则降级到 JSON 文件。"""
    if not ALLOW_REGISTRATION:
        raise ValueError("当前不允许注册新用户")
    if len(username) < 2 or len(username) > 32:
        raise ValueError("用户名长度需在 2-32 个字符之间")
    if len(password) < 6:
        raise ValueError("密码长度至少 6 个字符")

    hashed = hash_password(password)

    # 尝试数据库
    from core.db.engine import get_db_session
    from core.db.crud import get_user_by_username, create_user
    with get_db_session() as db:
        if db is not None:
            existing = get_user_by_username(db, username)
            if existing:
                raise ValueError("用户名已存在")
            user = create_user(db, username, hashed)
            db.commit()
            logger.info("新用户注册(DB): %s", username)

            # Create a tenant + owner membership for the new user
            from core.db.tenant_models import Tenant, UserTenant
            tenant = Tenant(id=user.id, name=f"{username}'s workspace")
            db.add(tenant)
            user_tenant = UserTenant(
                user_id=user.id,
                tenant_id=tenant.id,
                role="owner",
                status="active",
            )
            db.add(user_tenant)
            db.commit()

            return {"username": user.username, "user_id": str(user.id), "created_at": user.created_at.timestamp()}

    # 降级到 JSON
    users = _load_users()
    if username in users:
        raise ValueError("用户名已存在")
    user_data = {"username": username, "password_hash": hashed, "created_at": time.time()}
    users[username] = user_data
    _save_users(users)
    logger.info("新用户注册(JSON): %s", username)
    return {"username": username, "created_at": user_data["created_at"]}


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """验证用户名密码，成功返回用户信息（不含密码），失败返回 None。"""
    # 尝试数据库
    from core.db.engine import get_db_session
    from core.db.crud import get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user is None or not verify_password(password, user.password_hash):
                return None
            return {"username": user.username, "created_at": user.created_at.timestamp()}

    # 降级到 JSON
    users = _load_users()
    user = users.get(username)
    if not user or not verify_password(password, user["password_hash"]):
        return None
    return {"username": user["username"], "created_at": user["created_at"]}


def _user_exists(username: str) -> bool:
    """检查用户是否存在（供 get_current_user 验证 token 时使用）"""
    from core.db.engine import get_db_session
    from core.db.crud import get_user_by_username
    with get_db_session() as db:
        if db is not None:
            return get_user_by_username(db, username) is not None
    return username in _load_users()


def _resolve_tenant(username: str) -> dict | None:
    """Resolve a user's primary tenant.

    Priority:
    1. First active owner-level membership (user's own workspace)
    2. First active normal-level membership (joined team)
    3. Auto-create a tenant for pre-existing users (backward compat)

    Only ``status="active"`` memberships are considered; ``pending``
    invitations are **not** resolved to prevent premature access.

    Returns a dict with ``user_id``, ``tenant_id``, and ``role`` on success,
    or ``None`` when the database is unavailable or the user is not found.
    """
    from core.db.engine import get_db_session
    from core.db.crud import get_user_by_username
    from core.db.tenant_models import Tenant, UserTenant

    with get_db_session() as session:
        if session is None:
            return None

        user = get_user_by_username(session, username)
        if user is None:
            return None

        # 1. Look for an active owner-level membership
        user_tenant = (
            session.query(UserTenant)
            .filter(
                UserTenant.user_id == user.id,
                UserTenant.role == "owner",
                UserTenant.status == "active",
            )
            .first()
        )

        # 2. Fallback: first active membership of any role
        if user_tenant is None:
            user_tenant = (
                session.query(UserTenant)
                .filter(UserTenant.user_id == user.id, UserTenant.status == "active")
                .first()
            )

        # 3. Backward compatibility: auto-create a tenant for pre-existing users
        if user_tenant is None:
            tenant = Tenant(id=user.id, name=f"{username}'s workspace")
            session.add(tenant)
            user_tenant = UserTenant(
                user_id=user.id,
                tenant_id=tenant.id,
                role="owner",
                status="active",
            )
            session.add(user_tenant)
            session.commit()
            session.refresh(tenant)
            session.refresh(user_tenant)

        tenant_id = str(user_tenant.tenant_id)
        role = user_tenant.role

        # 必须在 session 关闭前读取 user.id，否则 ORM 对象脱离 session 会报 DetachedInstanceError
        user_id = str(user.id)

    return {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """FastAPI 依赖：从 Authorization header 解析当前用户

    返回值包含 ``user_id``, ``username``, ``tenant_id``, ``role``。
    数据库不可用时 ``user_id`` 和 ``tenant_id`` 降级为 "default"。
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

    if not _user_exists(username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve tenant context
    tenant_info = _resolve_tenant(username)
    if tenant_info is None:
        # Database unavailable -- degrade gracefully
        return {
            "user_id": username,
            "username": username,
            "tenant_id": "default",
            "role": "owner",
        }

    return {
        "user_id": tenant_info["user_id"],
        "username": username,
        "tenant_id": tenant_info["tenant_id"],
        "role": tenant_info["role"],
    }
