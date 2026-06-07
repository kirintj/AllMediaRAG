import os
import re
import logging
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from core.rate_limit import limiter, RATE_LIMIT_UPLOAD
from core.auth import get_current_user

logger = logging.getLogger(__name__)

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
}

router = APIRouter()

# 共享引擎实例（由 main.py 注入）
_engine = None
_config = None


def set_engine(engine, config):
    """由 main.py 调用，注入共享引擎实例"""
    global _engine, _config
    _engine = engine
    _config = config


def get_engine_and_config():
    if _engine is None:
        raise RuntimeError("RAG engine not initialized. Call set_engine() first.")
    return _engine, _config

@router.post("/upload")
@limiter.limit(RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """上传文档（同名文件自动去重）"""
    engine, config = get_engine_and_config()

    supported_types = [".html", ".htm", ".txt", ".md", ".pdf", ".docx"]
    # 防止路径遍历：只取文件名，丢弃路径分隔符
    safe_name = os.path.basename(file.filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="文件名为空")

    if len(safe_name) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=400, detail=f"文件名过长，最大 {MAX_FILENAME_LENGTH} 字符")

    ext = os.path.splitext(safe_name)[1].lower()

    if ext not in supported_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，支持: {', '.join(supported_types)}")

    # MIME type 校验（与扩展名双重验证）
    if file.content_type:
        allowed_mimes = ALLOWED_MIME_TYPES.get(ext, [])
        if allowed_mimes and file.content_type not in allowed_mimes:
            logger.warning("MIME 类型不匹配: filename=%s, content_type=%s, ext=%s", safe_name, file.content_type, ext)
            raise HTTPException(status_code=400, detail=f"文件类型不匹配，期望 {ext} 格式")

    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        file_path = os.path.join(config.DATA_DIR, safe_name)

        # 同名文件去重：先删除旧向量
        engine.delete_by_source(safe_name)

        content = await file.read()

        # 文件大小校验
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"文件过大，最大允许 {MAX_FILE_SIZE // (1024*1024)}MB")

        with open(file_path, "wb") as f:
            f.write(content)

        chunks = engine.ingest_document(file_path)

        return {
            "message": "上传成功",
            "filename": safe_name,
            "chunks": chunks
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("文档上传失败")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.get("/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    """获取文档列表"""
    engine, _ = get_engine_and_config()
    sources = engine.vector_store.get_all_sources()
    return {"documents": sources}

@router.delete("/documents/{source}")
async def delete_document(source: str, current_user: dict = Depends(get_current_user)):
    """删除单个文档及其向量"""
    engine, config = get_engine_and_config()

    # 防止路径穿越：只取文件名，丢弃路径分隔符
    safe_source = os.path.basename(source)
    if not safe_source:
        raise HTTPException(status_code=400, detail="无效的文件名")

    try:
        engine.delete_by_source(safe_source)

        # 同时删除磁盘文件
        file_path = os.path.join(config.DATA_DIR, safe_source)
        if os.path.exists(file_path):
            os.remove(file_path)

        return {"message": f"已删除文档: {safe_source}"}
    except Exception as e:
        logger.exception("删除文档失败: %s", source)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.delete("/documents")
async def clear_all_documents(current_user: dict = Depends(get_current_user)):
    """清空所有文档和向量"""
    engine, config = get_engine_and_config()

    try:
        engine.delete_all()

        # 清空数据目录
        if os.path.exists(config.DATA_DIR):
            shutil.rmtree(config.DATA_DIR)
            os.makedirs(config.DATA_DIR, exist_ok=True)

        return {"message": "已清空所有文档"}
    except Exception as e:
        logger.exception("清空文档失败")
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")

@router.post("/documents/load")
async def load_documents(current_user: dict = Depends(get_current_user)):
    """批量加载本地文档"""
    engine, config = get_engine_and_config()

    if not os.path.exists(config.DATA_DIR):
        raise HTTPException(status_code=404, detail="数据目录不存在")

    files = [f for f in os.listdir(config.DATA_DIR) if f.endswith((".html", ".htm", ".txt", ".md", ".pdf", ".docx"))]

    if not files:
        raise HTTPException(status_code=404, detail="未找到可处理的文档")

    total_chunks = 0
    loaded_files = []

    for file in files:
        file_path = os.path.join(config.DATA_DIR, file)
        chunks = engine.ingest_document(file_path)
        total_chunks += chunks
        loaded_files.append(file)

    return {
        "message": f"成功加载 {len(loaded_files)} 个文档",
        "files": loaded_files,
        "total_chunks": total_chunks
    }

@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """获取统计信息"""
    engine, _ = get_engine_and_config()
    doc_count = engine.vector_store.get_document_count()
    sources = engine.vector_store.get_all_sources()
    return {
        "document_count": doc_count,
        "source_count": len(sources)
    }
