import sys
import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

# 添加项目根目录和 backend 目录到 Python 路径
project_root = Path(__file__).parent.parent
backend_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 切换工作目录到项目根目录
os.chdir(project_root)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

from core.config import config
from core.rate_limit import limiter
from core.rag_engine import RAGEngine
from core.services import create_infra, InfraBundle

logger = logging.getLogger(__name__)
from core.services.retrieval_pipeline import RetrievalPipeline
from core.services.ingestion_service import IngestionService
from core.services.generation_service import GenerationService
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.conversations import router as conversations_router
from api.auth import router as auth_router
from api.eval import router as eval_router

# 启动时校验关键配置
if not config.MIMO_API_KEY:
    logging.warning("MIMO_API_KEY 未配置，LLM 相关功能将不可用")


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup creates infra + services, shutdown cleans up."""
    logging.info("Initializing RAG engine (models will be loaded on first use)...")

    # Create infra bundle + three services
    infra = create_infra(config)
    retrieval = RetrievalPipeline(infra)
    ingestion = IngestionService(infra)
    generation = GenerationService(infra, retrieval)

    # Build backward-compat RAGEngine facade (reuses the same infra + services)
    rag_engine = RAGEngine.from_services(config, infra, retrieval, ingestion, generation)

    # Store everything on app.state for dependency injection
    app.state.config = config
    app.state.infra = infra
    app.state.retrieval = retrieval
    app.state.ingestion = ingestion
    app.state.generation = generation
    app.state.rag_engine = rag_engine

    logging.info("RAG engine initialized. Server ready!")

    yield  # --- application runs ---

    # Shutdown: release resources
    logging.info("Shutting down: releasing RAG engine resources...")
    if hasattr(rag_engine, 'close'):
        rag_engine.close()


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(title="知识库智能问答助手 API", lifespan=lifespan)

# 速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 全局异常处理——防止未捕获异常泄露堆栈信息到客户端
# 为什么需要这个：生产环境中未处理的异常会返回 FastAPI 默认的 HTML 错误页，
# 包含完整的 Python 堆栈信息，这是安全风险（信息泄露）。
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "服务器内部错误，请稍后重试"},
    )

# CORS 配置（生产环境应通过 CORS_ORIGINS 环境变量配置）
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


# ---------------------------------------------------------------------------
# Dependency injection providers
# ---------------------------------------------------------------------------

def get_settings(request: Request):
    """Return the application config (AppSettings)."""
    return request.app.state.config


def get_infra(request: Request) -> InfraBundle:
    """Return the shared InfraBundle."""
    return request.app.state.infra


def get_retrieval(request: Request) -> RetrievalPipeline:
    """Return the retrieval pipeline service."""
    return request.app.state.retrieval


def get_ingestion(request: Request) -> IngestionService:
    """Return the ingestion service."""
    return request.app.state.ingestion


def get_generation(request: Request) -> GenerationService:
    """Return the generation service."""
    return request.app.state.generation


def get_rag_engine(request: Request) -> RAGEngine:
    """Return the backward-compat RAGEngine facade."""
    return request.app.state.rag_engine


# ---------------------------------------------------------------------------
# Register routes
# ---------------------------------------------------------------------------

# 注册路由（auth 路由无需认证）
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(eval_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "知识库智能问答助手 API"}


@app.get("/health")
async def health(request: Request):
    infra = getattr(request.app.state, "infra", None)
    if infra and infra.metrics_collector:
        return infra.metrics_collector.get_health()
    return {"status": "ok"}


if __name__ == "__main__":
    reload = os.getenv("DEV_RELOAD", "false").lower() in ("true", "1", "yes")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
