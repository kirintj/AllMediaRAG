# ============================================
# 前端 Dockerfile — 多阶段构建
# Stage 1: Node 构建
# Stage 2: Nginx 静态服务 + 反向代理
# ============================================

# --- 构建阶段 ---
FROM node:20-alpine AS builder

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --legacy-peer-deps
COPY frontend/ .
RUN npm run build

# --- 运行阶段 ---
FROM nginx:alpine

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/nginx.conf

# 复制构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
