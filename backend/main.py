import sys
import os
import logging
from pathlib import Path

# 添加项目根目录和 backend 目录到 Python 路径
project_root = Path(__file__).parent.parent
backend_dir = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

# 切换工作目录到项目根目录
os.chdir(project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

from core.advanced_config import init_advanced_config
from core.config import config
from core.rate_limit import limiter
from core.rag_engine import RAGEngine
from api.chat import router as chat_router, set_engine as set_chat_engine
from api.documents import router as documents_router, set_engine as set_docs_engine
from api.conversations import router as conversations_router
from api.auth import router as auth_router

# 显式加载 .env 配置
init_advanced_config()

# 启动时校验关键配置
if not config.MIMO_API_KEY:
    logging.warning("MIMO_API_KEY 未配置，LLM 相关功能将不可用")

# 创建共享的 RAG 引擎实例
rag_engine = RAGEngine(config)
set_chat_engine(rag_engine)
set_docs_engine(rag_engine, config)

app = FastAPI(title="知识库智能问答助手 API")

# 速率限制
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS 配置（生产环境应通过 CORS_ORIGINS 环境变量配置）
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# 注册路由（auth 路由无需认证）
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "知识库智能问答助手 API"}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    reload = os.getenv("DEV_RELOAD", "true").lower() in ("true", "1", "yes")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload)
