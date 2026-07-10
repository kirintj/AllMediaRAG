"""FastAPI 依赖注入提供者。

各路由通过 `from api.deps import ...` 使用，避免在每个路由文件中
重复定义 _get_infra / _get_retrieval 等局部函数。
"""
from fastapi import Request

from core.config import AppSettings
from core.services import InfraBundle
from core.services.retrieval_pipeline import RetrievalPipeline
from core.services.ingestion_service import IngestionService
from core.services.generation_service import GenerationService
from core.rag_engine import RAGEngine


def get_settings(request: Request) -> AppSettings:
    """应用配置"""
    return request.app.state.config


def get_infra(request: Request) -> InfraBundle:
    """共享基础设施包（包含所有组件实例）"""
    return request.app.state.infra


def get_retrieval(request: Request) -> RetrievalPipeline:
    """检索管线服务"""
    return request.app.state.retrieval


def get_ingestion(request: Request) -> IngestionService:
    """文档摄取服务"""
    return request.app.state.ingestion


def get_generation(request: Request) -> GenerationService:
    """生成服务"""
    return request.app.state.generation


def get_rag_engine(request: Request) -> RAGEngine:
    """RAGEngine 门面（向后兼容）"""
    return request.app.state.rag_engine


def get_db(request: Request):
    """数据库会话（上下文管理器）"""
    from core.db.engine import get_db_session
    return get_db_session()
