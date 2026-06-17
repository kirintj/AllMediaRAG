#!/usr/bin/env python3
"""
迁移 JSON 数据到 PostgreSQL
"""
import sys
import os
import json
import glob

script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
project_dir = os.path.dirname(backend_dir)

sys.path.insert(0, project_dir)
sys.path.insert(0, backend_dir)
os.chdir(project_dir)

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import config
from core.db.user_models import UserModel, ConversationModel, MessageModel

def main():
    print("=" * 60)
    print("迁移 JSON 数据到 PostgreSQL")
    print("=" * 60)

    engine = create_engine(config.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. 迁移用户数据
    print("\n[1/2] 迁移用户数据...")
    users_file = "data/users.json"

    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            users_data = json.load(f)

        migrated = 0
        skipped = 0

        for username, user_info in users_data.items():
            existing = session.query(UserModel).filter_by(username=username).first()
            if existing:
                skipped += 1
                continue

            user = UserModel(
                username=username,
                password_hash=user_info.get('password_hash', ''),
                created_at=datetime.fromtimestamp(user_info.get('created_at', 0)),
            )
            session.add(user)
            migrated += 1

        session.commit()
        print(f"[OK] 用户: 迁移 {migrated} 个, 跳过 {skipped} 个已存在")
    else:
        print("[INFO] users.json 不存在，跳过")

    # 2. 迁移对话数据
    print("\n[2/2] 迁移对话数据...")
    conversations_dir = "data/conversations"

    if os.path.exists(conversations_dir):
        json_files = glob.glob(os.path.join(conversations_dir, "*.json"))

        migrated = 0
        skipped = 0
        errors = 0

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    conv_data = json.load(f)

                conv_id = conv_data.get('id')

                # 检查是否已存在
                existing = session.query(ConversationModel).filter_by(title=conv_data.get('title', '')).first()
                if existing:
                    skipped += 1
                    continue

                # 获取第一个用户（如果没有用户则跳过）
                user = session.query(UserModel).first()
                if not user:
                    print("[WARN] 没有用户，无法迁移对话")
                    break

                # 创建对话
                conversation = ConversationModel(
                    user_id=user.id,
                    title=conv_data.get('title', '未命名对话'),
                    mode=conv_data.get('mode', 'rag'),
                    created_at=datetime.fromtimestamp(conv_data.get('created_at', 0)),
                    updated_at=datetime.fromtimestamp(conv_data.get('updated_at', 0)),
                )
                session.add(conversation)
                session.flush()  # 获取 conversation.id

                # 创建消息
                for msg in conv_data.get('messages', []):
                    message = MessageModel(
                        conversation_id=conversation.id,
                        role=msg.get('role', 'user'),
                        content=msg.get('content', ''),
                        sources=msg.get('sources'),
                        created_at=datetime.fromtimestamp(conv_data.get('created_at', 0)),
                    )
                    session.add(message)

                migrated += 1

            except Exception as e:
                errors += 1
                print(f"[ERROR] 迁移失败 {json_file}: {e}")

        session.commit()
        print(f"[OK] 对话: 迁移 {migrated} 个, 跳过 {skipped} 个, 错误 {errors} 个")
    else:
        print("[INFO] conversations/ 不存在，跳过")

    session.close()
    engine.dispose()

    print("\n" + "=" * 60)
    print("[OK] 数据迁移完成!")
    print("=" * 60)
    print("\n存储方案:")
    print("  - 用户/对话: PostgreSQL")
    print("  - 向量存储: ChromaDB")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
