#!/usr/bin/env python3
"""
初始化数据库表结构
"""
import sys
import os

# 获取脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取 backend 目录
backend_dir = os.path.dirname(script_dir)
# 获取项目根目录
project_dir = os.path.dirname(backend_dir)

# 添加到 Python 路径
sys.path.insert(0, project_dir)
sys.path.insert(0, backend_dir)
os.chdir(project_dir)

from sqlalchemy import create_engine
from core.config import config
from core.db.base import Base
from core.db.models import DocumentModel  # noqa: F401
from core.db.user_models import UserModel, ConversationModel, MessageModel  # noqa: F401

def main():
    print("=" * 60)
    print("初始化数据库表结构")
    print("=" * 60)

    print(f"\n数据库: {config.DATABASE_URL}")

    # 创建引擎
    engine = create_engine(config.DATABASE_URL)

    # 创建所有表
    print("\n[1/2] 创建表结构...")

    try:
        Base.metadata.create_all(engine)
        print("[OK] 表结构创建成功")
    except Exception as e:
        print(f"[ERROR] 创建表失败: {e}")
        return False

    # 验证表是否创建成功
    print("\n[2/2] 验证表结构...")
    from sqlalchemy import inspect
    inspector = inspect(engine)

    tables = inspector.get_table_names()
    expected_tables = ['users', 'conversations', 'messages', 'documents']

    for table_name in expected_tables:
        if table_name in tables:
            columns = inspector.get_columns(table_name)
            print(f"[OK] {table_name}: {len(columns)} 列")
        else:
            print(f"[FAIL] {table_name}: 未找到")

    engine.dispose()

    print("\n" + "=" * 60)
    print("[OK] 数据库初始化完成!")
    print("=" * 60)
    print("\n下一步: 运行数据迁移脚本")
    print("  python scripts/migrate_json_to_pg.py")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
