@echo off
chcp 65001 >nul
title DataPilotAI Dev - Stop

echo ============================================
echo   DataPilotAI Development Mode - Stop
echo ============================================
echo.

echo [1/2] Stopping infrastructure services ...
docker compose down

echo.
echo [2/2] Killing local Python and Node processes ...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im node.exe >nul 2>&1

echo.
echo All services stopped.
pause