@echo off
chcp 65001 >nul
title A-Share 520 MA System - STOP

echo ========================================
echo   Stopping all services...
echo ========================================
echo.
echo [1/2] Stopping Backend (port 8000)...
echo [2/2] Stopping Frontend (port 5173)...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
exit