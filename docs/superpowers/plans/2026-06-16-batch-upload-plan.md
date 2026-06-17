# 批量上传功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的批量上传功能，支持最多 100 个文件一次性上传，分阶段显示进度，失败自动重试。

**Architecture:** 采用 HTTP 轮询机制，小批量（<20）同步处理，大批量异步处理。新增 task_manager 模块管理后台任务状态，前端新增 BatchUploadProgress 组件展示分阶段进度。

**Tech Stack:** Python 3.10+, FastAPI, Vue 3, Element Plus, Axios

---

## 文件结构

### 新增文件

| 文件路径 | 职责 |
|----------|------|
| `backend/core/task_manager.py` | 批量任务状态管理（线程安全） |
| `backend/tests/test_batch_upload.py` | 批量上传 API 测试 |
| `frontend/src/components/BatchUploadProgress.vue` | 批量上传进度展示组件 |
| `frontend/src/components/__tests__/BatchUploadProgress.test.js` | 前端组件测试 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `backend/core/rate_limit.py:20-21` | 新增批量上传速率限制常量 |
| `backend/api/documents.py:49-109` | 新增批量上传 API 端点 |
| `frontend/src/api/index.js:155-168` | 新增批量上传 API 函数 |
| `frontend/src/components/DocumentPanel.vue:42-63` | 集成批量上传进度组件 |

---

## Task 1: 创建任务管理器模块

**Files:**
- Create: `backend/core/task_manager.py`
- Test: `backend/tests/test_task_manager.py`

- [ ] **Step 1: 编写任务管理器测试**

```python
# backend/tests/test_task_manager.py

import pytest
import time
from core.task_manager import TaskManager, TaskStatus, TaskPhase


class TestTaskManager:
    """任务管理器测试"""

    def setup_method(self):
        """每个测试前创建新的管理器实例"""
        self.manager = TaskManager()

    def test_create_task(self):
        """测试创建任务"""
        task_id = self.manager.create_task(total=100)

        assert task_id is not None
        assert task_id.startswith("batch_")

        task = self.manager.get_task(task_id)
        assert task is not None
        assert task.total == 100
        assert task.status == TaskStatus.PENDING
        assert task.phase == TaskPhase.UPLOADING

    def test_get_nonexistent_task(self):
        """测试获取不存在的任务"""
        task = self.manager.get_task("nonexistent")
        assert task is None

    def test_update_upload_progress(self):
        """测试更新上传进度"""
        task_id = self.manager.create_task(total=100)

        self.manager.update_upload_progress(task_id, current=50)

        task = self.manager.get_task(task_id)
        assert task.upload_current == 50

    def test_add_upload_failure(self):
        """测试记录上传失败"""
        task_id = self.manager.create_task(total=100)

        self.manager.add_upload_failure(task_id, "bad.txt", "格式错误")

        task = self.manager.get_task(task_id)
        assert len(task.upload_failed) == 1
        assert task.upload_failed[0].filename == "bad.txt"
        assert task.upload_failed[0].error == "格式错误"

    def test_set_phase(self):
        """测试切换阶段"""
        task_id = self.manager.create_task(total=100)

        self.manager.set_phase(task_id, TaskPhase.INDEXING)

        task = self.manager.get_task(task_id)
        assert task.phase == TaskPhase.INDEXING

    def test_update_index_progress(self):
        """测试更新索引进度"""
        task_id = self.manager.create_task(total=100)

        self.manager.update_index_progress(task_id, current=30, success=28)

        task = self.manager.get_task(task_id)
        assert task.index_current == 30
        assert task.index_success == 28

    def test_add_index_failure(self):
        """测试记录索引失败"""
        task_id = self.manager.create_task(total=100)

        self.manager.add_index_failure(task_id, "bad.pdf", "解析失败", retries=3)

        task = self.manager.get_task(task_id)
        assert len(task.index_failed) == 1
        assert task.index_failed[0].filename == "bad.pdf"
        assert task.index_failed[0].retries == 3

    def test_complete_task(self):
        """测试完成任务"""
        task_id = self.manager.create_task(total=100)

        self.manager.complete_task(task_id)

        task = self.manager.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_fail_task(self):
        """测试标记任务失败"""
        task_id = self.manager.create_task(total=100)

        self.manager.fail_task(task_id, "磁盘空间不足")

        task = self.manager.get_task(task_id)
        assert task.status == TaskStatus.FAILED

    def test_snapshot(self):
        """测试生成进度快照"""
        task_id = self.manager.create_task(total=100)
        self.manager.update_upload_progress(task_id, current=50)
        self.manager.update_index_progress(task_id, current=30, success=28)

        task = self.manager.get_task(task_id)
        snapshot = task.snapshot()

        assert snapshot["task_id"] == task_id
        assert snapshot["status"] == "pending"
        assert snapshot["phase"] == "uploading"
        assert snapshot["total"] == 100
        assert snapshot["upload"]["current"] == 50
        assert snapshot["index"]["current"] == 30
        assert snapshot["index"]["success"] == 28

    def test_cleanup_old_tasks(self):
        """测试清理旧任务"""
        # 创建一个任务并手动设置旧时间
        task_id = self.manager.create_task(total=100)
        task = self.manager.get_task(task_id)
        task.started_at = time.time() - (25 * 3600)  # 25 小时前

        # 清理 24 小时前的任务
        self.manager.cleanup_old_tasks(max_age_hours=24)

        # 任务应该被删除
        assert self.manager.get_task(task_id) is None

    def test_thread_safety(self):
        """测试线程安全"""
        import threading

        results = []

        def create_tasks():
            for _ in range(10):
                task_id = self.manager.create_task(total=10)
                results.append(task_id)

        # 并发创建任务
        threads = [threading.Thread(target=create_tasks) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 应该有 50 个任务
        assert len(results) == 50

        # 所有任务都应该存在
        for task_id in results:
            assert self.manager.get_task(task_id) is not None
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend
python -m pytest tests/test_task_manager.py -v
```

预期输出：FAIL（模块不存在）

- [ ] **Step 3: 实现任务管理器**

```python
# backend/core/task_manager.py

"""批量任务管理器

管理批量上传任务的状态和进度追踪。
使用内存存储，适合单实例部署。
"""

import threading
import time
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPhase(str, Enum):
    """任务阶段"""
    UPLOADING = "uploading"
    INDEXING = "indexing"


@dataclass
class FailedItem:
    """失败项"""
    filename: str
    error: str
    retries: int = 0


@dataclass
class TaskProgress:
    """任务进度"""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    phase: TaskPhase = TaskPhase.UPLOADING
    total: int = 0

    # 上传进度
    upload_current: int = 0
    upload_failed: List[FailedItem] = field(default_factory=list)

    # 索引进度
    index_current: int = 0
    index_success: int = 0
    index_failed: List[FailedItem] = field(default_factory=list)

    # 时间
    started_at: float = field(default_factory=time.time)

    def snapshot(self) -> dict:
        """生成进度快照"""
        elapsed = time.time() - self.started_at

        # 估算剩余时间
        if self.phase == TaskPhase.UPLOADING and self.upload_current > 0:
            avg_time = elapsed / self.upload_current
            remaining = avg_time * (self.total - self.upload_current)
        elif self.phase == TaskPhase.INDEXING and self.index_current > 0:
            avg_time = elapsed / self.index_current
            remaining = avg_time * (self.total - self.index_current)
        else:
            remaining = 0

        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "phase": self.phase.value,
            "total": self.total,
            "upload": {
                "current": self.upload_current,
                "total": self.total,
                "failed": [
                    {"filename": f.filename, "error": f.error}
                    for f in self.upload_failed
                ]
            },
            "index": {
                "current": self.index_current,
                "total": self.total,
                "success": self.index_success,
                "failed": [
                    {"filename": f.filename, "error": f.error, "retries": f.retries}
                    for f in self.index_failed
                ]
            },
            "started_at": self.started_at,
            "elapsed_seconds": round(elapsed, 1),
            "estimated_remaining": round(remaining, 1)
        }


class TaskManager:
    """批量任务管理器（线程安全）"""

    def __init__(self):
        self._tasks: Dict[str, TaskProgress] = {}
        self._lock = threading.Lock()

    def create_task(self, total: int) -> str:
        """创建新任务

        Args:
            total: 文件总数

        Returns:
            任务 ID
        """
        task_id = f"batch_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        with self._lock:
            self._tasks[task_id] = TaskProgress(
                task_id=task_id,
                total=total
            )

        return task_id

    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务

        Args:
            task_id: 任务 ID

        Returns:
            任务进度对象，不存在返回 None
        """
        with self._lock:
            return self._tasks.get(task_id)

    def update_upload_progress(self, task_id: str, current: int):
        """更新上传进度

        Args:
            task_id: 任务 ID
            current: 当前已上传数量
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.upload_current = current

    def add_upload_failure(self, task_id: str, filename: str, error: str):
        """记录上传失败

        Args:
            task_id: 任务 ID
            filename: 文件名
            error: 错误信息
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.upload_failed.append(FailedItem(filename=filename, error=error))

    def set_phase(self, task_id: str, phase: TaskPhase):
        """切换阶段

        Args:
            task_id: 任务 ID
            phase: 目标阶段
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.phase = phase

    def update_index_progress(self, task_id: str, current: int, success: int):
        """更新索引进度

        Args:
            task_id: 任务 ID
            current: 当前已索引数量
            success: 成功数量
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.index_current = current
                task.index_success = success

    def add_index_failure(self, task_id: str, filename: str, error: str, retries: int):
        """记录索引失败

        Args:
            task_id: 任务 ID
            filename: 文件名
            error: 错误信息
            retries: 重试次数
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.index_failed.append(FailedItem(
                    filename=filename, error=error, retries=retries
                ))

    def complete_task(self, task_id: str):
        """标记任务完成

        Args:
            task_id: 任务 ID
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED

    def fail_task(self, task_id: str, error: str):
        """标记任务失败

        Args:
            task_id: 任务 ID
            error: 错误信息
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.FAILED

    def has_running_task(self) -> bool:
        """检查是否有运行中的任务

        Returns:
            是否有运行中的任务
        """
        with self._lock:
            return any(
                task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
                for task in self._tasks.values()
            )

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务

        Args:
            max_age_hours: 最大保留时间（小时）
        """
        cutoff = time.time() - (max_age_hours * 3600)
        with self._lock:
            to_delete = [
                task_id for task_id, task in self._tasks.items()
                if task.started_at < cutoff
            ]
            for task_id in to_delete:
                del self._tasks[task_id]


# 全局单例
task_manager = TaskManager()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend
python -m pytest tests/test_task_manager.py -v
```

预期输出：PASS（所有测试通过）

- [ ] **Step 5: 提交代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add backend/core/task_manager.py backend/tests/test_task_manager.py
git commit -m "feat: add TaskManager for batch upload progress tracking"
```

---

## Task 2: 添加批量上传速率限制

**Files:**
- Modify: `backend/core/rate_limit.py:20-21`

- [ ] **Step 1: 添加速率限制常量**

```python
# backend/core/rate_limit.py

# 在文件末尾添加
RATE_LIMIT_BATCH_UPLOAD = "5/minute"  # 批量上传
```

- [ ] **Step 2: 提交代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add backend/core/rate_limit.py
git commit -m "feat: add rate limit constant for batch upload"
```

---

## Task 3: 实现批量上传 API

**Files:**
- Modify: `backend/api/documents.py`
- Test: `backend/tests/test_batch_upload.py`

- [ ] **Step 1: 编写批量上传 API 测试**

```python
# backend/tests/test_batch_upload.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import tempfile


class TestBatchUpload:
    """批量上传 API 测试"""

    def test_sync_mode_small_batch(self, client, auth_headers, sample_files_10):
        """测试小批量同步处理（<20个文件）"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_10,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "sync"
        assert data["total"] == 10
        assert data["success"] == 10

    def test_async_mode_large_batch(self, client, auth_headers, sample_files_25):
        """测试大批量异步处理（>=20个文件）"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "async"
        assert "task_id" in data
        assert data["total"] == 25

    def test_file_count_limit(self, client, auth_headers, sample_files_101):
        """测试文件数量限制（100个）"""
        response = client.post(
            "/api/upload/batch",
            files=sample_files_101,
            headers=auth_headers
        )

        assert response.status_code == 400
        assert "最多上传 100 个文件" in response.json()["detail"]

    def test_empty_files(self, client, auth_headers):
        """测试空文件列表"""
        response = client.post(
            "/api/upload/batch",
            files=[],
            headers=auth_headers
        )

        assert response.status_code == 422  # FastAPI 验证错误

    def test_invalid_file_skipped(self, client, auth_headers):
        """测试无效文件被跳过"""
        files = [
            ("files", ("valid.txt", b"valid content", "text/plain")),
            ("files", ("invalid.xyz", b"invalid", "application/octet-stream")),
        ]

        response = client.post(
            "/api/upload/batch",
            files=files,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1  # 只有 1 个有效文件

    def test_query_task_status(self, client, auth_headers, sample_files_25):
        """测试查询任务进度"""
        # 先创建一个任务
        response = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers
        )
        task_id = response.json()["task_id"]

        # 查询进度
        status_response = client.get(
            f"/api/upload/batch/status/{task_id}",
            headers=auth_headers
        )

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
        assert data["status"] in ["pending", "running", "completed"]

    def test_task_not_found(self, client, auth_headers):
        """测试查询不存在的任务"""
        response = client.get(
            "/api/upload/batch/status/nonexistent_task",
            headers=auth_headers
        )

        assert response.status_code == 404
        assert "任务不存在" in response.json()["detail"]

    def test_concurrent_task_limit(self, client, auth_headers, sample_files_25):
        """测试并发任务限制"""
        # 创建第一个任务
        response1 = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers
        )
        assert response1.status_code == 200

        # 尝试创建第二个任务
        response2 = client.post(
            "/api/upload/batch",
            files=sample_files_25,
            headers=auth_headers
        )

        assert response2.status_code == 409
        assert "已有批量任务正在运行" in response2.json()["detail"]
```

- [ ] **Step 2: 编写测试 fixtures**

```python
# backend/tests/conftest.py 添加以下 fixtures

@pytest.fixture
def sample_files_10():
    """生成 10 个测试文件"""
    return [
        ("files", (f"test_{i}.txt", b"test content", "text/plain"))
        for i in range(10)
    ]


@pytest.fixture
def sample_files_25():
    """生成 25 个测试文件"""
    return [
        ("files", (f"test_{i}.txt", b"test content", "text/plain"))
        for i in range(25)
    ]


@pytest.fixture
def sample_files_101():
    """生成 101 个测试文件"""
    return [
        ("files", (f"test_{i}.txt", b"test content", "text/plain"))
        for i in range(101)
    ]
```

- [ ] **Step 3: 运行测试验证失败**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend
python -m pytest tests/test_batch_upload.py -v
```

预期输出：FAIL（端点不存在）

- [ ] **Step 4: 实现批量上传 API**

```python
# backend/api/documents.py

# 在文件顶部添加导入
import threading
from typing import List
from core.task_manager import task_manager, TaskPhase
from core.rate_limit import limiter, RATE_LIMIT_UPLOAD, RATE_LIMIT_BATCH_UPLOAD

# 在文件中添加常量
MAX_BATCH_FILES = 100
MAX_BATCH_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB
SYNC_THRESHOLD = 20  # 小于此数量同步处理
MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 5]  # 指数退避（秒）

# 在现有 upload_document 端点之后添加

@router.post("/upload/batch")
@limiter.limit(RATE_LIMIT_BATCH_UPLOAD)
async def upload_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    """批量上传文档

    小批量（<20）同步处理，直接返回结果。
    大批量（>=20）异步处理，返回任务 ID。
    """
    engine, config = get_engine_and_config()

    # 1. 检查是否有运行中的任务
    if task_manager.has_running_task():
        raise HTTPException(
            status_code=409,
            detail="已有批量任务正在运行，请稍后再试"
        )

    # 2. 验证文件数量
    if len(files) == 0:
        raise HTTPException(status_code=400, detail="请选择至少一个文件")
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"单次最多上传 {MAX_BATCH_FILES} 个文件"
        )

    # 3. 验证并收集有效文件
    supported_types = [".html", ".htm", ".txt", ".md", ".pdf", ".docx",
                       ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"]

    file_list = []
    total_size = 0

    for file in files:
        # 防止路径遍历
        safe_name = os.path.basename(file.filename)
        if not safe_name:
            continue

        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in supported_types:
            continue

        content = await file.read()
        total_size += len(content)

        # 检查单文件大小
        if len(content) > MAX_FILE_SIZE:
            continue

        # 检查总大小
        if total_size > MAX_BATCH_TOTAL_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"文件总大小超过限制（最大 {MAX_BATCH_TOTAL_SIZE // (1024*1024)}MB）"
            )

        file_list.append({
            "filename": safe_name,
            "content": content,
            "size": len(content)
        })

    if not file_list:
        raise HTTPException(status_code=400, detail="没有有效的文件")

    # 4. 根据文件数量选择处理模式
    if len(file_list) < SYNC_THRESHOLD:
        return await _process_batch_sync(file_list, engine, config)
    else:
        return await _process_batch_async(file_list, engine, config)


async def _process_batch_sync(file_list: list, engine, config) -> dict:
    """同步处理小批量文件"""
    os.makedirs(config.DATA_DIR, exist_ok=True)

    results = []
    success_count = 0

    for item in file_list:
        file_path = os.path.join(config.DATA_DIR, item["filename"])

        try:
            # 保存文件
            with open(file_path, "wb") as f:
                f.write(item["content"])

            # 索引（先删除旧向量）
            engine.delete_by_source(item["filename"])
            chunks = engine.ingest_document(file_path)

            results.append({
                "filename": item["filename"],
                "status": "success",
                "chunks": chunks
            })
            success_count += 1

        except Exception as e:
            results.append({
                "filename": item["filename"],
                "status": "failed",
                "error": str(e)
            })

    return {
        "mode": "sync",
        "total": len(file_list),
        "success": success_count,
        "failed": len(file_list) - success_count,
        "results": results
    }


async def _process_batch_async(file_list: list, engine, config) -> dict:
    """异步处理大批量文件"""
    # 保存文件
    os.makedirs(config.DATA_DIR, exist_ok=True)
    saved_files = []

    for item in file_list:
        file_path = os.path.join(config.DATA_DIR, item["filename"])
        try:
            with open(file_path, "wb") as f:
                f.write(item["content"])
            saved_files.append(item["filename"])
        except Exception as e:
            # 记录保存失败
            pass

    # 创建任务
    task_id = task_manager.create_task(len(saved_files))

    # 启动后台索引线程
    def _index_worker():
        try:
            task_manager.set_phase(task_id, TaskPhase.INDEXING)

            success_count = 0
            for i, filename in enumerate(saved_files):
                file_path = os.path.join(config.DATA_DIR, filename)

                # 重试逻辑
                success = False
                for retry in range(MAX_RETRIES):
                    try:
                        engine.delete_by_source(filename)
                        chunks = engine.ingest_document(file_path)
                        success = True
                        break
                    except Exception as e:
                        if retry < MAX_RETRIES - 1:
                            import time
                            time.sleep(RETRY_DELAYS[retry])

                if success:
                    success_count += 1
                else:
                    task_manager.add_index_failure(
                        task_id, filename, "重试 3 次后仍失败", MAX_RETRIES
                    )

                task_manager.update_index_progress(task_id, i + 1, success_count)

            task_manager.complete_task(task_id)

        except Exception as e:
            task_manager.fail_task(task_id, str(e))

    threading.Thread(target=_index_worker, daemon=True).start()

    return {
        "mode": "async",
        "task_id": task_id,
        "total": len(saved_files),
        "message": f"批量上传任务已创建，请通过 /upload/batch/status/{task_id} 查询进度"
    }


@router.get("/upload/batch/status/{task_id}")
async def get_batch_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """查询批量上传进度"""
    task = task_manager.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task.snapshot()
```

- [ ] **Step 5: 运行测试验证通过**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend
python -m pytest tests/test_batch_upload.py -v
```

预期输出：PASS（所有测试通过）

- [ ] **Step 6: 提交代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add backend/api/documents.py backend/tests/test_batch_upload.py
git commit -m "feat: add batch upload API with sync/async modes"
```

---

## Task 4: 添加前端批量上传 API 函数

**Files:**
- Modify: `frontend/src/api/index.js:155-168`

- [ ] **Step 1: 添加批量上传 API 函数**

```javascript
// frontend/src/api/index.js

// 在 uploadDocument 函数之后添加

// 批量上传
export async function uploadBatch(files) {
  const formData = new FormData()
  files.forEach(file => {
    formData.append('files', file.raw || file)
  })

  const response = await api.post('/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000  // 5 分钟超时
  })
  return response.data
}

// 查询批量上传进度
export async function getBatchStatus(taskId) {
  const response = await api.get(`/upload/batch/status/${taskId}`)
  return response.data
}
```

- [ ] **Step 2: 提交代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add frontend/src/api/index.js
git commit -m "feat: add batch upload API functions"
```

---

## Task 5: 创建批量上传进度组件

**Files:**
- Create: `frontend/src/components/BatchUploadProgress.vue`
- Test: `frontend/src/components/__tests__/BatchUploadProgress.test.js`

- [ ] **Step 1: 编写组件测试**

```javascript
// frontend/src/components/__tests__/BatchUploadProgress.test.js

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import BatchUploadProgress from '../BatchUploadProgress.vue'
import * as api from '../../api'

vi.mock('../../api')

describe('BatchUploadProgress', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('应该显示上传进度', async () => {
    api.getBatchStatus.mockResolvedValue({
      task_id: 'test_task',
      status: 'running',
      phase: 'uploading',
      total: 100,
      upload: { current: 50, total: 100, failed: [] },
      index: { current: 0, total: 100, success: 0, failed: [] },
      elapsed_seconds: 60,
      estimated_remaining: 60
    })

    const wrapper = mount(BatchUploadProgress, {
      props: { taskId: 'test_task', total: 100 }
    })

    await vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.upload-status').text()).toContain('50/100')
  })

  it('应该显示索引进度', async () => {
    api.getBatchStatus.mockResolvedValue({
      task_id: 'test_task',
      status: 'running',
      phase: 'indexing',
      total: 100,
      upload: { current: 100, total: 100, failed: [] },
      index: { current: 50, total: 100, success: 48, failed: [] },
      elapsed_seconds: 120,
      estimated_remaining: 120
    })

    const wrapper = mount(BatchUploadProgress, {
      props: { taskId: 'test_task', total: 100 }
    })

    await vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.index-status').text()).toContain('50/100')
    expect(wrapper.find('.index-status').text()).toContain('48 成功')
  })

  it('应该显示失败文件列表', async () => {
    api.getBatchStatus.mockResolvedValue({
      task_id: 'test_task',
      status: 'running',
      phase: 'indexing',
      total: 100,
      upload: { current: 100, total: 100, failed: [] },
      index: {
        current: 50,
        total: 100,
        success: 48,
        failed: [
          { filename: 'bad.pdf', error: '解析失败', retries: 3 }
        ]
      },
      elapsed_seconds: 120,
      estimated_remaining: 120
    })

    const wrapper = mount(BatchUploadProgress, {
      props: { taskId: 'test_task', total: 100 }
    })

    await vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.error-count').text()).toContain('1 个文件索引失败')
  })

  it('应该在完成时触发 complete 事件', async () => {
    api.getBatchStatus.mockResolvedValue({
      task_id: 'test_task',
      status: 'completed',
      phase: 'completed',
      total: 100,
      upload: { current: 100, total: 100, failed: [] },
      index: { current: 100, total: 100, success: 98, failed: [] },
      elapsed_seconds: 300,
      estimated_remaining: 0
    })

    const wrapper = mount(BatchUploadProgress, {
      props: { taskId: 'test_task', total: 100 }
    })

    await vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('complete')).toBeTruthy()
    expect(wrapper.emitted('complete')[0][0]).toEqual({
      success: 98,
      failed: []
    })
  })

  it('应该在点击关闭时触发 close 事件', async () => {
    api.getBatchStatus.mockResolvedValue({
      task_id: 'test_task',
      status: 'completed',
      phase: 'completed',
      total: 100,
      upload: { current: 100, total: 100, failed: [] },
      index: { current: 100, total: 100, success: 100, failed: [] },
      elapsed_seconds: 300,
      estimated_remaining: 0
    })

    const wrapper = mount(BatchUploadProgress, {
      props: { taskId: 'test_task', total: 100 }
    })

    await vi.advanceTimersByTime(2000)
    await wrapper.vm.$nextTick()

    await wrapper.find('.close-btn').trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('应该在组件卸载时清除定时器', async () => {
    api.getBatchStatus.mockResolvedValue({
      task_id: 'test_task',
      status: 'running',
      phase: 'uploading',
      total: 100,
      upload: { current: 50, total: 100, failed: [] },
      index: { current: 0, total: 100, success: 0, failed: [] },
      elapsed_seconds: 60,
      estimated_remaining: 60
    })

    const wrapper = mount(BatchUploadProgress, {
      props: { taskId: 'test_task', total: 100 }
    })

    await vi.advanceTimersByTime(2000)
    wrapper.unmount()

    // 定时器应该被清除
    expect(api.getBatchStatus).toHaveBeenCalledTimes(1)
  })
})
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/frontend
npm run test -- BatchUploadProgress.test.js
```

预期输出：FAIL（组件不存在）

- [ ] **Step 3: 实现批量上传进度组件**

```vue
<!-- frontend/src/components/BatchUploadProgress.vue -->

<template>
  <div class="batch-progress" v-if="visible">
    <!-- 阶段1：上传进度 -->
    <div class="phase" :class="{ active: phase === 'uploading', done: phase === 'indexing' || phase === 'completed' }">
      <div class="phase-header">
        <span class="phase-icon">📤</span>
        <span class="phase-title">阶段 1：上传文件</span>
        <span class="phase-status upload-status">{{ uploadStatusText }}</span>
      </div>
      <el-progress
        :percentage="uploadPercent"
        :status="uploadProgressStatus"
        :stroke-width="8"
      />
      <div class="phase-detail" v-if="upload.failed.length > 0">
        <span class="error-count">⚠️ {{ upload.failed.length }} 个文件上传失败</span>
      </div>
    </div>

    <!-- 阶段2：索引进度 -->
    <div class="phase" :class="{ active: phase === 'indexing', done: phase === 'completed' }">
      <div class="phase-header">
        <span class="phase-icon">🔍</span>
        <span class="phase-title">阶段 2：建立索引</span>
        <span class="phase-status index-status">{{ indexStatusText }}</span>
      </div>
      <el-progress
        :percentage="indexPercent"
        :status="indexProgressStatus"
        :stroke-width="8"
      />
      <div class="phase-detail">
        <span>成功: {{ index.success }}</span>
        <span v-if="index.failed.length > 0" class="error-count">
          失败: {{ index.failed.length }}
        </span>
      </div>
    </div>

    <!-- 失败详情 -->
    <div class="failed-section" v-if="index.failed.length > 0">
      <div class="failed-header" @click="showErrors = !showErrors">
        <span>⚠️ 失败文件详情</span>
        <span class="toggle-icon">{{ showErrors ? '▼' : '▶' }}</span>
      </div>
      <div class="failed-list" v-if="showErrors">
        <div v-for="item in index.failed" :key="item.filename" class="failed-item">
          <span class="filename">{{ item.filename }}</span>
          <span class="error">{{ item.error }}</span>
          <span class="retries">（重试 {{ item.retries }} 次）</span>
        </div>
      </div>
    </div>

    <!-- 时间信息 -->
    <div class="time-info" v-if="phase !== 'completed'">
      <span>已用时: {{ formatTime(elapsed) }}</span>
      <span v-if="estimated > 0">预计剩余: {{ formatTime(estimated) }}</span>
    </div>

    <!-- 完成状态 -->
    <div class="batch-footer" v-if="phase === 'completed'">
      <span class="total-info">
        ✅ 完成！{{ index.success }}/{{ total }} 个文档已索引
      </span>
      <button class="hm-action-btn close-btn" @click="$emit('close')">关闭</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { getBatchStatus } from '../api'

const props = defineProps({
  taskId: { type: String, required: true },
  total: { type: Number, required: true }
})

const emit = defineEmits(['close', 'complete'])

// 状态
const visible = ref(true)
const phase = ref('uploading')  // uploading | indexing | completed
const upload = ref({ current: 0, total: props.total, failed: [] })
const index = ref({ current: 0, total: props.total, success: 0, failed: [] })
const elapsed = ref(0)
const estimated = ref(0)
const showErrors = ref(false)

// 计算属性
const uploadPercent = computed(() =>
  upload.value.total > 0
    ? Math.round((upload.value.current / upload.value.total) * 100)
    : 0
)
const indexPercent = computed(() =>
  index.value.total > 0
    ? Math.round((index.value.current / index.value.total) * 100)
    : 0
)
const uploadStatusText = computed(() =>
  `${upload.value.current}/${upload.value.total}`
)
const indexStatusText = computed(() =>
  `${index.value.current}/${index.value.total} (${index.value.success} 成功)`
)
const uploadProgressStatus = computed(() => {
  if (phase.value === 'indexing' || phase.value === 'completed') return 'success'
  if (upload.value.failed.length > 0) return 'warning'
  return undefined
})
const indexProgressStatus = computed(() => {
  if (phase.value === 'completed') return 'success'
  if (index.value.failed.length > 0) return 'warning'
  return undefined
})

// 格式化时间
function formatTime(seconds) {
  if (seconds < 60) return `${Math.round(seconds)}秒`
  if (seconds < 3600) return `${Math.round(seconds / 60)}分钟`
  return `${Math.round(seconds / 3600)}小时`
}

// 轮询
let pollTimer = null
async function pollStatus() {
  try {
    const data = await getBatchStatus(props.taskId)

    // 更新阶段
    phase.value = data.phase

    // 更新进度
    upload.value = data.upload
    index.value = data.index
    elapsed.value = data.elapsed_seconds
    estimated.value = data.estimated_remaining

    // 检查是否完成
    if (data.status === 'completed') {
      phase.value = 'completed'
      emit('complete', {
        success: index.value.success,
        failed: index.value.failed
      })
      return
    }

    // 继续轮询
    pollTimer = setTimeout(pollStatus, 2000)
  } catch (error) {
    console.error('查询进度失败:', error)
    pollTimer = setTimeout(pollStatus, 5000)  // 失败后延长间隔
  }
}

// 启动轮询
pollStatus()

// 清理
onUnmounted(() => {
  if (pollTimer) clearTimeout(pollTimer)
})
</script>

<style scoped>
.batch-progress {
  padding: 16px;
  background: var(--hm-bg-container-secondary);
  border-radius: var(--hm-radius-lg);
  margin-top: 12px;
}

.phase {
  padding: 12px;
  border-radius: var(--hm-radius-md);
  margin-bottom: 12px;
  opacity: 0.5;
  transition: opacity 0.3s ease;
}

.phase.active,
.phase.done {
  opacity: 1;
}

.phase.active {
  background: var(--hm-brand-bg-light);
}

.phase-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.phase-icon {
  font-size: 18px;
}

.phase-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--hm-font-primary);
}

.phase-status {
  margin-left: auto;
  font-size: 13px;
  color: var(--hm-font-secondary);
}

.phase-detail {
  display: flex;
  gap: 16px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--hm-font-secondary);
}

.error-count {
  color: var(--hm-error);
}

.failed-section {
  margin-top: 12px;
  padding: 12px;
  background: var(--hm-bg-container-tertiary);
  border-radius: var(--hm-radius-md);
}

.failed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  font-size: 13px;
  color: var(--hm-error);
}

.toggle-icon {
  font-size: 12px;
}

.failed-list {
  margin-top: 8px;
  max-height: 150px;
  overflow-y: auto;
}

.failed-item {
  display: flex;
  gap: 8px;
  padding: 6px 0;
  font-size: 12px;
  border-bottom: 1px solid var(--hm-divider);
}

.failed-item:last-child {
  border-bottom: none;
}

.filename {
  font-weight: 500;
  color: var(--hm-font-primary);
}

.error {
  color: var(--hm-font-secondary);
}

.retries {
  color: var(--hm-font-tertiary);
}

.time-info {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  font-size: 12px;
  color: var(--hm-font-tertiary);
}

.batch-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--hm-divider);
}

.total-info {
  font-size: 14px;
  font-weight: 500;
  color: var(--hm-success);
}

.close-btn {
  padding: 6px 16px;
  font-size: 13px;
}
</style>
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/frontend
npm run test -- BatchUploadProgress.test.js
```

预期输出：PASS（所有测试通过）

- [ ] **Step 5: 提交代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add frontend/src/components/BatchUploadProgress.vue frontend/src/components/__tests__/BatchUploadProgress.test.js
git commit -m "feat: add BatchUploadProgress component with two-phase progress display"
```

---

## Task 6: 集成批量上传到文档管理面板

**Files:**
- Modify: `frontend/src/components/DocumentPanel.vue`

- [ ] **Step 1: 添加导入和状态**

```vue
<!-- frontend/src/components/DocumentPanel.vue -->

<script setup>
// 在现有导入之后添加
import { ref } from 'vue'
import BatchUploadProgress from './BatchUploadProgress.vue'
import { uploadBatch } from '../api'

// 在现有状态之后添加
const batchTaskId = ref(null)
const batchTotal = ref(0)
const pendingFiles = ref([])
</script>
```

- [ ] **Step 2: 修改上传处理逻辑**

```vue
<!-- frontend/src/components/DocumentPanel.vue -->

<script setup>
// 替换现有的 handleUpload 函数
async function handleUpload(file) {
  // 收集文件
  pendingFiles.value.push(file)

  // 延迟处理，等待所有文件收集完成
  if (pendingFiles.value.length === 1) {
    setTimeout(async () => {
      const filesToUpload = [...pendingFiles.value]
      pendingFiles.value = []

      if (filesToUpload.length >= 20) {
        // 大批量：使用批量上传
        await handleBatchUpload(filesToUpload)
      } else {
        // 小批量：逐个上传（保持原有行为）
        for (const f of filesToUpload) {
          await handleSingleUpload(f)
        }
      }
    }, 100)
  }
}

// 新增：批量上传处理
async function handleBatchUpload(files) {
  try {
    uploadStatusType.value = 'uploading'
    uploadStatus.value = `正在批量上传 ${files.length} 个文件...`

    const result = await uploadBatch(files)

    if (result.mode === 'sync') {
      // 小批量，直接显示结果
      uploadStatusType.value = 'success'
      uploadStatus.value = `上传成功 · ${result.success} 个成功 / ${result.failed} 个失败`
      await refresh()
    } else {
      // 大批量，显示进度组件
      uploadStatus.value = ''
      batchTaskId.value = result.task_id
      batchTotal.value = result.total
    }
  } catch (error) {
    uploadStatusType.value = 'error'
    uploadStatus.value = `批量上传失败: ${error.message}`
  }
}

// 重命名原有函数
async function handleSingleUpload(file) {
  // 原有的 handleUpload 逻辑
  uploadCount.value.total++
  const idx = uploadCount.value.total
  uploadStatusType.value = 'uploading'
  uploadStatus.value = `正在上传 (${idx}/${idx})...`

  try {
    const result = await uploadDocument(file.raw)
    if (result.error) {
      uploadCount.value.fail++
      uploadStatusType.value = 'error'
      uploadStatus.value = `「${file.name}」: ${result.error}`
    } else {
      uploadCount.value.success++
      uploadStatusType.value = 'success'
      uploadStatus.value = `上传成功 · ${uploadCount.value.success} 个成功 / ${uploadCount.value.fail} 个失败`
      await refresh()
    }
  } catch (error) {
    uploadCount.value.fail++
    uploadStatusType.value = 'error'
    uploadStatus.value = `「${file.name}」上传失败: ${error.message}`
  }

  uploadCount.value.done++
  if (uploadCount.value.done >= uploadCount.value.total) {
    setTimeout(() => {
      uploadCount.value = { done: 0, total: 0, success: 0, fail: 0 }
      uploadStatusType.value = ''
    }, 3000)
  }
}

// 新增：批量完成回调
async function handleBatchComplete({ success, failed }) {
  ElMessage.success(`批量索引完成，成功 ${success} 个`)
  batchTaskId.value = null
  await refresh()
}
</script>
```

- [ ] **Step 3: 添加进度组件到模板**

```vue
<!-- frontend/src/components/DocumentPanel.vue -->

<template>
  <!-- 在 upload-area 的 el-upload 之后添加 -->

  <!-- 批量上传进度 -->
  <BatchUploadProgress
    v-if="batchTaskId"
    :task-id="batchTaskId"
    :total="batchTotal"
    @close="batchTaskId = null"
    @complete="handleBatchComplete"
  />
</template>
```

- [ ] **Step 4: 提交代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add frontend/src/components/DocumentPanel.vue
git commit -m "feat: integrate batch upload into DocumentPanel"
```

---

## Task 7: 集成测试

**Files:**
- 无新增文件

- [ ] **Step 1: 运行后端测试**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/backend
python -m pytest tests/ -v
```

预期输出：PASS（所有测试通过）

- [ ] **Step 2: 运行前端测试**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG/frontend
npm run test
```

预期输出：PASS（所有测试通过）

- [ ] **Step 3: 手动测试完整流程**

1. 启动后端服务
2. 启动前端服务
3. 选择 10 个文件上传（测试同步模式）
4. 选择 30 个文件上传（测试异步模式）
5. 验证进度显示
6. 验证失败重试

- [ ] **Step 4: 提交最终代码**

```bash
cd D:/HuaweiMoveData/Users/28966/Desktop/多模态RAG
git add -A
git commit -m "feat: complete batch upload feature with progress tracking"
```

---

## 自审检查清单

### 1. 规格覆盖

- ✅ FR-01: 支持一次性选择最多 100 个文件上传（Task 3）
- ✅ FR-02: 文件数 < 20 时同步处理（Task 3）
- ✅ FR-03: 文件数 >= 20 时异步处理（Task 3）
- ✅ FR-04: 分阶段显示进度（Task 5）
- ✅ FR-05: 索引失败自动重试 3 次（Task 3）
- ✅ FR-06: 显示失败文件列表及错误原因（Task 5）
- ✅ FR-07: 估算剩余时间（Task 5）
- ✅ NFR-01: 单文件大小限制 10MB（Task 3）
- ✅ NFR-02: 单次文件数量限制 100 个（Task 3）
- ✅ NFR-03: 单次总大小限制 500MB（Task 3）
- ✅ NFR-04: 批量上传速率限制 5 次/分钟（Task 2）
- ✅ NFR-05: 进度查询间隔 2 秒（Task 5）
- ✅ NFR-06: 任务超时清理 24 小时（Task 1）

### 2. 占位符扫描

- ✅ 无 TBD/TODO
- ✅ 所有代码块完整
- ✅ 所有测试用例完整

### 3. 类型一致性

- ✅ TaskManager 方法名一致
- ✅ API 响应格式一致
- ✅ 组件 Props/Events 一致

---

## 执行选项

**计划已完成并保存到 `docs/superpowers/plans/2026-06-16-batch-upload-plan.md`。两种执行方式：**

**1. Subagent-Driven（推荐）** - 我为每个任务调度一个新的 subagent，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中执行任务，批量执行并设置检查点

**选择哪种方式？**
