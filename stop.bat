@echo off
chcp 65001 >nul
title DataPilotAI - Stop

echo Stopping all services ...
docker compose down
echo Done.
pause
