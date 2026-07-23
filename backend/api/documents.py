import os
import logging
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from core.rate_limit import limiter, RATE_LIMIT_UPLOAD, RATE_LIMIT_BATCH_UPLOAD
from core.auth import get_current_user
from core.config import AppSettings
from core.services import InfraBundle
from core.services.ingestion_service import IngestionService
from core.task_queue import TaskQueue, TaskMessage, gen_task_id, gen_batch_id
from api.deps import get_settings, get_infra, get_ingestion, get_task_queue

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

router = APIRouter()


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
    queue: TaskQueue = Depends(get_task_queue),
):
    """上传文档（同名文件自动去重，异步处理）"""
    safe_name = os.path.basename(file.filename)
    _validate_upload_file(file, safe_name)

    try:
        content = await file.read()

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

        # 入队
        task_id = gen_task_id()
        msg = TaskMessage(
            task_id=task_id,
            batch_id=task_id,  # 单文件，batch_id = task_id
            file_path=file_path,
            source=safe_name,
            user_id=current_user.get("id", "anonymous"),
        )
        queue.enqueue(msg, priority="high")

        return {
            "message": "上传成功，正在处理",
            "filename": safe_name,
            "task_id": task_id,
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
    queue: TaskQueue = Depends(get_task_queue),
):
    """批量上传文档（全部异步处理）"""
    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"最多上传 {MAX_BATCH_FILES} 个文件",
        )

    total_size = 0
    file_contents = []
    for file in files:
        content = await file.read()
        total_size += len(content)
        file_contents.append((file.filename, content))

    if total_size > MAX_BATCH_TOTAL_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件总大小超过限制 ({MAX_BATCH_TOTAL_SIZE // (1024*1024)}MB)",
        )

    os.makedirs(config.DATA_DIR, exist_ok=True)
    batch_id = gen_batch_id()
    messages = []

    for filename, content in file_contents:
        safe_name = os.path.basename(filename)
        if not safe_name or len(safe_name) > MAX_FILENAME_LENGTH:
            continue

        ext = os.path.splitext(safe_name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        if len(content) > MAX_FILE_SIZE:
            continue

        file_path = os.path.join(config.DATA_DIR, safe_name)
        ingestion.delete_by_source(safe_name)
        with open(file_path, "wb") as f:
            f.write(content)

        messages.append(TaskMessage(
            task_id=gen_task_id(),
            batch_id=batch_id,
            file_path=file_path,
            source=safe_name,
            user_id=current_user.get("id", "anonymous"),
        ))

    if not messages:
        raise HTTPException(status_code=400, detail="没有有效的文件可处理")

    returned_batch_id, task_ids = queue.enqueue_batch(messages)

    return {
        "message": f"已提交 {len(messages)} 个文件",
        "batch_id": returned_batch_id,
        "task_ids": task_ids,
    }


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """查询单个任务状态"""
    state = queue.get_state(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="任务不存在")
    return state.to_dict()


@router.get("/batches/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: dict = Depends(get_current_user),
    queue: TaskQueue = Depends(get_task_queue),
):
    """查询批次聚合状态"""
    state = queue.get_batch_state(batch_id)
    if not state:
        raise HTTPException(status_code=404, detail="批次不存在")
    return state


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
    config: AppSettings = Depends(get_settings),
    queue: TaskQueue = Depends(get_task_queue),
):
    """批量加载本地文档（异步入队）"""
    if not os.path.exists(config.DATA_DIR):
        raise HTTPException(status_code=404, detail="数据目录不存在")

    files = [f for f in os.listdir(config.DATA_DIR) if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]

    if not files:
        return {"message": "本地文档目录为空，请先上传文档", "files": [], "total": 0}

    batch_id = gen_batch_id()
    messages = []
    for filename in files:
        file_path = os.path.join(config.DATA_DIR, filename)
        messages.append(TaskMessage(
            task_id=gen_task_id(),
            batch_id=batch_id,
            file_path=file_path,
            source=filename,
            user_id=current_user.get("id", "anonymous"),
        ))

    returned_batch_id, task_ids = queue.enqueue_batch(messages)

    return {
        "message": f"已提交 {len(messages)} 个文档加载任务",
        "batch_id": returned_batch_id,
        "total": len(messages),
    }


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
