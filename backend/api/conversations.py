import os
import re
import json
import time
import logging
from fastapi import APIRouter, HTTPException, Depends
from core.auth import get_current_user

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


def _get_user_dir(username: str) -> str:
    """获取用户专属对话目录"""
    conv_dir = get_conversations_dir()
    user_dir = os.path.join(conv_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def _list_user(username: str) -> list:
    """读取指定用户的所有对话元信息"""
    user_dir = _get_user_dir(username)
    conversations = []
    for fname in os.listdir(user_dir):
        if fname.endswith(".json"):
            try:
                with open(os.path.join(user_dir, fname), "r", encoding="utf-8") as f:
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


def save_conversation(conv_id, username, title, messages, mode):
    """保存对话（由 chat.py 调用）

    Args:
        conv_id: 对话 ID
        username: 所属用户名
        title: 对话标题
        messages: 消息列表
        mode: 对话模式
    """
    user_dir = _get_user_dir(username)
    path = os.path.join(user_dir, f"{conv_id}.json")
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
            "username": username,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "mode": mode,
            "messages": messages,
        }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


# conv_id 校验正则：仅允许字母数字、下划线、短横线
_CONV_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _validate_conv_id(conv_id: str) -> str:
    """校验对话 ID，防止路径遍历"""
    if not _CONV_ID_PATTERN.match(conv_id):
        raise HTTPException(status_code=400, detail="无效的对话 ID，仅允许字母、数字、下划线和短横线")
    return conv_id


@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """获取当前用户的对话列表"""
    return {"conversations": _list_user(current_user["username"])}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    """获取单个对话详情（仅限本人）"""
    _validate_conv_id(conv_id)
    user_dir = _get_user_dir(current_user["username"])
    path = os.path.join(user_dir, f"{conv_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="对话不存在")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.delete("/conversations")
async def clear_all_conversations(current_user: dict = Depends(get_current_user)):
    """清空当前用户的所有对话"""
    user_dir = _get_user_dir(current_user["username"])
    count = 0
    for fname in os.listdir(user_dir):
        if fname.endswith(".json"):
            os.remove(os.path.join(user_dir, fname))
            count += 1
    return {"message": f"已清空 {count} 条对话"}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    """删除对话（仅限本人）"""
    _validate_conv_id(conv_id)
    user_dir = _get_user_dir(current_user["username"])
    path = os.path.join(user_dir, f"{conv_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return {"message": "已删除对话"}
    raise HTTPException(status_code=404, detail="对话不存在")
