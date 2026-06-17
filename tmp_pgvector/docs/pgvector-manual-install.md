# pgvector 手动安装步骤

## 第 1 步：下载 pgvector

在浏览器中打开以下链接下载预编译版本：

**推荐下载地址（选一个）：**

### 选项 A: pgvector 官方 Windows 构建
https://github.com/pgvector/pgvector/releases

找到最新版本（如 v0.8.0），下载：
- `pgvector-0.8.0-windows-x64.zip`

### 选项 B: 使用 gitee 镜像（国内加速）
https://gitee.com/mirrors/pgvector/tags

### 选项 C: 使用蓝奏云/网盘（如果有人分享）
搜索 "pgvector windows postgresql 16 下载"

---

## 第 2 步：解压文件

下载后解压 zip 文件，会看到以下文件：
```
vector--1.0.sql
vector--1.0--1.1.sql
...多个 SQL 文件
vector.control
vector.dll
```

---

## 第 3 步：复制文件到 PostgreSQL

打开文件管理器，复制文件到以下位置：

### 复制 DLL 文件：
```
源文件：vector.dll
目标：D:\Develop\PostgreSQL\16\lib\
```

### 复制 SQL 和 control 文件：
```
源文件：vector*.sql, vector.control
目标：D:\Develop\PostgreSQL\16\share\extension\
```

---

## 第 4 步：重启 PostgreSQL 服务

1. 按 `Win + R`，输入 `services.msc`，回车
2. 找到 `postgresql-x64-16` 服务
3. 右键 -> 重启

---

## 第 5 步：验证安装

打开命令提示符，运行：

```cmd
cd D:\Develop\PostgreSQL\16\bin
set PGPASSWORD=20050202
psql -U rag_user -h localhost -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
```

如果看到类似以下输出，说明安装成功：
```
 extname | extversion
---------+------------
 vector  | 0.8.0
```

---

## 完成后

运行数据库测试脚本：
```cmd
cd D:\HuaweiMoveData\Users\28966\Desktop\多模态RAG\backend
python scripts\test_db_connection.py
```
