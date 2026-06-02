import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 切换工作目录到项目根目录
os.chdir(project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from api.chat import router as chat_router
from api.documents import router as documents_router
from api.conversations import router as conversations_router

app = FastAPI(title="Python 文档智能问答助手 API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Python 文档智能问答助手 API"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
