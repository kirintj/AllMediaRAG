#!/usr/bin/env python3
"""
测试 PostgreSQL 连接（无需 pgvector）
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def main():
    print("=" * 60)
    print("PostgreSQL 连接测试")
    print("=" * 60)

    try:
        from sqlalchemy import create_engine, text
        from core.config import config

        print(f"\n连接字符串: {config.DATABASE_URL}")

        # 创建引擎
        engine = create_engine(config.DATABASE_URL)

        # 测试连接
        print("\n[1/3] 测试连接...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"[OK] 连接成功!")
            print(f"     PostgreSQL 版本: {version}")

        # 检查现有表
        print("\n[2/3] 检查现有表...")
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            if tables:
                print(f"[OK] 找到 {len(tables)} 个表:")
                for table in tables:
                    print(f"     - {table}")
            else:
                print("[INFO] 数据库中暂无表（需要运行迁移）")

        # 检查 pgvector 扩展（可选）
        print("\n[3/3] 检查 pgvector 扩展（可选）...")
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            ))
            has_pgvector = result.fetchone() is not None

            if has_pgvector:
                print("[INFO] pgvector 已安装（可用于向量存储）")
            else:
                print("[INFO] pgvector 未安装（将使用 ChromaDB 进行向量存储）")

        engine.dispose()

        print("\n" + "=" * 60)
        print("[OK] PostgreSQL 配置正确!")
        print("=" * 60)
        print("\n当前存储方案:")
        print("  - 用户数据: PostgreSQL")
        print("  - 对话记录: PostgreSQL")
        print("  - 向量存储: ChromaDB")

        return True

    except ImportError as e:
        print(f"\n[ERROR] 缺少依赖: {e}")
        print("请安装 SQLAlchemy: pip install sqlalchemy psycopg2-binary")
        return False
    except Exception as e:
        print(f"\n[ERROR] 连接失败: {e}")
        print("\n请检查:")
        print("  1. PostgreSQL 服务是否运行")
        print("  2. 用户名/密码是否正确")
        print("  3. 数据库 rag_db 是否存在")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
