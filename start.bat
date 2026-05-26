@echo off
chcp 65001 >nul
title A-Share 520 MA System - START

echo ========================================
echo   A-Share 520 MA Analysis System
echo   Starting services (background)...
echo ========================================
echo.

echo [1/4] Installing Python dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Python dependency install failed.
    pause
    exit /b
)
echo [OK] Python dependencies ready.
echo.

echo [2/4] Starting Backend (FastAPI) in background...
powershell -Command "Start-Process -WindowStyle Hidden -FilePath 'python' -ArgumentList '-m uvicorn main:app --reload --host 127.0.0.1 --port 8000' -WorkingDirectory '%~dp0backend'"
echo [OK] Backend starting at http://127.0.0.1:8000
timeout /t 4 /nobreak >nul
echo.

echo [3/4] Installing Frontend dependencies...
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependency install failed.
    pause
    exit /b
)
echo [OK] Frontend dependencies ready.
echo.

echo [4/4] Starting Frontend (Vite) in background...
powershell -Command "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c npx vite --host 127.0.0.1 --port 5173' -WorkingDirectory '%~dp0frontend'"
echo [OK] Frontend starting at http://127.0.0.1:5173
echo.

echo ========================================
echo   All services started successfully!
echo.
echo   Backend  API: http://127.0.0.1:8000
echo   Frontend UI:  http://127.0.0.1:5173
echo.
echo   Use stop.bat to shut down all services.
echo ========================================
echo.
echo Opening web UI in browser...
start http://127.0.0.1:5173
echo.
echo This window will close automatically in 3 seconds...
timeout /t 3 /nobreak >nul
exit
