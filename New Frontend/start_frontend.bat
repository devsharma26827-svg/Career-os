@echo off
setlocal
title JobPulse AI - Frontend Server
cd /d "%~dp0"

echo ======================================================================
echo           JobPulse AI - CareerOS Frontend Service (Port 5173)
echo ======================================================================
echo.

echo [*] Starting Vite development server on http://localhost:5173 ...
call npm run dev
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Frontend server stopped unexpectedly with exit code %ERRORLEVEL%.
    echo Please review the error message above.
    pause
)
