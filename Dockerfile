# ============================================
# 后端 Dockerfile — 多阶段构建
# ============================================

FROM python:3.11-slim AS base

# 系统依赖（编译 bcrypt 等 C 扩展）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先复制依赖清单，利用 Docker 层缓存
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 设置工作目录和 Python 路径
ENV PYTHONPATH=/app:/app/backend
WORKDIR /app

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
