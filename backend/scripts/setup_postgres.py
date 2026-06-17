#!/usr/bin/env python3
"""
PostgreSQL 数据库初始化脚本
创建数据库、用户和启用 pgvector 扩展
"""

import subprocess
import sys
import os

def run_psql(command, user="postgres", password=None):
    """执行 psql 命令"""
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    try:
        result = subprocess.run(
            ["psql", "-U", user, "-h", "localhost", "-c", command],
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def main():
    print("=" * 60)
    print("PostgreSQL 数据库初始化")
    print("=" * 60)

    # 数据库配置
    DB_NAME = "rag_db"
    DB_USER = "rag_user"
    DB_PASSWORD = "rag_password"

    # 提示用户输入 postgres 密码
    print("\n请输入 PostgreSQL 超级用户 (postgres) 的密码：")
    print("(如果没有设置密码，直接按回车)")
    pg_password = input("> ").strip()

    if not pg_password:
        pg_password = None

    # 步骤 1: 创建用户
    print(f"\n[1/4] 创建用户 '{DB_USER}'...")
    success, stdout, stderr = run_psql(
        f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASSWORD}';",
        password=pg_password
    )

    if success:
        print(f"✓ 用户 '{DB_USER}' 创建成功")
    elif "already exists" in stderr:
        print(f"✓ 用户 '{DB_USER}' 已存在")
    else:
        print(f"✗ 创建用户失败: {stderr}")
        sys.exit(1)

    # 步骤 2: 创建数据库
    print(f"\n[2/4] 创建数据库 '{DB_NAME}'...")
    success, stdout, stderr = run_psql(
        f"CREATE DATABASE {DB_NAME} OWNER {DB_USER};",
        password=pg_password
    )

    if success:
        print(f"✓ 数据库 '{DB_NAME}' 创建成功")
    elif "already exists" in stderr:
        print(f"✓ 数据库 '{DB_NAME}' 已存在")
    else:
        print(f"✗ 创建数据库失败: {stderr}")
        sys.exit(1)

    # 步骤 3: 授予权限
    print(f"\n[3/4] 授予用户权限...")
    success, stdout, stderr = run_psql(
        f"GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};",
        password=pg_password
    )

    if success:
        print(f"✓ 权限授予成功")
    else:
        print(f"⚠ 权限授予失败（可能需要手动处理）: {stderr}")

    # 步骤 4: 启用 pgvector 扩展
    print(f"\n[4/4] 启用 pgvector 扩展...")
    success, stdout, stderr = run_psql(
        "CREATE EXTENSION IF NOT EXISTS vector;",
        user=DB_USER,
        password=DB_PASSWORD
    )

    if success:
        print(f"✓ pgvector 扩展启用成功")
    elif "already exists" in stdout or "already exists" in stderr:
        print(f"✓ pgvector 扩展已存在")
    else:
        print(f"✗ 启用 pgvector 扩展失败: {stderr}")
        print("\n请确保已安装 pgvector 扩展：")
        print("  Windows: 使用 Stack Builder 或下载安装包")
        print("  Linux: sudo apt install postgresql-16-pgvector")
        sys.exit(1)

    # 验证连接
    print("\n" + "=" * 60)
    print("验证数据库连接...")
    success, stdout, stderr = run_psql(
        "SELECT version();",
        user=DB_USER,
        password=DB_PASSWORD
    )

    if success:
        print("✓ 数据库连接成功")
        print(stdout)
    else:
        print(f"✗ 连接失败: {stderr}")
        sys.exit(1)

    # 验证 pgvector
    print("验证 pgvector 扩展...")
    success, stdout, stderr = run_psql(
        "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';",
        user=DB_USER,
        password=DB_PASSWORD
    )

    if success and "vector" in stdout:
        print("✓ pgvector 扩展正常")
        print(stdout)
    else:
        print(f"⚠ pgvector 扩展可能未正确安装")

    print("\n" + "=" * 60)
    print("✓ 数据库初始化完成！")
    print("=" * 60)
    print(f"\n连接信息：")
    print(f"  数据库: {DB_NAME}")
    print(f"  用户: {DB_USER}")
    print(f"  密码: {DB_PASSWORD}")
    print(f"  主机: localhost")
    print(f"  端口: 5432")
    print(f"\n连接字符串：")
    print(f"  postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/{DB_NAME}")

if __name__ == "__main__":
    main()
