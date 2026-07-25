# 多租户体系设计文档

## 概述

为 ALLRAG 实现完整的多租户体系：User/Tenant/UserTenant 数据模型、每租户多个知识库、MinIO/S3 文件存储隔离、ES 索引按租户隔离、团队协作（邀请/角色）。参照 RAGFlow 的多租户架构对齐。

## 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 团队模式 | User = Tenant + UserTenant | 与 RAGFlow 一致 |
| 知识库 | 每租户多个 KB | 独立管理文档和配置 |
| ES 索引 | `allrag_{tenant_id}` 每租户独立 | 强隔离，与 RAGFlow 一致 |
| 文件存储 | MinIO/S3 | 按租户/KB 隔离 |
| API 认证 | JWT → User → UserTenant → tenant_id | 与 RAGFlow 一致 |
| 数据迁移 | 现有数据归到 default 租户 | 平滑迁移 |
| 权限 | KB 级别 me/team | 与 RAGFlow 一致 |

## 数据模型

### User 表（改造现有 users 表）

```python
class User(Base):
    __tablename__ = "users"
    id: str              # UUID, primary key
    username: str        # unique
    email: str           # unique, nullable
    password_hash: str
    is_active: bool
    is_superuser: bool
    language: str        # "zh" / "en"
    created_at: datetime
```

### Tenant 表（新增）

```python
class Tenant(Base):
    __tablename__ = "tenants"
    id: str              # = user.id（创建时同 ID）
    name: str
    llm_id: int | None   # 默认 Chat 模型 ID（FK TenantLLM）
    embd_id: int | None  # 默认 Embedding
    rerank_id: int | None
    img2txt_id: int | None
    ocr_id: int | None
    tts_id: int | None
    asr_id: int | None
    created_at: datetime
```

### UserTenant 表（新增）

```python
class UserTenant(Base):
    __tablename__ = "user_tenants"
    id: int              # auto-increment
    user_id: str         # FK users.id
    tenant_id: str       # FK tenants.id
    role: str            # "owner" / "normal"
    invited_by: str | None
    status: str          # "active" / "pending"
    created_at: datetime
```

### Knowledgebase 表（新增）

```python
class Knowledgebase(Base):
    __tablename__ = "knowledgebases"
    id: str              # UUID
    tenant_id: str       # FK tenants.id
    name: str
    permission: str      # "me" / "team"
    embd_id: int | None  # KB 级别 Embedding 配置
    language: str
    created_by: str
    created_at: datetime
```

### Document 表（新增）

```python
class Document(Base):
    __tablename__ = "documents"
    id: str              # UUID
    kb_id: str           # FK knowledgebases.id
    tenant_id: str       # 冗余，便于查询
    name: str            # 文件名
    file_key: str        # MinIO/S3 对象键
    file_size: int
    file_type: str
    chunk_count: int
    status: str          # "pending" / "parsing" / "completed" / "failed"
    created_by: str
    created_at: datetime
```

## 租户隔离

### ES 索引隔离

```python
def index_name(tenant_id: str) -> str:
    return f"allrag_{tenant_id}"
```

- 每租户独立 ES 索引
- 同租户不同知识库通过 `kb_id` 字段过滤
- 检索时只查当前租户索引

### 文件存储隔离

```
MinIO bucket: allrag-files
key 格式:     {tenant_id}/{kb_id}/{document_id}/{filename}
```

### API 认证链

```
JWT → 解析 user_id → 查 User 表 → 查 UserTenant 表 → 返回 tenant_id + role
```

`get_current_user` 改造后返回：

```python
{"user_id": "...", "tenant_id": "...", "role": "owner", "username": "..."}
```

## API 端点

### 知识库管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/knowledgebases` | GET | 列出当前租户的知识库 |
| `/api/knowledgebases` | POST | 创建知识库 |
| `/api/knowledgebases/{kb_id}` | GET | 获取知识库详情 |
| `/api/knowledgebases/{kb_id}` | PUT | 更新知识库配置 |
| `/api/knowledgebases/{kb_id}` | DELETE | 删除知识库（级联） |
| `/api/knowledgebases/{kb_id}/documents` | GET | 列出文档 |
| `/api/knowledgebases/{kb_id}/upload` | POST | 上传文档 |
| `/api/knowledgebases/{kb_id}/documents/{doc_id}` | DELETE | 删除文档 |

### 团队管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/team/members` | GET | 列出成员 |
| `/api/team/invite` | POST | 邀请成员 |
| `/api/team/members/{user_id}` | PUT | 修改角色 |
| `/api/team/members/{user_id}` | DELETE | 移除成员 |

## 文档上传流程

```
POST /api/knowledgebases/{kb_id}/upload
    → 校验权限（用户是否属于该租户，KB 是否可见）
    → 上传文件到 MinIO: {tenant_id}/{kb_id}/{doc_id}/{filename}
    → 创建 Document 记录（status=pending）
    → 入队 TaskQueue: {task_id, tenant_id, kb_id, doc_id, file_key}
    → Worker 消费: MinIO 下载 → 解析 → 分块 → embedding → 写入 ES allrag_{tenant_id}
```

## 检索流程改造

```
用户提问 → 解析 tenant_id
    → RetrievalPipeline.retrieval(query, tenant_id, kb_ids?)
    → ES 检索索引 allrag_{tenant_id}（可选 kb_id 过滤）
    → 返回结果
```

## 数据迁移

现有数据迁移到默认租户：
1. 创建 default tenant（id = "default"）
2. ES 索引 `allrag_default` 保持不变（已是当前索引名）
3. 本地文件迁移到 MinIO: `default/default/{doc_id}/{filename}`
4. 创建 default UserTenant 记录

## 变更清单

### 新增

- `backend/db/tenant_models.py` — Tenant/UserTenant/Knowledgebase/Document 表
- `backend/api/knowledgebases.py` — 知识库 API
- `backend/api/team.py` — 团队管理 API
- `backend/core/storage/minio_storage.py` — MinIO 文件存储抽象
- `backend/core/auth.py` — 改造认证，返回 tenant_id

### 修改

- `backend/core/auth.py` — get_current_user 返回 tenant_id
- `backend/api/documents.py` — 上传流程走知识库 → MinIO → TaskQueue
- `backend/core/services/ingestion_service.py` — 入参增加 tenant_id/kb_id
- `backend/core/services/retrieval_pipeline.py` — 检索时传入 tenant_id
- `backend/core/providers/elasticsearch_store.py` — 索引名动态化
- `backend/core/task_queue/models.py` — 消息增加 tenant_id/kb_id
- `backend/worker.py` — 消费时从 MinIO 下载文件
- `backend/core/config.py` — 新增 MINIO_* 配置
- `docker-compose.yml` — 新增 MinIO 服务
- 前端新增知识库管理页面、团队管理页面

## 配置

```python
# config.py 新增
MINIO_ENDPOINT: str = "localhost:9000"
MINIO_ACCESS_KEY: str = "minioadmin"
MINIO_SECRET_KEY: str = "minioadmin"
MINIO_BUCKET: str = "allrag-files"
MINIO_SECURE: bool = False
```

## Docker Compose 新增

```yaml
  minio:
    image: minio/minio:latest
    container_name: multimodal-rag-minio
    command: server /data --console-address ":9001"
    ports:
      - "${MINIO_PORT:-9000}:9000"
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY:-minioadmin}
    volumes:
      - multimodal_rag_minio_data:/data
    healthcheck:
      test: ["CMD", "mc", "ready", "local"]
      interval: 10s
      timeout: 5s
      retries: 5
```
