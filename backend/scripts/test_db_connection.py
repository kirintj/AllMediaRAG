#!/usr/bin/env python3
"""
PostgreSQL 数据库连接测试脚本
验证数据库连接、pgvector 扩展和表结构
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("PostgreSQL 数据库连接测试")
    print("=" * 60)

    # 测试同步连接
    print("\n[1/5] 测试同步连接...")
    try:
        from sqlalchemy import create_engine, text
        from core.config import config

        engine = create_engine(config.DATABASE_URL_SYNC)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ 同步连接成功")
            print(f"  数据库版本: {version}")

        engine.dispose()
    except Exception as e:
        print(f"✗ 同步连接失败: {e}")
        return False

    # 测试异步连接
    print("\n[2/5] 测试异步连接...")
    try:
        import asyncio
        from sqlalchemy.ext.asyncio import create_async_engine
        from core.config import config

        async def test_async():
            engine = create_async_engine(config.DATABASE_URL)
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"✓ 异步连接成功")
                print(f"  数据库版本: {version}")
            await engine.dispose()

        asyncio.run(test_async())
    except Exception as e:
        print(f"✗ 异步连接失败: {e}")
        return False

    # 测试 pgvector 扩展
    print("\n[3/5] 测试 pgvector 扩展...")
    try:
        from sqlalchemy import create_engine, text
        from core.config import config

        engine = create_engine(config.DATABASE_URL_SYNC)

        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector'"
            ))
            row = result.fetchone()

            if row:
                print(f"✓ pgvector 扩展已安装")
                print(f"  版本: {row[1]}")
            else:
                print(f"✗ pgvector 扩展未安装")
                return False

        engine.dispose()
    except Exception as e:
        print(f"✗ 检查 pgvector 扩展失败: {e}")
        return False

    # 测试向量操作
    print("\n[4/5] 测试向量操作...")
    try:
        from sqlalchemy import create_engine, text
        from core.config import config
        from pgvector.sqlalchemy import Vector

        engine = create_engine(config.DATABASE_URL_SYNC)

        with engine.connect() as conn:
            # 创建测试表
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS vector_test (
                    id SERIAL PRIMARY KEY,
                    embedding VECTOR(3)
                )
            """))

            # 插入测试向量
            conn.execute(text(
                "INSERT INTO vector_test (embedding) VALUES (ARRAY[1.0, 2.0, 3.0]::vector)"
            ))

            # 查询测试向量
            result = conn.execute(text("SELECT * FROM vector_test"))
            rows = result.fetchall()

            print(f"✓ 向量操作成功")
            print(f"  插入和查询 {len(rows)} 条记录")

            # 清理测试表
            conn.execute(text("DROP TABLE IF EXISTS vector_test"))
            conn.commit()

        engine.dispose()
    except Exception as e:
        print(f"✗ 向量操作失败: {e}")
        return False

    # 测试 ORM 模型
    print("\n[5/5] 测试 ORM 模型...")
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from core.config import config
        from core.db.models import Base, DocumentChunk

        engine = create_engine(config.DATABASE_URL_SYNC)

        # 创建所有表
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        session = Session()

        # 测试查询
        count = session.query(DocumentChunk).count()
        print(f"✓ ORM 模型正常")
        print(f"  当前文档块数量: {count}")

        session.close()
        engine.dispose()
    except Exception as e:
        print(f"✗ ORM 模型测试失败: {e}")
        return False

    print("\n" + "=" * 60)
    print("✓ 所有测试通过！数据库配置正确。")
    print("=" * 60)

    return True

def show_table_info():
    """显示表信息"""
    print("\n" + "=" * 60)
    print("数据库表信息")
    print("=" * 60)

    try:
        from sqlalchemy import create_engine, text, inspect
        from core.config import config

        engine = create_engine(config.DATABASE_URL_SYNC)
        inspector = inspect(engine)

        tables = inspector.get_table_names()

        if not tables:
            print("\n⚠ 数据库中没有表")
            print("请运行 Alembic 迁移: python -m alembic upgrade head")
            return

        print(f"\n找到 {len(tables)} 个表:\n")

        for table_name in sorted(tables):
            if table_name.startswith('alembic_'):
                continue

            columns = inspector.get_columns(table_name)
            print(f"  📋 {table_name}")
            print(f"     列数: {len(columns)}")

            for col in columns[:5]:  # 只显示前5列
                print(f"     - {col['name']}: {col['type']}")

            if len(columns) > 5:
                print(f"     ... 还有 {len(columns) - 5} 列")

            print()

        engine.dispose()

    except Exception as e:
        print(f"✗ 获取表信息失败: {e}")

def main():
    """主函数"""
    success = test_connection()

    if success:
        show_table_info()
        print("\n✓ 数据库配置完成，可以启动应用了！")
        print("\n启动命令:")
        print("  cd backend")
        print("  python main.py")
        sys.exit(0)
    else:
        print("\n✗ 数据库配置有问题，请参考 docs/postgresql-setup.md 进行设置")
        sys.exit(1)

if __name__ == "__main__":
    main()
