@echo off
chcp 65001 >nul
echo ============================================================
echo PostgreSQL 数据库初始化脚本
echo ============================================================
echo.

REM 设置变量
set DB_NAME=rag_db
set DB_USER=rag_user
set DB_PASSWORD=rag_password

echo 请输入 PostgreSQL 超级用户 (postgres) 的密码：
echo (如果没有设置密码，直接按回车)
set /p PG_PASSWORD="> "

if "%PG_PASSWORD%"=="" (
    set PGPASSWORD_ARG=
) else (
    set PGPASSWORD=%PG_PASSWORD%
)

echo.
echo [1/4] 创建用户 '%DB_USER%'...
psql -U postgres -h localhost -c "CREATE USER %DB_USER% WITH PASSWORD '%DB_PASSWORD%';" 2>nul
if %errorlevel% equ 0 (
    echo ✓ 用户创建成功
) else (
    echo ✓ 用户可能已存在，继续...
)

echo.
echo [2/4] 创建数据库 '%DB_NAME%'...
psql -U postgres -h localhost -c "CREATE DATABASE %DB_NAME% OWNER %DB_USER%;" 2>nul
if %errorlevel% equ 0 (
    echo ✓ 数据库创建成功
) else (
    echo ✓ 数据库可能已存在，继续...
)

echo.
echo [3/4] 授予权限...
psql -U postgres -h localhost -c "GRANT ALL PRIVILEGES ON DATABASE %DB_NAME% TO %DB_USER%;" 2>nul
if %errorlevel% equ 0 (
    echo ✓ 权限授予成功
) else (
    echo ⚠ 权限授予失败，可能需要手动处理
)

echo.
echo [4/4] 启用 pgvector 扩展...
set PGPASSWORD=%DB_PASSWORD%
psql -U %DB_USER% -h localhost -d %DB_NAME% -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>nul
if %errorlevel% equ 0 (
    echo ✓ pgvector 扩展启用成功
) else (
    echo ✗ 启用 pgvector 扩展失败
    echo 请确保已安装 pgvector 扩展
    pause
    exit /b 1
)

echo.
echo ============================================================
echo 验证数据库连接...
echo ============================================================
psql -U %DB_USER% -h localhost -d %DB_NAME% -c "SELECT version();"

echo.
echo 验证 pgvector 扩展...
psql -U %DB_USER% -h localhost -d %DB_NAME% -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"

echo.
echo ============================================================
echo ✓ 数据库初始化完成！
echo ============================================================
echo.
echo 连接信息：
echo   数据库: %DB_NAME%
echo   用户: %DB_USER%
echo   密码: %DB_PASSWORD%
echo   主机: localhost
echo   端口: 5432
echo.
echo 连接字符串：
echo   postgresql://%DB_USER%:%DB_PASSWORD%@localhost:5432/%DB_NAME%
echo.
pause
