"""Knowledge base management API (知识库管理)

Provides CRUD endpoints for knowledge bases and their documents.
All endpoints require authentication via ``get_current_user``.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from core.auth import get_current_user
from core.db.engine import get_db_session
from core.db.tenant_models import Knowledgebase, KBDocument, UserTenant

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateKBRequest(BaseModel):
    name: str
    permission: str = "me"  # me / team
    language: str = "zh"
    description: str = ""


class UpdateKBRequest(BaseModel):
    name: str | None = None
    permission: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/knowledgebases")
async def list_knowledgebases(current_user: dict = Depends(get_current_user)):
    """List knowledge bases visible to the current user."""
    user_id = current_user["user_id"]

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "Database not available")

        # Collect all tenants the user belongs to
        tenant_ids = [
            str(r.tenant_id)
            for r in session.query(UserTenant)
            .filter(UserTenant.user_id == user_id)
            .all()
        ]

        kbs = (
            session.query(Knowledgebase)
            .filter(Knowledgebase.tenant_id.in_(tenant_ids))
            .all()
        )

        result = []
        for kb in kbs:
            # Permission filtering: team-visible or creator-only
            if kb.permission == "team" or str(kb.created_by) == user_id:
                doc_count = (
                    session.query(KBDocument)
                    .filter(KBDocument.kb_id == kb.id)
                    .count()
                )
                result.append({
                    "id": str(kb.id),
                    "name": kb.name,
                    "permission": kb.permission,
                    "language": kb.language,
                    "description": kb.description,
                    "document_count": doc_count,
                    "tenant_id": str(kb.tenant_id),
                    "created_at": kb.created_at.isoformat() if kb.created_at else None,
                })

        return {"knowledgebases": result}


@router.post("/knowledgebases")
async def create_knowledgebase(
    body: CreateKBRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new knowledge base."""
    tenant_id = current_user["tenant_id"]
    user_id = current_user["user_id"]

    kb = Knowledgebase(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(tenant_id),
        name=body.name,
        permission=body.permission,
        language=body.language,
        description=body.description,
        created_by=uuid.UUID(user_id),
    )

    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "Database not available")
        session.add(kb)
        session.commit()

    return {"message": "知识库创建成功", "id": str(kb.id), "name": kb.name}


@router.get("/knowledgebases/{kb_id}")
async def get_knowledgebase(
    kb_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get knowledge base details."""
    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "Database not available")

        try:
            kb_uuid = uuid.UUID(kb_id)
        except ValueError:
            raise HTTPException(400, "Invalid knowledge base ID")

        kb = session.query(Knowledgebase).get(kb_uuid)
        if not kb:
            raise HTTPException(404, "知识库不存在")

        doc_count = (
            session.query(KBDocument)
            .filter(KBDocument.kb_id == kb_uuid)
            .count()
        )
        return {
            "id": str(kb.id),
            "name": kb.name,
            "permission": kb.permission,
            "language": kb.language,
            "description": kb.description,
            "document_count": doc_count,
        }


@router.put("/knowledgebases/{kb_id}")
async def update_knowledgebase(
    kb_id: str,
    body: UpdateKBRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update knowledge base settings."""
    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "Database not available")

        try:
            kb_uuid = uuid.UUID(kb_id)
        except ValueError:
            raise HTTPException(400, "Invalid knowledge base ID")

        kb = session.query(Knowledgebase).get(kb_uuid)
        if not kb:
            raise HTTPException(404, "知识库不存在")

        if body.name is not None:
            kb.name = body.name
        if body.permission is not None:
            kb.permission = body.permission
        if body.description is not None:
            kb.description = body.description

        session.commit()

    return {"message": "知识库已更新"}


@router.delete("/knowledgebases/{kb_id}")
async def delete_knowledgebase(
    kb_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete a knowledge base (cascades to documents and vector data)."""
    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "Database not available")

        try:
            kb_uuid = uuid.UUID(kb_id)
        except ValueError:
            raise HTTPException(400, "Invalid knowledge base ID")

        kb = session.query(Knowledgebase).get(kb_uuid)
        if not kb:
            raise HTTPException(404, "知识库不存在")

        # Delete associated document records
        session.query(KBDocument).filter(KBDocument.kb_id == kb_uuid).delete()
        session.delete(kb)
        session.commit()

    # TODO: Clean up MinIO files and ES data
    return {"message": f"知识库已删除: {kb_id}"}


@router.get("/knowledgebases/{kb_id}/documents")
async def list_documents(
    kb_id: str,
    current_user: dict = Depends(get_current_user),
):
    """List documents in a knowledge base."""
    with get_db_session() as session:
        if session is None:
            raise HTTPException(503, "Database not available")

        try:
            kb_uuid = uuid.UUID(kb_id)
        except ValueError:
            raise HTTPException(400, "Invalid knowledge base ID")

        docs = (
            session.query(KBDocument)
            .filter(KBDocument.kb_id == kb_uuid)
            .all()
        )
        return {
            "documents": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "file_size": d.file_size,
                    "file_type": d.file_type,
                    "chunk_count": d.chunk_count,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in docs
            ]
        }
