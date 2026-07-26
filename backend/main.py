import sys
import os
import uuid
import asyncio
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
from core.observability.logger import JSONFormatter

logger = logging.getLogger(__name__)
from core.task_queue import TaskQueue
from api.chat import router as chat_router
from api.documents import router as documents_router
from api.conversations import router as conversations_router
from api.auth import router as auth_router
from api.eval import router as eval_router
from api.models import router as models_router
from api.tag_kb import router as tag_kb_router
from api.settings import router as settings_router
from api.graph import router as graph_router
from api.knowledgebases import router as kb_router
from api.team import router as team_router

# 启动时校验关键配置
if not config.MIMO_API_KEY:
    logging.warning("MIMO_API_KEY 未配置，LLM 相关功能将不可用")


# ---------------------------------------------------------------------------
# 结构化日志初始化
# 为什么在应用级而非模块级配置日志：统一所有模块的日志格式，
# 避免各模块自行配置导致格式不一致。
# ---------------------------------------------------------------------------
def _setup_logging():
    """激活 JSONFormatter 作为根日志格式化器

    为什么用 JSON 格式：生产环境日志需要被 ELK/Loki 等工具解析，
    JSON 格式比纯文本更易解析和查询。
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        root.addHandler(handler)
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

_setup_logging()
logger = logging.getLogger(__name__)

# 全局活跃请求计数器（用于优雅关闭时等待请求排空）
_active_requests: int = 0
_active_requests_lock = __import__("threading").Lock()

# 请求超时配置（秒）
# 为什么 30 秒：RAG 查询通常 2-5 秒完成，30 秒是合理的上限，
# 超过说明系统异常（如 LLM API 卡死），应主动断开避免连接泄漏。
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup creates RAG engine, shutdown cleans up.

    为什么用 RAGEngine 而非手动组装：RAGEngine.__init__ 内部已完成
    create_infra + 三个 Service 的初始化，main.py 只需提取引用即可。
    """
    logging.info("Initializing RAG engine...")

    rag_engine = RAGEngine(config)

    task_queue = TaskQueue(config.REDIS_URL, task_ttl=config.TASK_TTL_HOURS * 3600)

    # 存储到 app.state 供依赖注入（api/deps.py）
    app.state.config = config
    app.state.infra = rag_engine._infra
    app.state.retrieval = rag_engine.retrieval
    app.state.ingestion = rag_engine.ingestion
    app.state.generation = rag_engine.generation
    app.state.rag_engine = rag_engine
    app.state.task_queue = task_queue

    logger.info("RAG engine initialized. Server ready!")

    # 创建多租户相关表（如果不存在）
    from core.db.tenant_models import Tenant, UserTenant, Knowledgebase, KBDocument
    from core.db.base import Base as DBBase
    from core.db.engine import get_engine
    db_engine = get_engine()
    if db_engine is not None:
        DBBase.metadata.create_all(db_engine, tables=[
            Tenant.__table__,
            UserTenant.__table__,
            Knowledgebase.__table__,
            KBDocument.__table__,
        ])
        logger.info("Tenant tables ensured in database")

    yield  # --- application runs ---

    # 优雅关闭：等待活跃请求排空
    logger.info("Shutdown: waiting for active requests to drain...")
    import time
    deadline = time.time() + 15  # 最多等 15 秒
    while time.time() < deadline:
        with _active_requests_lock:
            if _active_requests == 0:
                break
        await asyncio.sleep(0.5)

    with _active_requests_lock:
        remaining = _active_requests
    if remaining > 0:
        logger.warning("Shutdown: %d requests still active after timeout", remaining)
    else:
        logger.info("Shutdown: all requests drained")

    # 释放 RAG 引擎资源（含 embedding 模型、GPU 缓存、线程池）
    logger.info("Shutdown: releasing resources...")
    rag_engine.close()
    infra = rag_engine._infra
    if infra.executor:
        infra.executor.shutdown(wait=False)
    logger.info("Shutdown complete")


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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """关联 ID 中间件 — 为每个请求注入唯一追踪 ID

    为什么需要关联 ID：生产环境多请求并发，日志交错时无法区分
    哪条日志属于哪个请求。X-Request-ID 将整个请求链路串联起来。
    客户端也可以传入自己的请求 ID（如前端生成的 UUID）。
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    # 绑定到 request.state，下游可通过 request.state.request_id 获取
    request.state.request_id = request_id

    # 为什么用 logging.LoggerAdapter：自动在所有日志中附加 request_id，
    # 无需每个 logger.info 手动传 extra。
    request_logger = logging.LoggerAdapter(logger, {"request_id": request_id})

    with _active_requests_lock:
        global _active_requests
        _active_requests += 1

    try:
        response = await asyncio.wait_for(
            call_next(request),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except asyncio.TimeoutError:
        request_logger.warning(
            "Request timeout after %ds: %s %s",
            REQUEST_TIMEOUT_SECONDS, request.method, request.url.path,
        )
        return JSONResponse(
            status_code=504,
            content={"error": "请求超时，请稍后重试", "request_id": request_id},
        )
    finally:
        with _active_requests_lock:
            _active_requests -= 1


# ---------------------------------------------------------------------------
# Register routes
# （依赖注入提供者已统一定义在 api/deps.py）
# ---------------------------------------------------------------------------

# 注册路由（auth 路由无需认证）
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(eval_router, prefix="/api")
app.include_router(models_router, prefix="/api")
app.include_router(tag_kb_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(graph_router, prefix="/api")
app.include_router(kb_router, prefix="/api")
app.include_router(team_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "知识库智能问答助手 API"}


@app.get("/health")
async def health(request: Request):
    """健康检查端点 — 检查所有关键依赖的状态

    为什么检查依赖而非只返回 "ok"：负载均衡器（如 K8s liveness probe）
    需要知道服务是否真正可用，而非只是进程活着。
    一个进程活着但向量库连不上，应返回 unhealthy。
    """
    infra = getattr(request.app.state, "infra", None)
    checks = {}
    overall_healthy = True

    if infra:
        # 向量库连通性
        try:
            infra.vector_store.get_document_count()
            checks["vector_store"] = "ok"
        except Exception as e:
            checks["vector_store"] = f"error: {e}"
            overall_healthy = False

        # Embedding 模型加载
        try:
            infra.embedding_service.encode(["healthcheck"])
            checks["embedding"] = "ok"
        except Exception as e:
            checks["embedding"] = f"error: {e}"
            overall_healthy = False

        # 指标数据
        if hasattr(infra, "metrics_collector") and infra.metrics_collector:
            checks["metrics"] = infra.metrics_collector.get_health()

    return {
        "status": "ok" if overall_healthy else "degraded",
        "checks": checks,
    }


if __name__ == "__main__":
    reload = os.getenv("DEV_RELOAD", "false").lower() in ("true", "1", "yes")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
