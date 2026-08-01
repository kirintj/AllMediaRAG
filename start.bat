@echo off
chcp 65001 >nul
title DataPilotAI - One Click Start

echo ============================================
echo   DataPilotAI One-Click Startup
echo ============================================
echo.

:: Check Docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker not running. Start Docker Desktop first.
    pause
    exit /b 1
)

:: Copy .env if missing
if not exist .env (
    if exist .env.example (
        echo [INFO] Copying .env.example to .env ...
        copy .env.example .env >nul
    ) else (
        echo [WARN] No .env file found. Create one before starting.
        pause
        exit /b 1
    )
)

echo [1/2] Starting all services (Redis, PostgreSQL, Neo4j, Backend, Worker, Frontend) ...
docker compose up -d --build

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] docker compose up failed. Check output above.
    pause
    exit /b 1
)

echo.
echo [2/2] Waiting for services to be healthy ...
echo.

:: Wait for backend health
set /a attempts=0
:wait_loop
set /a attempts+=1
if %attempts% gtr 30 (
    echo [WARN] Backend not healthy after 30 attempts. Check logs: docker compose logs backend
    goto open_browser
)
timeout /t 3 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo   ... waiting (%attempts%/30)
    goto wait_loop
)

:open_browser
echo.
echo ============================================
echo   All services started!
echo   Frontend:  http://localhost
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Neo4j:     http://localhost:7474
echo ============================================
echo.

:: Open browser
start http://localhost

echo Press any key to view logs (Ctrl+C to detach) ...
pause >nul
docker compose logs -f
