@echo off
setlocal
title JobPulse AI - Backend Server
cd /d "%~dp0"

echo ======================================================================
echo           JobPulse AI - FastAPI Backend Service (Port 8000)
echo ======================================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [*] Starting Uvicorn server on http://127.0.0.1:8000 ...
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Backend server stopped unexpectedly with exit code %ERRORLEVEL%.
    echo Please review the error message above.
    pause
)
