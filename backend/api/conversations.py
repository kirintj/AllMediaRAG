"""对话管理 API。

存储策略：优先使用 PostgreSQL（ConversationModel / MessageModel），
数据库不可用时降级到 JSON 文件。
"""
import os
import re
import json
import time
import secrets
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from core.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# conv_id 校验正则：仅允许字母数字、下划线、短横线
_CONV_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None


def _validate_conv_id(conv_id: str) -> str:
    """校验对话 ID，防止路径遍历"""
    if not _CONV_ID_PATTERN.match(conv_id):
        raise HTTPException(status_code=400, detail="无效的对话 ID，仅允许字母、数字、下划线和短横线")
    return conv_id


# ---------------------------------------------------------------------------
# JSON 文件降级存储
# ---------------------------------------------------------------------------
_conversations_dir: Optional[str] = None


def _get_conversations_dir() -> str:
    global _conversations_dir
    if _conversations_dir is None:
        from core.config import config
        _conversations_dir = os.path.join(os.path.dirname(config.DATA_DIR), "conversations")
    os.makedirs(_conversations_dir, exist_ok=True)
    return _conversations_dir


def _get_user_dir(username: str) -> str:
    conv_dir = _get_conversations_dir()
    user_dir = os.path.join(conv_dir, username)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def _list_user_json(username: str) -> list:
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
                logger.warning("跳过损坏的对话文件: %s", fname)
                continue
    conversations.sort(key=lambda x: x["updated_at"], reverse=True)
    return conversations


def _get_conversation_json(conv_id: str, username: str) -> Optional[dict]:
    user_dir = _get_user_dir(username)
    path = os.path.join(user_dir, f"{conv_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_conversation_json(conv_id, username, title, messages, mode):
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
            "id": conv_id, "username": username, "title": title,
            "created_at": now, "updated_at": now, "mode": mode,
            "messages": messages,
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def _delete_conversation_json(conv_id: str, username: str) -> bool:
    user_dir = _get_user_dir(username)
    path = os.path.join(user_dir, f"{conv_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def _clear_conversations_json(username: str) -> int:
    user_dir = _get_user_dir(username)
    count = 0
    for fname in os.listdir(user_dir):
        if fname.endswith(".json"):
            os.remove(os.path.join(user_dir, fname))
            count += 1
    return count


# ---------------------------------------------------------------------------
# 辅助：获取 DB 可用的 user_id，不可用时返回 None
# ---------------------------------------------------------------------------

def _get_user_id(db, username: str):
    """通过用户名查找 user_id，DB 不可用或用户不存在返回 None"""
    from core.db.crud import get_user_by_username
    user = get_user_by_username(db, username)
    return user.id if user else None


# ---------------------------------------------------------------------------
# 公共接口：save_conversation（供 chat.py 调用）
# ---------------------------------------------------------------------------

def save_conversation(conv_id, username, title, messages, mode):
    """保存对话。数据库可用时写入 DB，否则降级到 JSON 文件。"""
    from core.db.engine import get_db_session
    from core.db.crud import save_conversation_db, get_or_create_user_by_username

    with get_db_session() as db:
        if db is not None:
            try:
                # 确保用户存在于 DB（JSON 迁移后可能尚未同步）
                user = get_or_create_user_by_username(db, username)
                save_conversation_db(db, conv_id, user.id, title, messages, mode)
                logger.debug("对话保存(DB): conv_id=%s", conv_id)
                return
            except Exception as e:
                logger.warning("对话保存 DB 失败，降级到 JSON: %s", e)

    # 降级到 JSON
    data = _save_conversation_json(conv_id, username, title, messages, mode)
    logger.debug("对话保存(JSON): conv_id=%s", conv_id)
    return data


# ---------------------------------------------------------------------------
# API 端点
# ---------------------------------------------------------------------------

@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """获取当前用户的对话列表"""
    username = current_user["username"]

    from core.db.engine import get_db_session
    from core.db.crud import list_conversations_by_user, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                return {"conversations": list_conversations_by_user(db, user.id)}

    return {"conversations": _list_user_json(username)}


@router.get("/conversations/{conv_id}")
async def get_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    """获取单个对话详情"""
    _validate_conv_id(conv_id)
    username = current_user["username"]

    from core.db.engine import get_db_session
    from core.db.crud import get_conversation_by_id, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                data = get_conversation_by_id(db, conv_id, user.id)
                if data is not None:
                    return data
                raise HTTPException(status_code=404, detail="对话不存在")

    data = _get_conversation_json(conv_id, username)
    if data is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    return data


@router.delete("/conversations")
async def clear_all_conversations(current_user: dict = Depends(get_current_user)):
    """清空当前用户的所有对话"""
    username = current_user["username"]

    from core.db.engine import get_db_session
    from core.db.crud import clear_conversations_db, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                count = clear_conversations_db(db, user.id)
                return {"message": f"已清空 {count} 条对话"}

    count = _clear_conversations_json(username)
    return {"message": f"已清空 {count} 条对话"}


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    """删除对话"""
    _validate_conv_id(conv_id)
    username = current_user["username"]

    from core.db.engine import get_db_session
    from core.db.crud import delete_conversation_db, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                ok = delete_conversation_db(db, conv_id, user.id)
                if ok:
                    return {"message": "已删除对话"}
                raise HTTPException(status_code=404, detail="对话不存在")

    ok = _delete_conversation_json(conv_id, username)
    if ok:
        return {"message": "已删除对话"}
    raise HTTPException(status_code=404, detail="对话不存在")


@router.patch("/conversations/{conv_id}")
async def update_conversation(
    conv_id: str,
    body: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
):
    """部分更新对话（重命名、收藏、归档）"""
    _validate_conv_id(conv_id)
    username = current_user["username"]

    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="没有要更新的字段")

    from core.db.engine import get_db_session
    from core.db.crud import update_conversation_fields, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                result = update_conversation_fields(db, conv_id, user.id, **fields)
                if result:
                    return result
                raise HTTPException(status_code=404, detail="对话不存在")

    # JSON 降级：只支持 title 和 is_favorite
    data = _get_conversation_json(conv_id, username)
    if data is None:
        raise HTTPException(status_code=404, detail="对话不存在")
    if "title" in fields:
        data["title"] = fields["title"]
    if "is_favorite" in fields:
        data["is_favorite"] = fields["is_favorite"]
    if "is_archived" in fields:
        data["is_archived"] = fields["is_archived"]
    data["updated_at"] = time.time()
    user_dir = _get_user_dir(username)
    path = os.path.join(user_dir, f"{conv_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {
        "id": data["id"],
        "title": data.get("title", "新对话"),
        "is_favorite": data.get("is_favorite", False),
        "is_archived": data.get("is_archived", False),
        "updated_at": data["updated_at"],
    }


@router.post("/conversations/{conv_id}/duplicate")
async def duplicate_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    """复制对话"""
    _validate_conv_id(conv_id)
    username = current_user["username"]

    from core.db.engine import get_db_session
    from core.db.crud import duplicate_conversation_db, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                result = duplicate_conversation_db(db, conv_id, user.id)
                if result:
                    return result
                raise HTTPException(status_code=404, detail="对话不存在")

    # JSON 降级
    data = _get_conversation_json(conv_id, username)
    if data is None:
        raise HTTPException(status_code=404, detail="对话不存在")

    import uuid as _uuid
    new_id = str(_uuid.uuid4())[:8]
    new_data = {
        "id": new_id,
        "username": username,
        "title": f"{data.get('title', '新对话')} (副本)",
        "created_at": time.time(),
        "updated_at": time.time(),
        "mode": data.get("mode", "rag"),
        "messages": data.get("messages", []),
    }
    user_dir = _get_user_dir(username)
    path = os.path.join(user_dir, f"{new_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    return {
        "id": new_id,
        "title": new_data["title"],
        "created_at": new_data["created_at"],
        "updated_at": new_data["updated_at"],
        "message_count": len(new_data["messages"]),
    }


@router.post("/conversations/{conv_id}/share")
async def share_conversation(conv_id: str, current_user: dict = Depends(get_current_user)):
    """生成分享链接"""
    _validate_conv_id(conv_id)
    username = current_user["username"]

    from core.db.engine import get_db_session
    from core.db.crud import share_conversation_db, get_user_by_username
    with get_db_session() as db:
        if db is not None:
            user = get_user_by_username(db, username)
            if user:
                result = share_conversation_db(db, conv_id, user.id)
                if result:
                    return result
                raise HTTPException(status_code=404, detail="对话不存在")

    # JSON 降级：生成 token 并写入文件
    data = _get_conversation_json(conv_id, username)
    if data is None:
        raise HTTPException(status_code=404, detail="对话不存在")

    if not data.get("shared_token"):
        data["shared_token"] = secrets.token_urlsafe(32)
        data["updated_at"] = time.time()
        user_dir = _get_user_dir(username)
        path = os.path.join(user_dir, f"{conv_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "id": data["id"],
        "shared_token": data["shared_token"],
        "share_url": f"/share/{data['shared_token']}",
    }
