# PostgreSQL 数据库设置指南

## 快速开始

### 方法 1: 使用批处理脚本（推荐）

1. 双击运行 `backend/scripts/setup_postgres.bat`
2. 输入 postgres 用户的密码（如果没有设置密码直接按回车）
3. 等待脚本自动完成所有设置

### 方法 2: 手动执行

#### 1. 创建数据库和用户

打开命令提示符或 PowerShell，执行以下命令：

```bash
# 切换到 PostgreSQL 安装目录的 bin 目录
cd "D:\Develop\PostgreSQL\16\bin"

# 创建用户
psql -U postgres -h localhost -c "CREATE USER rag_user WITH PASSWORD 'rag_password';"

# 创建数据库
psql -U postgres -h localhost -c "CREATE DATABASE rag_db OWNER rag_user;"

# 授予权限
psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE rag_db TO rag_user;"
```

#### 2. 启用 pgvector 扩展

```bash
psql -U rag_user -h localhost -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### 3. 验证安装

```bash
# 检查 pgvector 版本
psql -U rag_user -h localhost -d rag_db -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

## 配置应用

数据库创建完成后，`.env` 文件应该包含以下配置：

```env
DATABASE_URL=postgresql+asyncpg://rag_user:rag_password@localhost:5432/rag_db
DATABASE_URL_SYNC=postgresql://rag_user:rag_password@localhost:5432/rag_db
USE_POSTGRES=true
```

## 初始化数据库表

数据库创建后，需要运行 Alembic 迁移来创建表结构：

```bash
cd backend
python -m alembic upgrade head
```

## 迁移现有数据（可选）

如果已有 ChromaDB 数据需要迁移到 PostgreSQL：

```bash
cd backend
python scripts/migrate_chroma_to_pg.py
```

## 常见问题

### 1. pgvector 扩展未安装

**错误信息**: `ERROR: extension "vector" is not available`

**解决方案**:
- Windows: 使用 Stack Builder 安装 pgvector，或从 https://github.com/pgvector/pgvector/releases 下载预编译版本
- Linux (Ubuntu): `sudo apt install postgresql-16-pgvector`
- macOS: `brew install pgvector`

### 2. 连接被拒绝

**错误信息**: `connection refused`

**解决方案**:
1. 检查 PostgreSQL 服务是否启动
2. 检查 `pg_hba.conf` 文件，确保允许本地连接
3. 检查防火墙设置

### 3. 密码认证失败

**错误信息**: `password authentication failed`

**解决方案**:
1. 确认密码正确
2. 检查 `pg_hba.conf` 中的认证方式
3. 尝试重置密码: `ALTER USER rag_user WITH PASSWORD 'new_password';`

## 数据库信息

- **数据库名**: rag_db
- **用户名**: rag_user
- **密码**: rag_password
- **主机**: localhost
- **端口**: 5432
- **连接字符串**: `postgresql://rag_user:rag_password@localhost:5432/rag_db`

## 备份与恢复

### 备份数据库

```bash
pg_dump -U rag_user -h localhost -d rag_db > backup.sql
```

### 恢复数据库

```bash
psql -U rag_user -h localhost -d rag_db < backup.sql
```

## 性能调优

编辑 PostgreSQL 配置文件 `postgresql.conf`：

```ini
# 共享缓冲区（建议为系统内存的 25%）
shared_buffers = 256MB

# 工作内存（用于排序和哈希操作）
work_mem = 16MB

# 维护工作内存
maintenance_work_mem = 64MB

# 有效缓存大小（系统可用内存的 75%）
effective_cache_size = 1GB

# WAL 缓冲区
wal_buffers = 16MB

# 向量索引参数（针对 pgvector 优化）
max_parallel_workers_per_gather = 4
```

修改后需要重启 PostgreSQL 服务。
