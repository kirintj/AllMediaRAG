# pgvector 自动安装脚本 (PowerShell)
# 以管理员身份运行此脚本

$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "pgvector 自动安装脚本 (PostgreSQL 16)" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# PostgreSQL 安装路径
$PG_PATH = "D:\Develop\PostgreSQL\16"
$PG_VERSION = "16"

# 检查 PostgreSQL 是否存在
if (-not (Test-Path "$PG_PATH\bin\pg_config.exe")) {
    Write-Host "[ERROR] PostgreSQL 未找到: $PG_PATH" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] PostgreSQL 路径: $PG_PATH" -ForegroundColor Green
Write-Host "[INFO] PostgreSQL 版本: $PG_VERSION" -ForegroundColor Green
Write-Host ""

# 方法 1: 尝试使用 Stack Builder
Write-Host "[1/3] 尝试使用 Stack Builder 安装..." -ForegroundColor Yellow
$stackBuilder = "$PG_PATH\bin\StackBuilder.exe"

if (Test-Path $stackBuilder) {
    Write-Host "[INFO] Stack Builder 已找到" -ForegroundColor Green
    Write-Host ""
    Write-Host "请手动完成以下步骤：" -ForegroundColor Cyan
    Write-Host "1. Stack Builder 即将打开" -ForegroundColor White
    Write-Host "2. 选择你的 PostgreSQL 16 实例" -ForegroundColor White
    Write-Host "3. 展开 'Spatial Extensions' 分类" -ForegroundColor White
    Write-Host "4. 勾选 'pgvector' 并点击下一步安装" -ForegroundColor White
    Write-Host "5. 安装完成后关闭 Stack Builder" -ForegroundColor White
    Write-Host ""
    Read-Host "按 Enter 键打开 Stack Builder"

    # 启动 Stack Builder
    Start-Process $stackBuilder

    Write-Host ""
    Read-Host "安装完成后按 Enter 键继续"

    # 验证安装
    Write-Host ""
    Write-Host "[2/3] 验证 pgvector 安装..." -ForegroundColor Yellow

    $env:PGPASSWORD = "20050202"
    $result = & "$PG_PATH\bin\psql.exe" -U postgres -h localhost -c "SELECT 1 FROM pg_available_extensions WHERE name = 'vector';" 2>&1

    if ($result -match "1") {
        Write-Host "[OK] pgvector 扩展可用" -ForegroundColor Green
    } else {
        Write-Host "[WARN] pgvector 扩展可能未安装" -ForegroundColor Yellow
        Write-Host "请尝试方法 2 或方法 3" -ForegroundColor Yellow
    }
} else {
    Write-Host "[WARN] Stack Builder 未找到" -ForegroundColor Yellow
}

# 方法 2: 手动下载说明
Write-Host ""
Write-Host "[3/3] 如果 Stack Builder 安装失败，请手动安装：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 访问 https://github.com/pgvector/pgvector/releases" -ForegroundColor Cyan
Write-Host "2. 下载 'pgvector-*-windows-x64.zip'" -ForegroundColor Cyan
Write-Host "3. 解压后复制文件到 PostgreSQL 目录：" -ForegroundColor Cyan
Write-Host "   - vector.dll -> $PG_PATH\lib\" -ForegroundColor White
Write-Host "   - vector*.sql -> $PG_PATH\share\extension\" -ForegroundColor White
Write-Host "   - vector.control -> $PG_PATH\share\extension\" -ForegroundColor White
Write-Host "4. 重启 PostgreSQL 服务" -ForegroundColor Cyan
Write-Host ""

# 验证扩展
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "验证 pgvector 扩展" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$env:PGPASSWORD = "20050202"
$env:PGUSER = "rag_user"
$env:PGDATABASE = "rag_db"

Write-Host "连接数据库并启用扩展..." -ForegroundColor Yellow
$result = & "$PG_PATH\bin\psql.exe" -U rag_user -h localhost -d rag_db -c "CREATE EXTENSION IF NOT EXISTS vector; SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" 2>&1

if ($result -match "vector") {
    Write-Host ""
    Write-Host "[OK] pgvector 安装并启用成功！" -ForegroundColor Green
    Write-Host $result
} else {
    Write-Host ""
    Write-Host "[FAIL] pgvector 安装失败" -ForegroundColor Red
    Write-Host $result
    Write-Host ""
    Write-Host "请参考 docs/pgvector-install.md 获取详细安装指南" -ForegroundColor Yellow
}

Write-Host ""
Read-Host "按 Enter 键退出"
