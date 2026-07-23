import os
import re
import logging
import shutil
import threading
import time
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from core.rate_limit import limiter, RATE_LIMIT_UPLOAD, RATE_LIMIT_BATCH_UPLOAD
from core.task_manager import task_manager, TaskPhase
from core.auth import get_current_user
from core.config import AppSettings
from core.services import InfraBundle
from core.services.ingestion_service import IngestionService
from api.deps import get_settings, get_infra, get_ingestion

logger = logging.getLogger(__name__)

# 支持的文件扩展名（统一常量，避免多处重复定义）
SUPPORTED_EXTENSIONS = {
    ".html", ".htm", ".txt", ".md", ".pdf", ".docx",
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif",
}

# 文件上传限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILENAME_LENGTH = 200
ALLOWED_MIME_TYPES = {
    ".html": ["text/html", "application/xhtml+xml"],
    ".htm": ["text/html", "application/xhtml+xml"],
    ".txt": ["text/plain"],
    ".md": ["text/markdown", "text/plain", "application/octet-stream"],
    ".pdf": ["application/pdf"],
    ".docx": ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    # 图片格式（OCR 支持）
    ".png": ["image/png"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
    ".bmp": ["image/bmp"],
    ".tiff": ["image/tiff"],
    ".tif": ["image/tiff"],
}

# 批量上传限制
MAX_BATCH_FILES = 200
MAX_BATCH_TOTAL_SIZE = 500 * 1024 * 1024  # 500MB
SYNC_THRESHOLD = 20
MAX_RETRIES = 3
RETRY_DELAYS = [1, 3, 5]

router = APIRouter()


# ---------------------------------------------------------------------------
# Batch load state
# ---------------------------------------------------------------------------

class _LoadState:
    """线程安全的批量加载进度跟踪"""

    def __init__(self):
        self.status = "idle"  # idle | running | done | error
        self.current = 0
        self.total = 0
        self.result = None
        self.error = None
        self.started_at = None
        self._lock = threading.Lock()

    def try_start(self, total: int) -> bool:
        """尝试开始任务（原子操作，防止竞态条件）

        Args:
            total: Total number of items to process.

        Returns:
            True if the task was started, False if already running.
        """
        with self._lock:
            if self.status == "running":
                return False
            self.status = "running"
            self.current = 0
            self.total = total
            self.result = None
            self.error = None
            self.started_at = time.time()
            return True

    def reset(self, total: int):
        with self._lock:
            self.status = "running"
            self.current = 0
            self.total = total
            self.result = None
            self.error = None
            self.started_at = time.time()

    def advance(self):
        with self._lock:
            self.current += 1

    def finish(self, result: dict):
        with self._lock:
            self.status = "done"
            self.result = result

    def fail(self, error: str):
        with self._lock:
            self.status = "error"
            self.error = error

    def snapshot(self) -> dict:
        with self._lock:
            elapsed = round(time.time() - self.started_at, 1) if self.started_at else 0
            return {
                "status": self.status,
                "current": self.current,
                "total": self.total,
                "elapsed": elapsed,
                "result": self.result,
                "error": self.error,
            }


_load_state = _LoadState()


# ---------------------------------------------------------------------------
# File processing helpers
# ---------------------------------------------------------------------------

def _validate_upload_file(file: UploadFile, safe_name: str) -> str:
    """校验上传文件的名称、扩展名、MIME 类型。

    Args:
        file: FastAPI UploadFile 对象
        safe_name: 经 os.path.basename 处理后的安全文件名

    Returns:
        文件扩展名（小写）

    Raises:
        HTTPException: 校验失败时抛出 400
    """
    if not safe_name:
        raise HTTPException(status_code=400, detail="文件名为空")

    if len(safe_name) > MAX_FILENAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"文件名过长，最大 {MAX_FILENAME_LENGTH} 字符",
        )

    ext = os.path.splitext(safe_name)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式，支持: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # MIME type 校验（与扩展名双重验证）
    if file.content_type:
        allowed_mimes = ALLOWED_MIME_TYPES.get(ext, [])
        if allowed_mimes and file.content_type not in allowed_mimes:
            logger.warning(
                "MIME 类型不匹配: filename=%s, content_type=%s, ext=%s",
                safe_name, file.content_type, ext,
            )
            raise HTTPException(
                status_code=400,
                detail=f"文件类型不匹配，期望 {ext} 格式",
            )

    return ext


def _save_and_ingest(
    ingestion: IngestionService,
    config: AppSettings,
    content: bytes,
    safe_name: str,
) -> int:
    """保存文件到磁盘并建立索引。

    Args:
        ingestion: 文档摄入服务
        config: 应用配置
        content: 文件二进制内容
        safe_name: 安全文件名

    Returns:
        成功索引的 chunk 数量

    Raises:
        HTTPException: 文件过大或处理失败时抛出
    """
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    os.makedirs(config.DATA_DIR, exist_ok=True)
    file_path = os.path.join(config.DATA_DIR, safe_name)

    # 同名文件去重：先删除旧向量
    ingestion.delete_by_source(safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    return ingestion.ingest_document(file_path)


def _process_single_file(
    ingestion: IngestionService,
    config: AppSettings,
    file: UploadFile,
    safe_name: str,
) -> int:
    """处理单个文件：校验、保存、索引。

    Returns:
        成功索引的 chunk 数量。

    Raises:
        HTTPException: 文件校验或处理失败时抛出。
    """
    _validate_upload_file(file, safe_name)
    content = file.file.read()
    return _save_and_ingest(ingestion, config, content, safe_name)


def _process_batch_sync(ingestion: IngestionService, config: AppSettings, files: List[UploadFile]) -> dict:
    """同步处理批量文件，返回汇总结果。"""
    success_count = 0
    results = []

    for file in files:
        safe_name = os.path.basename(file.filename)
        if not safe_name:
            results.append({"filename": file.filename, "status": "failed", "error": "文件名为空"})
            continue
        if len(safe_name) > MAX_FILENAME_LENGTH:
            results.append({"filename": safe_name, "status": "failed", "error": "文件名过长"})
            continue
        try:
            chunks = _process_single_file(ingestion, config, file, safe_name)
            success_count += 1
            results.append({"filename": safe_name, "status": "success", "chunks": chunks})
        except Exception as e:
            logger.warning("批量处理文件失败 %s: %s", safe_name, e)
            results.append({"filename": safe_name, "status": "failed", "error": str(e)})

    return {
        "mode": "sync",
        "total": len(files),
        "success": success_count,
        "failed": len(files) - success_count,
        "results": results,
    }


def _process_batch_async(ingestion: IngestionService, config: AppSettings, files: List[UploadFile], task_id: str):
    """在后台线程中逐个处理文件，带重试逻辑。"""
    task_manager.start_task(task_id)
    task_manager.set_phase(task_id, TaskPhase.UPLOADING)

    success_count = 0

    for idx, file in enumerate(files):
        safe_name = os.path.basename(file.filename)
        if not safe_name:
            task_manager.add_upload_failure(task_id, file.filename or "", "文件名为空")
            task_manager.update_upload_progress(task_id, idx + 1)
            continue
        if len(safe_name) > MAX_FILENAME_LENGTH:
            task_manager.add_upload_failure(task_id, safe_name, "文件名过长")
            task_manager.update_upload_progress(task_id, idx + 1)
            continue

        retries = 0
        for attempt in range(MAX_RETRIES):
            try:
                _process_single_file(ingestion, config, file, safe_name)
                success_count += 1
                break
            except Exception as e:
                retries = attempt + 1
                if attempt < MAX_RETRIES - 1:
                    logger.warning(
                        "批量处理文件失败 %s (尝试 %d/%d): %s",
                        safe_name, retries, MAX_RETRIES, e,
                    )
                    time.sleep(RETRY_DELAYS[attempt])
                else:
                    logger.warning("批量处理文件最终失败 %s: %s", safe_name, e)
                    task_manager.add_index_failure(
                        task_id, safe_name, str(e), retries=retries
                    )

        task_manager.update_upload_progress(task_id, idx + 1)

    task_manager.update_index_progress(task_id, len(files), success_count)
    task_manager.complete_task(task_id)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@router.post("/upload")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """上传文档（同名文件自动去重）"""
    # 防止路径遍历：只取文件名，丢弃路径分隔符
    safe_name = os.path.basename(file.filename)
    _validate_upload_file(file, safe_name)

    try:
        content = await file.read()
        chunks = _save_and_ingest(ingestion, config, content, safe_name)
        return {
            "message": "上传成功",
            "filename": safe_name,
            "chunks": chunks,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("文档上传失败")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/upload/batch")
@limiter.limit(RATE_LIMIT_BATCH_UPLOAD)
async def batch_upload(
    request: Request,
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """批量上传文档。

    文件数 < SYNC_THRESHOLD 时同步处理并直接返回结果，
    否则异步处理并返回 task_id 供前端轮询。
    """
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"最多上传 {MAX_BATCH_FILES} 个文件",
        )

    # Read all file contents once for size check + later processing
    file_contents = []  # list of (filename, bytes)
    total_size = 0
    for file in files:
        content = await file.read()
        total_size += len(content)
        file_contents.append((file.filename, content))
        file.file.seek(0)  # reset for sync processing path

    if total_size > MAX_BATCH_TOTAL_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件总大小超过限制 ({MAX_BATCH_TOTAL_SIZE // (1024*1024)}MB)",
        )

    if len(files) < SYNC_THRESHOLD:
        return _process_batch_sync(ingestion, config, files)

    task_id = task_manager.create_task(total=len(files))

    def _run_async():
        from io import BytesIO
        wrapper_files = []
        for filename, content in file_contents:
            wrapper = UploadFile(filename=filename, file=BytesIO(content))
            wrapper_files.append(wrapper)
        _process_batch_async(ingestion, config, wrapper_files, task_id)

    threading.Thread(target=_run_async, daemon=True).start()

    return {
        "mode": "async",
        "task_id": task_id,
        "total": len(files),
        "message": f"批量上传任务已创建，请通过 /upload/batch/status/{task_id} 查询进度",
    }


@router.get("/upload/batch/status/{task_id}")
async def batch_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
):
    """查询批量上传任务进度。"""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.snapshot()


@router.get("/documents")
async def get_documents(
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(get_infra),
):
    """获取文档列表"""
    sources = infra.vector_store.get_all_sources()
    return {"documents": sources}


@router.get("/documents/overview")
async def get_documents_overview(
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(get_infra),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """一次返回文档列表 + 详情 + 统计（避免多次全量遍历）"""
    overview = infra.vector_store.get_overview()
    index_stats = ingestion.get_index_stats()

    details = []
    total_size = 0
    data_dir = config.DATA_DIR
    for item in overview["source_details"]:
        source = item["source"]
        file_path = os.path.join(data_dir, source)
        file_size = 0
        if os.path.isfile(file_path):
            try:
                file_size = os.path.getsize(file_path)
                total_size += file_size
            except OSError:
                pass
        ext = os.path.splitext(source)[1].lower().lstrip(".")
        details.append({
            "source": source,
            "chunks": item["chunks"],
            "file_size": file_size,
            "file_type": ext,
        })

    return {
        "documents": overview["sources"],
        "details": details,
        "stats": {
            "document_count": overview["document_count"],
            "source_count": len(overview["sources"]),
            "total_size": total_size,
            "indexed_documents": index_stats["indexed_documents"],
            "vector_count": index_stats["vector_count"],
            "bm25_ready": index_stats["bm25_ready"],
        },
    }


@router.get("/documents/detail")
async def get_document_details(
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(get_infra),
    config: AppSettings = Depends(get_settings),
):
    """获取文档详情（chunks 数量、文件大小、文件类型）"""
    source_details = infra.vector_store.get_source_details()
    documents = []
    for item in source_details:
        source = item["source"]
        file_path = os.path.join(config.DATA_DIR, source)
        file_size = 0
        if os.path.isfile(file_path):
            file_size = os.path.getsize(file_path)
        ext = os.path.splitext(source)[1].lower().lstrip(".")
        documents.append({
            "source": source,
            "chunks": item["chunks"],
            "file_size": file_size,
            "file_type": ext,
        })
    return {"documents": documents}


@router.delete("/documents/{source}")
async def delete_document(
    source: str,
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """删除单个文档及其向量"""
    # 防止路径穿越：只取文件名，丢弃路径分隔符
    safe_source = os.path.basename(source)
    if not safe_source:
        raise HTTPException(status_code=400, detail="无效的文件名")

    try:
        ingestion.delete_by_source(safe_source)

        # 同时删除磁盘文件
        file_path = os.path.join(config.DATA_DIR, safe_source)
        if os.path.exists(file_path):
            os.remove(file_path)

        return {"message": f"已删除文档: {safe_source}"}
    except Exception as e:
        logger.exception("删除文档失败: %s", source)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.delete("/documents")
async def clear_all_documents(
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """清空所有文档和向量"""
    try:
        ingestion.delete_all()

        # 清空数据目录
        if os.path.exists(config.DATA_DIR):
            shutil.rmtree(config.DATA_DIR)
            os.makedirs(config.DATA_DIR, exist_ok=True)

        return {"message": "已清空所有文档"}
    except Exception as e:
        logger.exception("清空文档失败")
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


@router.post("/documents/load")
async def load_documents(
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """批量加载本地文档（后台执行，通过 /documents/load/status 查询进度）"""
    if not os.path.exists(config.DATA_DIR):
        raise HTTPException(status_code=404, detail="数据目录不存在")

    files = [f for f in os.listdir(config.DATA_DIR) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]

    if not files:
        return {
            "message": "本地文档目录为空，请先上传文档",
            "files": [],
            "total_chunks": 0
        }

    if not _load_state.try_start(len(files)):
        raise HTTPException(status_code=409, detail="文档加载任务正在进行中")

    def _run():
        loaded_files = []
        total_chunks = 0
        for file in files:
            try:
                file_path = os.path.join(config.DATA_DIR, file)
                chunks = ingestion.ingest_document(file_path)
                total_chunks += chunks
                loaded_files.append(file)
            except Exception as e:
                logger.warning("加载文档失败 %s: %s", file, e)
            finally:
                _load_state.advance()

        _load_state.finish({
            "message": f"成功加载 {len(loaded_files)} 个文档",
            "files": loaded_files,
            "total_chunks": total_chunks,
        })

    threading.Thread(target=_run, daemon=True).start()

    return {
        "message": "文档加载任务已启动",
        "total": len(files),
    }


@router.get("/documents/load/status")
async def load_documents_status(current_user: dict = Depends(get_current_user)):
    """查询批量加载进度"""
    return _load_state.snapshot()


@router.post("/documents/sync")
async def sync_documents(
    current_user: dict = Depends(get_current_user),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """增量同步文档索引

    扫描数据目录，对比已索引文档的 Hash，
    只处理新增、修改、删除的文档。
    """
    if not os.path.exists(config.DATA_DIR):
        raise HTTPException(status_code=404, detail="数据目录不存在")

    try:
        result = ingestion.sync_index(config.DATA_DIR)
        return {
            "message": "同步完成",
            "result": result
        }
    except Exception as e:
        logger.exception("同步失败")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.get("/stats")
async def get_stats(
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(get_infra),
    ingestion: IngestionService = Depends(get_ingestion),
    config: AppSettings = Depends(get_settings),
):
    """获取统计信息"""
    doc_count = infra.vector_store.get_document_count()
    sources = infra.vector_store.get_all_sources()
    index_stats = ingestion.get_index_stats()

    # 计算 DATA_DIR 中所有已索引文件的总大小
    total_size = 0
    data_dir = config.DATA_DIR
    if os.path.isdir(data_dir):
        for source in sources:
            file_path = os.path.join(data_dir, source)
            try:
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
            except OSError:
                pass

    return {
        "document_count": doc_count,
        "source_count": len(sources),
        "total_size": total_size,
        "indexed_documents": index_stats["indexed_documents"],
        "vector_count": index_stats["vector_count"],
        "bm25_ready": index_stats["bm25_ready"],
    }
