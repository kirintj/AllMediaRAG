# 批量上传功能设计文档

> 日期：2026-06-16
> 状态：设计完成
> 作者：AI Assistant

## 1. 概述

### 1.1 背景

当前系统只支持单文件上传，每次上传后立即进行向量化处理。当用户需要一次性上传大量文档（如 500 个）时，会遇到以下问题：

- 速率限制（30次/分钟）
- 前端串行上传，效率低
- 无法查看整体进度
- 长时间等待，用户体验差

### 1.2 目标

实现完整的批量上传功能，支持：

- 一次性选择并上传多个文件（最多 100 个）
- 分阶段显示进度（上传阶段 + 索引阶段）
- 失败自动重试（最多 3 次）
- 混合处理模式（小批量同步，大批量异步）

### 1.3 范围

**包含**：
- 批量上传 API
- 任务状态管理
- 前端进度展示组件
- 错误处理和重试机制

**不包含**：
- WebSocket 实时通信
- 任务队列（Celery/Redis）
- 文件去重（依赖现有逻辑）

## 2. 需求规格

### 2.1 功能需求

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-01 | 支持一次性选择最多 100 个文件上传 | P0 |
| FR-02 | 文件数 < 20 时同步处理，直接返回结果 | P0 |
| FR-03 | 文件数 >= 20 时异步处理，返回任务 ID | P0 |
| FR-04 | 分阶段显示进度（上传 + 索引） | P0 |
| FR-05 | 索引失败自动重试 3 次 | P1 |
| FR-06 | 显示失败文件列表及错误原因 | P1 |
| FR-07 | 估算剩余时间 | P2 |

### 2.2 非功能需求

| ID | 需求 | 规格 |
|----|------|------|
| NFR-01 | 单文件大小限制 | 10 MB |
| NFR-02 | 单次文件数量限制 | 100 个 |
| NFR-03 | 单次总大小限制 | 500 MB |
| NFR-04 | 批量上传速率限制 | 5 次/分钟 |
| NFR-05 | 进度查询间隔 | 2 秒 |
| NFR-06 | 任务超时清理 | 24 小时 |

### 2.3 处理模式

```python
if 文件数 < 20:
    模式 = "同步处理"  # 直接返回结果
else:
    模式 = "异步处理"  # 返回任务 ID，后台处理
```

## 3. 架构设计

### 3.1 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                            前端层                                    │
├─────────────────────────────────────────────────────────────────────┤
│  DocumentPanel.vue                                                  │
│    ├─ el-upload（拖拽/选择文件）                                    │
│    ├─ BatchUploadProgress.vue（新组件）                              │
│    │     ├─ 阶段1：上传进度条                                       │
│    │     └─ 阶段2：索引进度条                                       │
│    └─ api/index.js                                                  │
│          ├─ uploadBatch(files) → POST /upload/batch                 │
│          └─ getBatchStatus(taskId) → GET /upload/batch/status/{id}  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           后端层                                     │
├─────────────────────────────────────────────────────────────────────┤
│  api/documents.py                                                   │
│    ├─ POST /upload/batch（批量上传）                                │
│    │     ├─ 文件数 < 20：同步处理，直接返回                         │
│    │     └─ 文件数 >= 20：保存文件，创建后台任务                    │
│    ├─ GET /upload/batch/status/{task_id}（查询进度）                │
│    └─ 后台线程：批量索引处理                                       │
│                                                                     │
│  core/task_manager.py（新增）                                       │
│    ├─ 任务状态管理（内存存储）                                      │
│    ├─ 进度追踪                                                      │
│    └─ 错误重试逻辑                                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          存储层                                      │
├─────────────────────────────────────────────────────────────────────┤
│  文件系统：data/knowledge-base/（保存原始文件）                      │
│  Chroma：向量索引                                                   │
│  内存：任务状态（_batch_tasks dict）                                │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
用户选择文件 → 前端验证 → 调用 /upload/batch
                              │
                              ├─ 文件数 < 20
                              │     ↓
                              │   同步处理
                              │     ↓
                              │   返回结果
                              │
                              └─ 文件数 >= 20
                                    ↓
                                  保存文件
                                    ↓
                                  创建任务
                                    ↓
                                  返回任务 ID
                                    ↓
                                  前端轮询
                                    ↓
                                  后台索引
                                    ↓
                                  完成通知
```

## 4. API 设计

### 4.1 批量上传

```
POST /api/upload/batch
Content-Type: multipart/form-data
Authorization: Bearer <token>

请求参数：
  files: List[UploadFile]  # 多个文件，最多 100 个

响应（同步模式）：
{
  "mode": "sync",
  "total": 15,
  "success": 14,
  "failed": 1,
  "results": [
    {"filename": "doc1.md", "status": "success", "chunks": 5},
    {"filename": "doc2.pdf", "status": "success", "chunks": 12},
    {"filename": "broken.txt", "status": "failed", "error": "文件格式错误"}
  ]
}

响应（异步模式）：
{
  "mode": "async",
  "task_id": "batch_20260616_143052_a1b2c3",
  "total": 100,
  "message": "批量上传任务已创建，请通过 /upload/batch/status/{task_id} 查询进度"
}
```

### 4.2 查询进度

```
GET /api/upload/batch/status/{task_id}
Authorization: Bearer <token>

响应：
{
  "task_id": "batch_20260616_143052_a1b2c3",
  "status": "running",
  "phase": "indexing",
  "total": 100,
  "upload": {
    "current": 100,
    "total": 100,
    "failed": []
  },
  "index": {
    "current": 45,
    "total": 100,
    "success": 42,
    "failed": [
      {"filename": "bad.pdf", "error": "PDF 解析失败", "retries": 3}
    ]
  },
  "started_at": 1687876252.0,
  "elapsed_seconds": 120.5,
  "estimated_remaining": 180.0
}
```

### 4.3 速率限制

| API | 限制 |
|-----|------|
| POST /upload | 30 次/分钟 |
| POST /upload/batch | 5 次/分钟 |
| GET /upload/batch/status | 60 次/分钟 |

## 5. 前端设计

### 5.1 组件结构

```
DocumentPanel.vue
  ├─ el-upload（现有）
  ├─ BatchUploadProgress.vue（新增）
  │     ├─ 阶段1：上传进度
  │     ├─ 阶段2：索引进度
  │     └─ 失败文件列表
  └─ 状态消息（现有）
```

### 5.2 BatchUploadProgress 组件

**Props**：
- `taskId`: String（必需）- 任务 ID
- `total`: Number（必需）- 文件总数

**Events**：
- `close`: 用户点击关闭
- `complete`: 任务完成，返回 `{ success, failed }`

**状态**：
- `phase`: "uploading" | "indexing" | "completed"
- `upload`: `{ current, total, failed }`
- `index`: `{ current, total, success, failed }`

### 5.3 轮询机制

```javascript
// 轮询间隔：2 秒
// 失败后间隔：5 秒
// 组件卸载时清除定时器
```

## 6. 后端设计

### 6.1 新增模块：core/task_manager.py

**职责**：
- 任务状态管理（内存存储）
- 进度追踪
- 线程安全

**核心类**：
- `TaskProgress`: 任务进度数据类
- `TaskManager`: 任务管理器（线程安全）

**接口**：
- `create_task(total) -> task_id`
- `get_task(task_id) -> TaskProgress`
- `update_upload_progress(task_id, current)`
- `update_index_progress(task_id, current, success)`
- `add_index_failure(task_id, filename, error, retries)`
- `complete_task(task_id)`
- `fail_task(task_id, error)`

### 6.2 修改模块：api/documents.py

**新增函数**：
- `upload_batch()`: 批量上传端点
- `get_batch_status()`: 查询进度端点
- `_process_sync()`: 同步处理逻辑
- `_process_async()`: 异步处理逻辑

### 6.3 修改模块：core/rate_limit.py

**新增常量**：
- `RATE_LIMIT_BATCH_UPLOAD = "5/minute"`

## 7. 错误处理

### 7.1 错误分类

| 错误类型 | 阶段 | 处理策略 | 重试 |
|----------|------|----------|------|
| 文件格式不支持 | 上传前 | 跳过 | ❌ |
| 文件过大 | 上传前 | 跳过 | ❌ |
| 磁盘空间不足 | 上传 | 终止任务 | ❌ |
| 网络中断 | 上传 | 终止任务 | ❌ |
| 解析失败 | 索引 | 记录失败 | ✅ 3次 |
| 向量化失败 | 索引 | 记录失败 | ✅ 3次 |
| 数据库写入失败 | 索引 | 记录失败 | ✅ 3次 |

### 7.2 重试策略

```python
MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 5]  # 指数退避（秒）

for retry in range(MAX_RETRIES):
    try:
        # 尝试处理
        break
    except Exception:
        if retry < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAYS[retry])
        else:
            # 记录最终失败
```

### 7.3 边界情况

| 情况 | 处理方式 |
|------|----------|
| 服务重启 | 任务状态丢失，文件已保存，可用"加载本地文档"恢复 |
| 并发上传 | 同时只允许 1 个批量任务运行 |
| 任务超时 | 24 小时后自动清理 |

## 8. 测试策略

### 8.1 后端测试

- 单元测试：task_manager.py（覆盖率 95%）
- API 测试：documents.py（覆盖率 90%）
- 集成测试：完整流程

### 8.2 前端测试

- 组件测试：BatchUploadProgress.vue（覆盖率 80%）
- E2E 测试：关键路径

### 8.3 测试用例

1. 小批量同步处理（<20 文件）
2. 大批量异步处理（>=20 文件）
3. 文件数量超限（>100）
4. 文件总大小超限（>500MB）
5. 无效文件跳过
6. 任务进度查询
7. 任务不存在返回 404
8. 失败重试机制
9. 并发任务限制

## 9. 实现计划

### 9.1 阶段一：后端核心（预计 2 小时）

1. 创建 `core/task_manager.py`
2. 修改 `core/rate_limit.py`
3. 修改 `api/documents.py`
4. 编写后端测试

### 9.2 阶段二：前端组件（预计 1.5 小时）

1. 创建 `BatchUploadProgress.vue`
2. 修改 `api/index.js`
3. 修改 `DocumentPanel.vue`
4. 编写前端测试

### 9.3 阶段三：集成测试（预计 0.5 小时）

1. 完整流程测试
2. 边界情况验证
3. 性能测试

## 10. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 内存溢出 | 中 | 高 | 限制并发任务数，监控内存使用 |
| 任务状态丢失 | 低 | 中 | 文件已保存，可用"加载本地文档"恢复 |
| 网络超时 | 中 | 中 | 增加超时时间，优化错误提示 |
| 磁盘空间不足 | 低 | 高 | 上传前检查空间，及时清理失败文件 |

## 11. 附录

### 11.1 术语表

| 术语 | 定义 |
|------|------|
| 同步处理 | 上传后立即索引，等待完成后返回结果 |
| 异步处理 | 上传后立即返回任务 ID，后台异步索引 |
| 任务 ID | 批量上传任务的唯一标识符 |
| 索引 | 将文档切分、向量化并存入数据库的过程 |

### 11.2 参考文档

- 现有上传逻辑：`backend/api/documents.py`
- 速率限制：`backend/core/rate_limit.py`
- 前端组件：`frontend/src/components/DocumentPanel.vue`
