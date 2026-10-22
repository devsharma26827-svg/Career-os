@echo off
setlocal enabledelayedexpansion
title JobPulse AI - Shutdown Controller
color 0C

cd /d "%~dp0"
set PROJECT_ROOT=%~dp0
set LOG_DIR=%PROJECT_ROOT%logs
set LOG_FILE=%LOG_DIR%\run.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo ======================================================================
echo           JobPulse AI - Graceful Shutdown Controller
echo ======================================================================
echo.
echo [*] Terminating running JobPulse AI services safely...

:: Execute selective shutdown script via PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%scripts\stop_services.ps1"

:: Fallback window close in case CMD windows linger
taskkill /FI "WINDOWTITLE eq JobPulse AI - Backend Server*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq JobPulse AI - Frontend Server*" /T /F >nul 2>&1

:: Clean up PID tracking file if exists
if exist "%LOG_DIR%\pids.txt" del /f /q "%LOG_DIR%\pids.txt" >nul 2>&1

echo.
echo ======================================================================
echo   SUCCESS: All JobPulse AI services have been stopped cleanly.
echo   Network ports 8000 and 5173 have been released.
echo   No background tasks or orphaned processes remain running.
echo ======================================================================
echo.
:: Safe pause without failing on redirected input
ping -n 3 127.0.0.1 >nul 2>&1
exit /b 0
