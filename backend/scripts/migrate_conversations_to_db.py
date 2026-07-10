"""JSON → PostgreSQL 数据迁移脚本。

将 users.json 和 conversations/ 目录下的数据导入数据库。
用法：
    python -m scripts.migrate_conversations_to_db          # 正式执行
    python -m scripts.migrate_conversations_to_db --dry-run # 仅预览
"""
import argparse
import json
import os
import sys
import time
import uuid

# 确保能导入 backend 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.config import config
from core.db.engine import get_engine, get_session_factory
from core.db.user_models import UserModel, ConversationModel, MessageModel
from core.db.base import Base
from core.auth import hash_password


def _find_json_files():
    """定位 users.json 和 conversations/ 目录"""
    data_parent = os.path.dirname(config.DATA_DIR)
    users_file = os.path.join(data_parent, "users.json")
    conv_dir = os.path.join(data_parent, "conversations")
    return users_file, conv_dir


def _ensure_tables(engine):
    """确保表结构存在"""
    Base.metadata.create_all(engine)


def migrate_users(session, users_file, dry_run=False):
    """迁移用户数据"""
    if not os.path.exists(users_file):
        print(f"[跳过] 用户文件不存在: {users_file}")
        return 0

    with open(users_file, "r", encoding="utf-8") as f:
        users_data = json.load(f)

    count = 0
    for username, info in users_data.items():
        existing = session.query(UserModel).filter_by(username=username).first()
        if existing:
            print(f"  [已存在] 用户: {username}")
            continue

        user = UserModel(
            username=username,
            password_hash=info.get("password_hash", ""),
            email=info.get("email"),
        )
        session.add(user)
        count += 1
        print(f"  [迁移] 用户: {username}")

    if not dry_run:
        session.commit()
    return count


def migrate_conversations(session, conv_dir, dry_run=False):
    """迁移对话数据"""
    if not os.path.exists(conv_dir):
        print(f"[跳过] 对话目录不存在: {conv_dir}")
        return 0, 0

    conv_count = 0
    msg_count = 0

    for username in os.listdir(conv_dir):
        user_dir = os.path.join(conv_dir, username)
        if not os.path.isdir(user_dir):
            continue

        # 确保用户在 DB 中存在
        user = session.query(UserModel).filter_by(username=username).first()
        if user is None:
            user = UserModel(username=username, password_hash=hash_password("placeholder"))
            session.add(user)
            session.flush()
            print(f"  [新建] 用户: {username}（占位密码，请手动重置）")

        for fname in os.listdir(user_dir):
            if not fname.endswith(".json"):
                continue
            with open(os.path.join(user_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)

            conv_id_str = data.get("id", fname.replace(".json", ""))
            try:
                conv_uuid = uuid.UUID(conv_id_str)
            except ValueError:
                conv_uuid = uuid.uuid4()

            existing = session.query(ConversationModel).filter_by(id=conv_uuid).first()
            if existing:
                print(f"  [已存在] 对话: {conv_id_str}")
                continue

            conv = ConversationModel(
                id=conv_uuid,
                user_id=user.id,
                title=data.get("title", "新对话"),
                mode=data.get("mode", "rag"),
            )
            session.add(conv)
            session.flush()

            for m in data.get("messages", []):
                msg = MessageModel(
                    conversation_id=conv.id,
                    role=m.get("role", "user"),
                    content=m.get("content", ""),
                    sources=m.get("sources"),
                    extra_metadata=m.get("metadata") or m.get("verification"),
                )
                session.add(msg)
                msg_count += 1

            conv_count += 1
            print(f"  [迁移] 对话: {conv_id_str} ({len(data.get('messages', []))} 条消息)")

    if not dry_run:
        session.commit()
    return conv_count, msg_count


def main():
    parser = argparse.ArgumentParser(description="JSON → PostgreSQL 数据迁移")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入数据库")
    args = parser.parse_args()

    engine = get_engine()
    if engine is None:
        print("[错误] 数据库引擎不可用，请检查 DATABASE_URL 配置")
        sys.exit(1)

    _ensure_tables(engine)
    session = get_session_factory()()

    users_file, conv_dir = _find_json_files()
    print(f"数据源: users={users_file}, conversations={conv_dir}")
    print(f"模式: {'预览' if args.dry_run else '正式执行'}")
    print()

    print("=== 迁移用户 ===")
    user_count = migrate_users(session, users_file, dry_run=args.dry_run)
    print(f"用户迁移完成: {user_count} 条\n")

    print("=== 迁移对话 ===")
    conv_count, msg_count = migrate_conversations(session, conv_dir, dry_run=args.dry_run)
    print(f"对话迁移完成: {conv_count} 条对话, {msg_count} 条消息\n")

    if args.dry_run:
        print("[预览模式] 未实际写入数据库，以上为预期变更。")
    else:
        print("[完成] 数据已写入数据库。")

    session.close()


if __name__ == "__main__":
    main()
