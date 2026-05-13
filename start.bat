@echo off
setlocal enabledelayedexpansion
set PYTHONIOENCODING=utf-8

echo ==========================================================
echo   ShieldCloud -- Full System Launcher
echo ==========================================================
echo.
echo [1/9] Starting Docker infrastructure (PostgreSQL, MinIO, Redis, RabbitMQ)...
cd /d "%~dp0infra"
docker-compose up -d --remove-orphans
cd /d "%~dp0"
echo       [OK] Docker started
timeout /t 4 /nobreak >nul

echo [2/9] Starting Auth Service on :3001...
start "Auth Service" cmd /c "cd /d %~dp0auth-service && npm run start"
timeout /t 3 /nobreak >nul
echo       [OK] Auth Service started

echo [3/9] Starting Storage Service on :3003...
start "Storage Service" cmd /c "cd /d %~dp0storage-service && npm run start"
timeout /t 3 /nobreak >nul
echo       [OK] Storage Service started

echo [4/9] Starting Encryption Service on :3002...
start "Encryption Service" cmd /c "cd /d %~dp0encryption-service && python -m uvicorn src.main:app --host 0.0.0.0 --port 3002 --reload"
timeout /t 3 /nobreak >nul
echo       [OK] Encryption Service started

echo [5/9] Starting Anomaly ML Service on :3004...
start "Anomaly ML" cmd /c "cd /d %~dp0anomaly-service && python -m uvicorn src.main:app --host 0.0.0.0 --port 3004 --reload"
timeout /t 4 /nobreak >nul
echo       [OK] Anomaly ML Service started

echo [6/9] Starting Risk Engine on :3005...
start "Risk Engine" cmd /c "cd /d %~dp0risk-engine && python -m uvicorn src.main:sio_app --host 0.0.0.0 --port 3005 --reload"
timeout /t 3 /nobreak >nul
echo       [OK] Risk Engine started

echo [7/9] Starting Self-Healing Worker...
start "Self-Healing" cmd /c "cd /d %~dp0self-healing-service && python src\workers\consumer.py"
timeout /t 2 /nobreak >nul
echo       [OK] Self-Healing Consumer started

echo [8/9] Starting Notification Service...
start "Notification" cmd /c "cd /d %~dp0notification-service && npx ts-node src/main.ts"
timeout /t 2 /nobreak >nul
echo       [OK] Notification Service started

echo [9/9] Starting Frontend on :5173...
start "Frontend" cmd /c "cd /d %~dp0frontend && npm run dev -- --host"
timeout /t 5 /nobreak >nul
echo       [OK] Frontend started

echo.
echo ==================================================
echo   All ShieldCloud Services Running!
echo ==================================================
echo.
echo   Dashboard      -^>  http://localhost:5173
echo   Auth API       -^>  http://localhost:3001
echo   Encryption API -^>  http://localhost:3002
echo   Storage API    -^>  http://localhost:3003
echo   Anomaly ML API -^>  http://localhost:3004
echo   Risk Engine    -^>  http://localhost:3005
echo   MinIO UI       -^>  http://localhost:9001  (minioadmin/minioadmin)
echo   RabbitMQ UI    -^>  http://localhost:15672 (guest/guest)
echo.
echo   LAN Access     -^>  http://10.82.170.145:5173
echo.

echo [PUBLIC] Getting public HTTPS tunnel URL...
start "Localtunnel" cmd /c "npx --yes localtunnel --port 5173"
timeout /t 6 /nobreak >nul

echo.
echo   NOTE: A new window opened called "Localtunnel".
echo   Look inside it for a line saying:
echo       your url is: https://XXXX.loca.lt
echo   That is your public HTTPS URL - open on any device!
echo   (First visit: click the Continue button on the splash page)
echo.

start "" "http://localhost:5173"

echo Press any key to stop all services and close this window...
pause >nul

echo Stopping all services...
taskkill /FI "WINDOWTITLE eq Auth Service*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Storage Service*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Encryption Service*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Anomaly ML*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Risk Engine*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Self-Healing*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Notification*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Frontend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Localtunnel*" /F >nul 2>&1
