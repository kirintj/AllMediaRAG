"""Tag Knowledge Base API routes."""
from __future__ import annotations

import os
import logging
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from core.auth import get_current_user
from core.tag_kb import TagKBManager

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_tag_kb_manager(request: Request) -> TagKBManager:
    infra = request.app.state.infra
    return TagKBManager(infra.vector_store)


def _get_settings(request: Request):
    return request.app.state.config


@router.post("/tag-kb/upload")
async def upload_tag_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    tag_kb_manager: TagKBManager = Depends(_get_tag_kb_manager),
    settings=Depends(_get_settings),
):
    """Upload a tag file (Excel/CSV) to create a tag knowledge base."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".xlsx", ".csv"):
        raise HTTPException(400, "Only .xlsx and .csv formats are supported")

    # Save temp file
    data_dir = settings.DATA_DIR
    os.makedirs(data_dir, exist_ok=True)
    tag_kb_id = f"tag_kb_{uuid.uuid4().hex[:8]}"
    file_path = os.path.join(data_dir, f"{tag_kb_id}{ext}")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        count = tag_kb_manager.ingest_tag_file(file_path, tag_kb_id)
        return {
            "message": "Tag knowledge base created successfully",
            "tag_kb_id": tag_kb_id,
            "tag_count": count,
        }
    except Exception as e:
        logger.exception("Tag KB creation failed")
        raise HTTPException(500, f"Creation failed: {e}")


@router.get("/tag-kb")
async def list_tag_kbs(
    current_user: dict = Depends(get_current_user),
    tag_kb_manager: TagKBManager = Depends(_get_tag_kb_manager),
):
    """List all tag knowledge bases."""
    return {"tag_kbs": tag_kb_manager.list_tag_kbs()}


@router.delete("/tag-kb/{tag_kb_id}")
async def delete_tag_kb(
    tag_kb_id: str,
    current_user: dict = Depends(get_current_user),
    tag_kb_manager: TagKBManager = Depends(_get_tag_kb_manager),
):
    """Delete a tag knowledge base."""
    tag_kb_manager.delete_tag_kb(tag_kb_id)
    return {"message": f"Tag KB {tag_kb_id} deleted"}


@router.get("/tag-kb/{tag_kb_id}/tags")
async def get_tags(
    tag_kb_id: str,
    current_user: dict = Depends(get_current_user),
    tag_kb_manager: TagKBManager = Depends(_get_tag_kb_manager),
):
    """Get the tag set for a tag knowledge base."""
    tags = tag_kb_manager.get_all_tags(tag_kb_id)
    return {"tags": tags}
