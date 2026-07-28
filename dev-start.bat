@echo off
chcp 65001 >nul
title ALLRAG Dev - One Click Start

echo ============================================
echo   ALLRAG Development Mode - One-Click Start
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

echo [1/4] Starting infrastructure services (Redis, PostgreSQL, MinIO, Elasticsearch, Neo4j) ...
docker compose up -d redis postgres minio elasticsearch neo4j

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] docker compose up failed. Check output above.
    pause
    exit /b 1
)

echo.
echo [2/4] Waiting for services to be ready ...
echo.

:: Wait for PostgreSQL to be ready
set /a pg_attempts=0
:wait_pg
set /a pg_attempts+=1
if %pg_attempts% gtr 30 (
    echo [WARN] PostgreSQL not ready after 30 attempts. Continuing anyway...
    goto wait_redis
)
timeout /t 2 /nobreak >nul
docker exec multimodal-rag-postgres pg_isready -U rag_user -d rag_db >nul 2>&1
if %errorlevel% neq 0 (
    echo   ... waiting for PostgreSQL (%pg_attempts%/30)
    goto wait_pg
)
echo   PostgreSQL is ready

:: Wait for Redis to be ready
:wait_redis
set /a redis_attempts=0
:wait_redis_loop
set /a redis_attempts+=1
if %redis_attempts% gtr 20 (
    echo [WARN] Redis not ready after 20 attempts. Continuing anyway...
    goto start_services
)
timeout /t 2 /nobreak >nul
docker exec multimodal-rag-redis redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo   ... waiting for Redis (%redis_attempts%/20)
    goto wait_redis_loop
)
echo   Redis is ready

:start_services
echo.
echo [3/4] Starting local services in separate windows ...
echo.

:: Start backend in new window
echo   Starting Backend (http://localhost:8000) ...
start "ALLRAG - Backend" cmd /k "cd /d %~dp0backend && python main.py"

:: Start worker in new window
echo   Starting Worker ...
start "ALLRAG - Worker" cmd /k "cd /d %~dp0backend && python worker.py"

:: Start frontend in new window
echo   Starting Frontend (http://localhost:5173) ...
start "ALLRAG - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo [4/4] Waiting for services to start ...
echo.

:: Wait for frontend to be ready
set /a fe_attempts=0
:wait_fe
set /a fe_attempts+=1
if %fe_attempts% gtr 30 (
    echo [WARN] Frontend not ready after 30 attempts. Opening browser anyway...
    goto open_browser
)
timeout /t 3 /nobreak >nul
curl -s http://localhost:5173 >nul 2>&1
if %errorlevel% neq 0 (
    echo   ... waiting for Frontend (%fe_attempts%/30)
    goto wait_fe
)

:open_browser
echo.
echo ============================================
echo   All services started!
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo   Neo4j:     http://localhost:7474
echo ============================================
echo.

:: Open browser
start "" "http://localhost:5173"

echo Press any key to exit ...
pause >nul