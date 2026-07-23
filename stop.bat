@echo off
chcp 65001 >nul
title ALLRAG - Stop

echo Stopping all services ...
docker compose down
echo Done.
pause
