# 异步任务队列设计文档

## 概述

用 Redis Stream 替换现有的 `threading.Thread` + 内存 `TaskManager` 方案，实现生产级异步任务队列。每个文件解析任务独立入队，支持两级优先级、自动重试、分阶段进度跟踪，Worker 作为独立进程消费队列。

## 目标

- 单文件上传不再阻塞 HTTP 响应，立即返回 task_id
- 批量上传统一走队列，不再区分同步/异步两条路径
- 任务状态持久化（Redis Hash），进程崩溃不丢失
- 两级优先级：单文件上传（high）优先于批量/同步任务（low）
- Worker 独立进程，可水平扩展
- 摄入接口预留 parser_type / enrichment 字段，为后续增强做铺垫

## 架构

```
                        ┌──────────────┐
                        │   Redis      │
                        │              │
                        │ stream:task:  │
                        │   high ──────┼──→ Worker (独立进程)
                        │   low  ──────┼──→   ↓
                        │              │   IngestionService
                        │ hash:task:*  │   (现有逻辑不变)
                        │ hash:batch:* │
                        └──────┬───────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
               POST /upload   轮询 GET    POST /batch
               (入队)        /task/{id}   (批量入队)
                    │          │          │
                    └──────────┴──────────┘
                        FastAPI Server
```

三个组件：

- **TaskQueue**（`core/task_queue/`）：Redis Stream + Hash 封装，入队/出队/状态管理
- **Worker**（`worker.py`）：独立进程，`XREADGROUP` 消费任务，调用 `IngestionService.ingest_document()`
- **API 层**（`api/documents.py`）：上传端点改为入队，新增任务/批次状态查询端点

核心原则：`IngestionService.ingest_document()` 零改动，Worker 直接调用它。

## Redis 数据模型

### Stream（消息队列）

```
stream:task:high    ← 单文件上传（用户正在等待）
stream:task:low     ← 批量上传、本地同步、未来后台任务
```

消息结构：

```json
{
  "task_id":      "task_a1b2c3d4",
  "batch_id":     "batch_x1y2",
  "file_path":    "/data/xxx.pdf",
  "source":       "xxx.pdf",
  "user_id":      "user_001",
  "parser_type":  "auto",
  "enrichment":   "{}",
  "retry":        "0",
  "created_at":   "1721712000"
}
```

`parser_type` 和 `enrichment` 现在 Worker 不处理，消息中已携带，后续增强时 Worker 读取并分发。

### Hash（任务状态）

```
hash:task:{task_id}
  status:       pending | processing | completed | failed
  source:       "xxx.pdf"
  batch_id:     "batch_x1y2"
  user_id:      "user_001"
  phase:        queued | parsing | chunking | embedding | indexing | done
  progress:     "3/5"            # 预留：当前阶段内子进度，现阶段不使用
  chunks:       "42"
  error:        ""
  started_at:   "1721712001"
  completed_at: "1721712005"
  retry:        "0"
  TTL: 24h
```

### Hash（批次状态）

```
hash:batch:{batch_id}
  status:     running | completed | failed
  total:      "10"
  completed:  "7"
  failed:     "1"
  user_id:    "user_001"
  created_at: "1721712000"
  TTL: 24h
```

设计要点：

- `phase` 分 5 个阶段（parsing → chunking → embedding → indexing → done），Worker 每阶段切换时 HSET 更新，前端展示精细进度
- `batch_id` 用于查询一次批量上传的聚合状态：`get_batch_state` 先读 `hash:batch:{id}` 获取 total/user_id，再 `SCAN hash:task:*` 过滤 `batch_id` 字段匹配的任务 hash 统计 completed/failed 数
- 单文件上传时 `batch_id = task_id`，逻辑统一

## TaskQueue 模块 API

### 数据模型（`backend/core/task_queue/models.py`）

```python
@dataclass
class TaskMessage:
    task_id: str
    batch_id: str
    file_path: str
    source: str
    user_id: str
    parser_type: str = "auto"
    enrichment: str = "{}"
    retry: int = 0

@dataclass
class TaskState:
    task_id: str
    status: str           # pending|processing|completed|failed
    phase: str            # queued|parsing|chunking|embedding|indexing|done
    source: str
    batch_id: str
    chunks: int = 0
    error: str = ""
    retry: int = 0
```

### 核心封装（`backend/core/task_queue/queue.py`）

```python
class TaskQueue:
    def __init__(self, redis_url: str): ...

    # Producer（API 调用）
    def enqueue(self, msg: TaskMessage, priority: str = "low") -> str
    def enqueue_batch(self, messages: list[TaskMessage]) -> tuple[str, list[str]]

    # Consumer（Worker 调用）
    def dequeue(self, group: str, consumer: str, count: int = 1) -> list
    def ack(self, stream: str, msg_id: str)

    # 状态管理
    def update_state(self, task_id: str, **fields)
    def get_state(self, task_id: str) -> TaskState | None
    def get_batch_state(self, batch_id: str) -> dict

    # 重试
    def requeue(self, msg: TaskMessage)

    # 清理
    def cleanup(self, max_age_hours: int = 24)
```

`dequeue` 优先级逻辑：先非阻塞读 `stream:task:high`（timeout=100ms），无消息再阻塞读 `stream:task:low`（timeout=2000ms）。

## Worker 进程

新建 `backend/worker.py`，独立进程启动。

### 主循环

```python
def main():
    queue = TaskQueue(config.REDIS_URL)
    queue.ensure_consumer_group("ingestion-workers")

    infra = create_infra(config)
    ingestion = IngestionService(infra)

    with ThreadPoolExecutor(max_workers=config.WORKER_CONCURRENCY) as pool:
        while not shutdown:
            messages = queue.dequeue(group, consumer, count=1)
            for msg in messages:
                pool.submit(process_message, queue, ingestion, msg)
```

### 单条消息处理流程

```
process_message(queue, ingestion, msg):
    task_id = msg.task_id

    1. update_state(phase=parsing)
       # 未来根据 msg.parser_type 分发到不同解析器

    2. update_state(phase=chunking)

    3. update_state(phase=embedding)

    4. update_state(phase=indexing)

    5. chunks = ingestion.ingest_document(file_path)  ← 现有逻辑不变
       update_state(status=completed, phase=done, chunks=chunks)
       ack(stream, msg_id)

    异常时：
       if retry < MAX_RETRIES:
           msg.retry += 1
           requeue(msg)  # 放回 high 优先级
       else:
           update_state(status=failed, error=str(e))
           ack(stream, msg_id)  # 死信，ack 掉避免阻塞
```

### Docker Compose

```yaml
worker:
  build: .
  command: python worker.py
  depends_on:
    redis:
      condition: service_healthy
  volumes:
    - ./data:/app/data
  environment:
    - REDIS_URL=redis://redis:6379/0
    - WORKER_CONCURRENCY=4
  restart: unless-stopped
```

## API 层改造

改动集中于 `backend/api/documents.py`。

### 单文件上传 `POST /upload`

改造前：读文件 → `_save_and_ingest()` → 等处理完 → 返回结果
改造后：读文件 → 保存磁盘 → `queue.enqueue()` → 立即返回 task_id

```python
@router.post("/upload")
async def upload_document(...):
    safe_name = os.path.basename(file.filename)
    _validate_upload_file(file, safe_name)
    content = await file.read()

    # 1. 保存到磁盘
    os.makedirs(config.DATA_DIR, exist_ok=True)
    file_path = os.path.join(config.DATA_DIR, safe_name)
    ingestion.delete_by_source(safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    # 2. 入队
    task_id = queue.enqueue(TaskMessage(...), priority="high")

    return {"message": "上传成功，正在处理", "task_id": task_id}
```

### 批量上传 `POST /upload/batch`

改造前：< SYNC_THRESHOLD 同步处理，> threshold 启动 threading.Thread
改造后：全部入队，统一返回 batch_id + task_ids

```python
@router.post("/upload/batch")
async def batch_upload(...):
    # 1. 校验 + 保存所有文件到磁盘
    saved_files = []
    for file in files:
        ...
        saved_files.append((file_path, safe_name))

    # 2. 批量入队
    batch_id, task_ids = queue.enqueue_batch([...])

    return {
        "message": f"已提交 {len(saved_files)} 个文件",
        "batch_id": batch_id,
        "task_ids": task_ids,
    }
```

### 进度查询端点

```python
# 替换现有 batch_status
@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str, ...):
    state = queue.get_state(task_id)
    if not state:
        raise HTTPException(404, "任务不存在")
    return state

# 新增
@router.get("/batches/{batch_id}")
async def get_batch_status(batch_id: str, ...):
    state = queue.get_batch_state(batch_id)
    if not state:
        raise HTTPException(404, "批次不存在")
    return state
```

`/documents/load` 和 `/documents/sync` 同步改为入队方式。

### 删除的代码

| 删除项 | 位置 | 原因 |
|--------|------|------|
| `_save_and_ingest()` | documents.py | 摄入逻辑移入 Worker |
| `_process_single_file()` | documents.py | 同上 |
| `_process_batch_sync()` | documents.py | 统一走队列 |
| `_process_batch_async()` | documents.py | 用 Redis Stream 替代 |
| `_LoadState` 类 | documents.py | 用 Redis Hash 替代 |
| `task_manager.py` 全文件 | core/task_manager.py | 用 TaskQueue 替代 |

### 依赖注入（`api/deps.py`）

```python
def get_task_queue(request: Request) -> TaskQueue:
    return request.app.state.task_queue
```

### Lifespan 改造（`main.py`）

```python
async def lifespan(app: FastAPI):
    infra = create_infra(config)
    task_queue = TaskQueue(config.REDIS_URL)
    ...
    app.state.task_queue = task_queue
    yield
```

## 配置与依赖

### config.py 新增

```python
REDIS_URL: str = "redis://localhost:6379/0"
WORKER_CONCURRENCY: int = 4
WORKER_MAX_RETRIES: int = 3
WORKER_RETRY_DELAYS: list[int] = [5, 15, 30]
TASK_TTL_HOURS: int = 24
```

### requirements.txt 新增

```
redis>=5.0.0
```

### docker-compose.yml 改造

backend 加 `depends_on: redis`，新增 `worker` 服务。

## 变更文件清单

### 新增（4 个）

- `backend/core/task_queue/__init__.py`
- `backend/core/task_queue/models.py`
- `backend/core/task_queue/queue.py`
- `backend/worker.py`

### 修改（5 个）

- `backend/api/documents.py` — 上传端点改为入队，新增查询端点，删除同步处理代码
- `backend/main.py` — lifespan 初始化 TaskQueue
- `backend/api/deps.py` — 新增 get_task_queue
- `backend/core/config.py` — 新增 Redis/Worker 配置
- `docker-compose.yml` — 新增 worker 服务

### 配置文件（2 个）

- `requirements.txt` — 新增 redis>=5.0.0
- `.env.example` — 新增 REDIS_URL、WORKER_* 示例

### 删除（1 个）

- `backend/core/task_manager.py` — 功能完全被 TaskQueue 替代

### 零改动

- `backend/core/services/ingestion_service.py` — Worker 直接调用其 ingest_document()
- `backend/core/services/retrieval_pipeline.py` — 检索层不受影响
- `backend/core/services/generation_service.py` — 生成层不受影响

## 预留扩展点

- `TaskMessage.parser_type`：后续 Worker 根据此字段分发到不同解析器
- `TaskMessage.enrichment`：后续传递 LLM 增强选项（关键词提取、RAPTOR 等）
- `TaskState.phase`：5 阶段进度上报，后续可在每阶段内增加子进度
- `TaskQueue` 接口独立于 Redis 实现，理论上可替换为 Kafka/ RabbitMQ（不推荐，但接口预留）
