"""PostgreSQL 认证模块"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from core.db.engine import get_db_session
from core.db.user_models import UserModel

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """哈希密码"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_username(username: str) -> UserModel | None:
    """根据用户名获取用户"""
    with get_db_session() as session:
        return session.query(UserModel).filter_by(username=username).first()


def register_user(username: str, password: str) -> UserModel:
    """注册新用户"""
    with get_db_session() as session:
        existing = session.query(UserModel).filter_by(username=username).first()
        if existing:
            raise ValueError("用户名已存在")

        user = UserModel(
            username=username,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


def authenticate_user(username: str, password: str) -> UserModel | None:
    """验证用户凭据"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
