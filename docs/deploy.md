# 上线部署指南

## 前置条件

- 一台 Linux 服务器（Ubuntu 22.04+，推荐 2核4G 以上）
- 已安装 Docker 和 Docker Compose
- 知道服务器的公网 IP 地址

---

## 第一步：配置环境变量

```bash
cp .env.example .env
vi .env
```

修改以下项：

```bash
# 1. CORS 改为服务器实际 IP（替换 YOUR_SERVER_IP）
CORS_ORIGINS=http://你的服务器IP,http://localhost:5173,http://127.0.0.1:5173

# 2. 关闭注册（可选，按需）
ALLOW_REGISTRATION=false

# 3. 确认已关闭热更新
DEV_RELOAD=false
```

> JWT_SECRET_KEY 已在 .env 中生成，无需修改。

---

## 第二步：构建并启动

```bash
# 构建镜像
docker-compose build

# 启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

---

## 第三步：验证

浏览器访问：`http://你的服务器IP`

API 健康检查：`http://你的服务器IP/health`

应返回 `{"status":"ok"}`

---

## 日常运维

```bash
# 查看日志
docker-compose logs -f backend

# 更新部署
git pull && docker-compose build && docker-compose up -d

# 备份
tar -czf backup-$(date +%Y%m%d).tar.gz data/ chroma_db/ .env
```

---

## 安全提醒

- 确保服务器防火墙/安全组开放 **80 端口**
- `.env` 不要提交到 Git
- 如果后续有域名和证书，可再配置 HTTPS（见下方）

---

## 后续：配置 HTTPS（有域名后）

```bash
# 1. 域名 DNS 解析到服务器 IP
# 2. 安装 certbot 申请证书
apt install certbot
certbot certonly --standalone -d your-domain.com

# 3. 修改 nginx.conf 加入 SSL 配置
# 4. docker-compose.yml 添加 443 端口映射
# 5. 重建部署
```
