import os
import logging
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException

logger = logging.getLogger(__name__)

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
async def upload_document(file: UploadFile = File(...)):
    """上传文档（同名文件自动去重）"""
    engine, config = get_engine_and_config()

    supported_types = [".html", ".htm", ".txt", ".md", ".pdf", ".docx"]
    # 防止路径遍历：只取文件名，丢弃路径分隔符
    safe_name = os.path.basename(file.filename)
    if not safe_name:
        raise HTTPException(status_code=400, detail="文件名为空")

    ext = os.path.splitext(safe_name)[1].lower()

    if ext not in supported_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式，支持: {', '.join(supported_types)}")

    try:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        file_path = os.path.join(config.DATA_DIR, safe_name)

        # 同名文件去重：先删除旧向量
        engine.delete_by_source(safe_name)

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        chunks = engine.ingest_document(file_path)

        return {
            "message": "上传成功",
            "filename": safe_name,
            "chunks": chunks
        }

    except Exception as e:
        logger.exception("文档上传失败")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@router.get("/documents")
async def get_documents():
    """获取文档列表"""
    engine, _ = get_engine_and_config()
    sources = engine.vector_store.get_all_sources()
    return {"documents": sources}

@router.delete("/documents/{source}")
async def delete_document(source: str):
    """删除单个文档及其向量"""
    engine, config = get_engine_and_config()

    try:
        engine.delete_by_source(source)

        # 同时删除磁盘文件
        file_path = os.path.join(config.DATA_DIR, source)
        if os.path.exists(file_path):
            os.remove(file_path)

        return {"message": f"已删除文档: {source}"}
    except Exception as e:
        logger.exception("删除文档失败: %s", source)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.delete("/documents")
async def clear_all_documents():
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
async def load_documents():
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
async def get_stats():
    """获取统计信息"""
    engine, _ = get_engine_and_config()
    doc_count = engine.vector_store.get_document_count()
    sources = engine.vector_store.get_all_sources()
    return {
        "document_count": doc_count,
        "source_count": len(sources)
    }
