"""数据库引擎配置

- engine / SessionLocal 延迟到首次使用时才创建；
- 若 DATABASE_URL 未配置或连接失败，engine 会返回 None。
"""
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from core.config import config


_engine = None
_SessionLocal = None


def _build_engine():
    """尝试创建 SQLAlchemy engine，失败则返回 None"""
    url = (config.DATABASE_URL or "").strip()
    if not url:
        return None
    try:
        engine = create_engine(
            url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        # 触发一次连接检查；失败时不 crash 整个服务启动
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            "数据库引擎初始化失败（未配置 DATABASE_URL 或服务未启动）: %s", e
        )
        return None


def get_engine():
    """返回可用的 SQLAlchemy engine（延迟创建）；不可用时返回 None"""
    global _engine
    if _engine is not None:
        return _engine
    _engine = _build_engine()
    return _engine


def get_session_factory():
    """返回 sessionmaker 工厂；engine 不可用时返回 None"""
    global _SessionLocal
    engine = get_engine()
    if engine is None:
        return None
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


# 向后兼容：其他模块 `from core.db.engine import engine, SessionLocal` 时
# 若当前进程从未创建引擎，返回 None 让调用方自行处理
engine = None
SessionLocal = None


@contextmanager
def get_db_session() -> Session | None:
    """获取数据库会话（上下文管理器）；数据库不可用时返回 None"""
    factory = get_session_factory()
    if factory is None:
        yield None
        return
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_db():
    """FastAPI 依赖注入用的数据库会话；数据库不可用时 yield None"""
    factory = get_session_factory()
    if factory is None:
        yield None
        return
    db = factory()
    try:
        yield db
    finally:
        db.close()
