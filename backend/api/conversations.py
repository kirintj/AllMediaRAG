import os
import json
import time
import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

_conversations_dir = None

def get_conversations_dir():
    global _conversations_dir
    if _conversations_dir is None:
        from core.config import config
        _conversations_dir = os.path.join(os.path.dirname(config.DATA_DIR), "conversations")
    os.makedirs(_conversations_dir, exist_ok=True)
    return _conversations_dir


def _list_all():
    """读取所有对话元信息"""
    conv_dir = get_conversations_dir()
    conversations = []
    for fname in os.listdir(conv_dir):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(conv_dir, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "title": data["title"],
                    "created_at": data["created_at"],
                    "updated_at": data.get("updated_at", data["created_at"]),
                    "message_count": len(data.get("messages", [])),
                })
            except Exception:
                continue
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    return conversations


def save_conversation(conv_id, title, messages, mode):
    """保存对话（由 chat.py 调用）"""
    conv_dir = get_conversations_dir()
    path = os.path.join(conv_dir, f"{conv_id}.json")
    now = time.time()

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["messages"] = messages
        data["updated_at"] = now
        data["mode"] = mode
    else:
        data = {
            "id": conv_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "mode": mode,
            "messages": messages,
        }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


@router.get("/conversations")
async def list_conversations():
    """获取对话列表"""
    return {"conversations": _list_all()}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    """获取单个对话详情"""
    conv_dir = get_conversations_dir()
    path = os.path.join(conv_dir, f"{conv_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="对话不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除对话"""
    conv_dir = get_conversations_dir()
    path = os.path.join(conv_dir, f"{conv_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return {"message": "已删除对话"}
    raise HTTPException(status_code=404, detail="对话不存在")
