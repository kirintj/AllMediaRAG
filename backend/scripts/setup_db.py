#!/usr/bin/env python3
"""
PostgreSQL 数据库设置脚本（非交互式）
"""

import subprocess
import sys
import os

def run_command(cmd, env=None):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            timeout=30,
            env=env
        )
        stdout = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ""
        stderr = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ""
        return result.returncode == 0, stdout, stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

def main():
    # 数据库配置
    PG_PASSWORD = "20050202"  # postgres 用户密码
    DB_NAME = "rag_db"
    DB_USER = "rag_user"
    DB_PASSWORD = "rag_password"

    # PostgreSQL bin 目录
    PG_BIN = r"D:\Develop\PostgreSQL\16\bin"

    # 设置环境变量
    env = os.environ.copy()
    env["PGPASSWORD"] = PG_PASSWORD
    env["PATH"] = PG_BIN + ";" + env.get("PATH", "")

    print("=" * 60)
    print("PostgreSQL 数据库设置")
    print("=" * 60)

    # 步骤 1: 创建用户
    print("\n[1/4] 创建用户...")
    cmd = f'psql -U postgres -h localhost -c "CREATE USER {DB_USER} WITH PASSWORD \'{DB_PASSWORD}\';"'
    success, stdout, stderr = run_command(cmd, env)

    if success:
        print(f"[OK] 用户 '{DB_USER}' 创建成功")
    elif "already exists" in stderr or "已经存在" in stderr:
        print(f"[OK] 用户 '{DB_USER}' 已存在")
    else:
        print(f"[FAIL] 创建用户失败: {stderr}")
        print("\n请检查 postgres 用户密码是否正确")
        print("如果是空密码，请修改脚本中的 PG_PASSWORD 为空字符串")
        return False

    # 步骤 2: 创建数据库
    print("\n[2/4] 创建数据库...")
    cmd = f'psql -U postgres -h localhost -c "CREATE DATABASE {DB_NAME} OWNER {DB_USER};"'
    success, stdout, stderr = run_command(cmd, env)

    if success:
        print(f"[OK] 数据库 '{DB_NAME}' 创建成功")
    elif "already exists" in stderr or "已经存在" in stderr:
        print(f"[OK] 数据库 '{DB_NAME}' 已存在")
    else:
        print(f"[FAIL] 创建数据库失败: {stderr}")
        return False

    # 步骤 3: 授权
    print("\n[3/4] 授予权限...")
    cmd = f'psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE {DB_NAME} TO {DB_USER};"'
    success, stdout, stderr = run_command(cmd, env)

    if success:
        print(f"[OK] 权限授予成功")
    else:
        print(f"[WARN] 权限授予失败: {stderr}")

    # 步骤 4: 启用 pgvector
    print("\n[4/4] 启用 pgvector 扩展...")
    env2 = env.copy()
    env2["PGPASSWORD"] = DB_PASSWORD
    cmd = f'psql -U {DB_USER} -h localhost -d {DB_NAME} -c "CREATE EXTENSION IF NOT EXISTS vector;"'
    success, stdout, stderr = run_command(cmd, env2)

    try:
        if success:
            print(f"[OK] pgvector 扩展启用成功")
        elif (stderr and "already exists" in stderr) or (stdout and "already exists" in stdout):
            print(f"[OK] pgvector 扩展已存在")
        else:
            print(f"[FAIL] 启用 pgvector 失败")
            print(f"请确保已安装 pgvector 扩展")
            return False
    except UnicodeEncodeError:
        if success:
            print(f"[OK] pgvector 扩展启用成功")
        else:
            print(f"[FAIL] 启用 pgvector 失败，请确保已安装 pgvector 扩展")
            return False

    # 验证连接
    print("\n" + "=" * 60)
    print("验证数据库连接...")
    print("=" * 60)

    cmd = f'psql -U {DB_USER} -h localhost -d {DB_NAME} -c "SELECT version();"'
    success, stdout, stderr = run_command(cmd, env2)

    try:
        if success:
            print(f"[OK] 数据库连接成功")
            print(stdout[:200] if len(stdout) > 200 else stdout)
        else:
            print(f"[FAIL] 连接失败")
            return False
    except UnicodeEncodeError:
        if success:
            print(f"[OK] 数据库连接成功")
        else:
            print(f"[FAIL] 连接失败")
            return False

    # 验证 pgvector
    print("\n验证 pgvector 扩展...")
    cmd = f'psql -U {DB_USER} -h localhost -d {DB_NAME} -c "SELECT extname, extversion FROM pg_extension WHERE extname = \'vector\';"'
    success, stdout, stderr = run_command(cmd, env2)

    try:
        if success and stdout and "vector" in stdout:
            print(f"[OK] pgvector 扩展正常")
            print(stdout[:200] if len(stdout) > 200 else stdout)
        else:
            print(f"[WARN] pgvector 扩展可能未正确安装")
    except UnicodeEncodeError:
        if success:
            print(f"[OK] pgvector 扩展正常")
        else:
            print(f"[WARN] pgvector 扩展可能未正确安装")

    print("=" * 60)
    print("[OK] 数据库设置完成！")
    print("=" * 60)
    print(f"\n连接信息:")
    print(f"  数据库: {DB_NAME}")
    print(f"  用户: {DB_USER}")
    print(f"  密码: {DB_PASSWORD}")
    print(f"  主机: localhost")
    print(f"  端口: 5432")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
