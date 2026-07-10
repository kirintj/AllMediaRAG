"""评测报告与工程性能 API

GET /api/metrics           — 运行时性能指标（管线延迟、缓存命中率、请求统计）
GET /api/eval/reports      — 评测报告列表
GET /api/eval/reports/{fn} — 单个评测报告详情
"""

import json
import os
from pathlib import Path
from fastapi import APIRouter, Request, Depends, HTTPException
from core.auth import get_current_user
from core.services import InfraBundle
from api.deps import get_infra

router = APIRouter()

# 评测报告目录（相对于 backend）
EVAL_DIR = Path(__file__).parent.parent / "eval"


# ── /api/metrics ─────────────────────────────────────────────────────────

@router.get("/metrics")
async def get_metrics(
    current_user: dict = Depends(get_current_user),
    infra: InfraBundle = Depends(get_infra),
):
    """返回运行时工程性能指标"""
    collector = infra.metrics_collector
    return collector.get_stats()


# ── /api/eval/reports ────────────────────────────────────────────────────

@router.get("/eval/reports")
async def list_eval_reports(
    current_user: dict = Depends(get_current_user),
):
    """扫描 eval 目录，返回所有评测报告的摘要列表"""
    if not EVAL_DIR.exists():
        return {"reports": []}

    reports = []
    for f in sorted(EVAL_DIR.glob("report*.json"), key=os.path.getmtime, reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            reports.append({
                "filename": f.name,
                "framework": data.get("framework", "custom"),
                "total_samples": data.get("total_samples", 0),
                "metrics": {
                    "retrieval": data.get("retrieval", {}),
                    "generation": data.get("generation", {}),
                    "keyword_coverage": data.get("keyword_coverage"),
                },
                "modified": os.path.getmtime(f),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return {"reports": reports}


@router.get("/eval/reports/{filename}")
async def get_eval_report(
    filename: str,
    current_user: dict = Depends(get_current_user),
):
    """读取单个评测报告的完整内容"""
    # 安全检查：只允许读取 report*.json
    if not filename.startswith("report") or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="无效的报告文件名")

    filepath = EVAL_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="报告不存在")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data
