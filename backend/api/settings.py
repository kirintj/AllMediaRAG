"""RAG 增强设置 API"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core.auth import get_current_user
from core.config import config

logger = logging.getLogger(__name__)
router = APIRouter()


class RagSettings(BaseModel):
    enable_auto_keywords: bool = False
    auto_keywords_topn: int = 5
    enable_auto_questions: bool = False
    auto_questions_topn: int = 3
    enable_metadata_extraction: bool = False
    enable_toc_extraction: bool = False
    enable_raptor: bool = False
    raptor_max_clusters: int = 64
    raptor_clustering_method: str = "gmm"
    enable_content_tagging: bool = False
    content_tag_topn: int = 3
    content_tag_kb_ids: str = ""
    graphrag_enabled: bool = False
    graphrag_method: str = "general"
    graphrag_enable_resolution: bool = True
    graphrag_enable_community: bool = True
    graphrag_pagerank_enabled: bool = True


@router.get("/settings/rag")
async def get_rag_settings(current_user: dict = Depends(get_current_user)):
    """读取 RAG 增强配置"""
    return RagSettings(
        enable_auto_keywords=getattr(config, 'ENABLE_AUTO_KEYWORDS', False),
        auto_keywords_topn=getattr(config, 'AUTO_KEYWORDS_TOPN', 5),
        enable_auto_questions=getattr(config, 'ENABLE_AUTO_QUESTIONS', False),
        auto_questions_topn=getattr(config, 'AUTO_QUESTIONS_TOPN', 3),
        enable_metadata_extraction=getattr(config, 'ENABLE_METADATA_EXTRACTION', False),
        enable_toc_extraction=getattr(config, 'ENABLE_TOC_EXTRACTION', False),
        enable_raptor=getattr(config, 'ENABLE_RAPTOR', False),
        raptor_max_clusters=getattr(config, 'RAPTOR_MAX_CLUSTERS', 64),
        raptor_clustering_method=getattr(config, 'RAPTOR_CLUSTERING_METHOD', 'gmm'),
        enable_content_tagging=getattr(config, 'ENABLE_CONTENT_TAGGING', False),
        content_tag_topn=getattr(config, 'CONTENT_TAG_TOPN', 3),
        content_tag_kb_ids=getattr(config, 'CONTENT_TAG_KB_IDS', ''),
        graphrag_enabled=getattr(config, 'GRAPHRAG_ENABLED', False),
        graphrag_method=getattr(config, 'GRAPHRAG_METHOD', 'general'),
        graphrag_enable_resolution=getattr(config, 'GRAPHRAG_ENABLE_RESOLUTION', True),
        graphrag_enable_community=getattr(config, 'GRAPHRAG_ENABLE_COMMUNITY', True),
        graphrag_pagerank_enabled=getattr(config, 'GRAPHRAG_PAGERANK_ENABLED', True),
    )


@router.put("/settings/rag")
async def update_rag_settings(
    settings: RagSettings,
    current_user: dict = Depends(get_current_user),
):
    """更新 RAG 增强配置（写入 .env 文件，重启后生效）"""
    import os
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")

    # 读取现有 .env
    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # 构建新值映射
    new_values = {
        "ENABLE_AUTO_KEYWORDS": str(settings.enable_auto_keywords).lower(),
        "AUTO_KEYWORDS_TOPN": str(settings.auto_keywords_topn),
        "ENABLE_AUTO_QUESTIONS": str(settings.enable_auto_questions).lower(),
        "AUTO_QUESTIONS_TOPN": str(settings.auto_questions_topn),
        "ENABLE_METADATA_EXTRACTION": str(settings.enable_metadata_extraction).lower(),
        "ENABLE_TOC_EXTRACTION": str(settings.enable_toc_extraction).lower(),
        "ENABLE_RAPTOR": str(settings.enable_raptor).lower(),
        "RAPTOR_MAX_CLUSTERS": str(settings.raptor_max_clusters),
        "RAPTOR_CLUSTERING_METHOD": settings.raptor_clustering_method,
        "ENABLE_CONTENT_TAGGING": str(settings.enable_content_tagging).lower(),
        "CONTENT_TAG_TOPN": str(settings.content_tag_topn),
        "CONTENT_TAG_KB_IDS": settings.content_tag_kb_ids,
        "GRAPHRAG_ENABLED": str(settings.graphrag_enabled).lower(),
        "GRAPHRAG_METHOD": settings.graphrag_method,
        "GRAPHRAG_ENABLE_RESOLUTION": str(settings.graphrag_enable_resolution).lower(),
        "GRAPHRAG_ENABLE_COMMUNITY": str(settings.graphrag_enable_community).lower(),
        "GRAPHRAG_PAGERANK_ENABLED": str(settings.graphrag_pagerank_enabled).lower(),
    }

    # 更新或追加
    updated_keys: set[str] = set()
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line else ""
        if key in new_values:
            new_lines.append(f"{key}={new_values[key]}\n")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in new_values.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return {"message": "配置已保存，重启后生效", "settings": settings.dict()}
