@echo off
setlocal enabledelayedexpansion
title JobPulse AI - Launch Controller
color 0B

cd /d "%~dp0"
set PROJECT_ROOT=%~dp0
set LOG_DIR=%PROJECT_ROOT%logs
set LOG_FILE=%LOG_DIR%\run.log

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [%DATE% %TIME%] [START] Launching JobPulse AI Controller... >> "%LOG_FILE%"

echo ======================================================================
echo           JobPulse AI - Accessible Autonomous Job Application Platform
echo ======================================================================
echo.

:: 1. Check Python Dependency & Version (>= 3.10)
echo [*] Checking Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo         Please install Python 3.10 or higher from https://www.python.org/
    echo         Ensure "Add python.exe to PATH" is checked during setup.
    echo [%DATE% %TIME%] [ERROR] Python not found in PATH >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3.10 or higher is required.
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo         Found: %%i
    echo         Please upgrade Python to 3.10 or higher.
    echo [%DATE% %TIME%] [ERROR] Python version below 3.10 >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do (
    echo     Found %%i
    echo [%DATE% %TIME%] [INFO] Python: %%i >> "%LOG_FILE%"
)

:: 2. Check Node.js Dependency & Version (>= 18)
echo [*] Checking Node.js installation...
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js was not found in your system PATH.
    echo         Please install Node.js 18 or higher from https://nodejs.org/
    echo [%DATE% %TIME%] [ERROR] Node.js not found in PATH >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)

node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 18 ? 0 : 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js 18 or higher is required.
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do echo         Found: Node.js %%i
    echo         Please upgrade Node.js to 18 or higher.
    echo [%DATE% %TIME%] [ERROR] Node.js version below 18 >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version 2^>^&1') do (
    echo     Found Node.js %%i
    echo [%DATE% %TIME%] [INFO] Node.js: %%i >> "%LOG_FILE%"
)

:: 3. Check npm Dependency & Version (>= 9)
echo [*] Checking npm installation...
call npm --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm was not found in your system PATH.
    echo         Please install npm 9 or higher - included with Node.js.
    echo [%DATE% %TIME%] [ERROR] npm not found in PATH >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)

node -e "const cp = require('child_process'); try { const v = cp.execSync('npm --version', {shell: true}).toString().trim().split('.')[0]; process.exit(Number(v) >= 9 ? 0 : 1); } catch(e) { process.exit(1); }" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] npm 9 or higher is required.
    for /f "tokens=*" %%i in ('call npm --version 2^>^&1') do echo         Found: npm %%i
    echo         Please upgrade npm.
    echo [%DATE% %TIME%] [ERROR] npm version below 9 >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('call npm --version 2^>^&1') do (
    echo     Found npm %%i
    echo [%DATE% %TIME%] [INFO] npm: %%i >> "%LOG_FILE%"
)

:: 4. Verify or Create Backend Virtual Environment
set BACKEND_DIR=%PROJECT_ROOT%backend
set FRONTEND_DIR=%PROJECT_ROOT%New Frontend
set VENV_DIR=%BACKEND_DIR%\venv
set VENV_PYTHON=%VENV_DIR%\Scripts\python.exe

echo.
echo [*] Verifying backend virtual environment...
if not exist "%VENV_PYTHON%" (
    echo     Creating Python virtual environment in backend\venv...
    echo [%DATE% %TIME%] [INFO] Creating venv in %VENV_DIR% >> "%LOG_FILE%"
    python -m venv "%VENV_DIR%"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create Python virtual environment.
        echo         Ensure Python venv module is available on your machine.
        echo [%DATE% %TIME%] [ERROR] Failed to create venv >> "%LOG_FILE%"
        echo.
        pause
        exit /b 1
    )
    echo     Virtual environment created successfully.
) else (
    echo     Existing virtual environment verified.
)

:: 5. Verify Backend Dependencies
echo [*] Verifying backend dependencies...
"%VENV_PYTHON%" -c "import fastapi, uvicorn, pydantic, sqlalchemy" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo     Installing backend packages - this may take a moment on first run...
    echo [%DATE% %TIME%] [INFO] Installing backend dependencies via pip >> "%LOG_FILE%"
    "%VENV_PYTHON%" -m pip install --upgrade pip >nul 2>&1
    "%VENV_PYTHON%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install backend dependencies.
        echo         Check your internet connection and proxy settings.
        echo [%DATE% %TIME%] [ERROR] Pip install requirements.txt failed >> "%LOG_FILE%"
        echo.
        pause
        exit /b 1
    )
    echo     Backend dependencies installed successfully.
) else (
    echo     Backend dependencies are verified.
)

:: 6. Verify Backend Configuration (.env)
if not exist "%BACKEND_DIR%\.env" (
    echo [*] Initializing backend configuration...
    if exist "%BACKEND_DIR%\.env.example" (
        copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
        echo     Created backend\.env from template.
        echo [%DATE% %TIME%] [INFO] Created backend\.env from .env.example >> "%LOG_FILE%"
    ) else (
        echo SECRET_KEY=jobpulse_default_local_development_secret_key_32bytes_min_length_12345> "%BACKEND_DIR%\.env"
        echo DATABASE_URL=sqlite:///./sql_app.db>> "%BACKEND_DIR%\.env"
        echo ENVIRONMENT=production>> "%BACKEND_DIR%\.env"
        echo     Created default backend\.env configuration.
        echo [%DATE% %TIME%] [INFO] Created default backend\.env >> "%LOG_FILE%"
    )
    echo     NOTE: Optional services can be configured in backend\.env
) else (
    echo     Backend configuration verified.
)

:: 7. Verify Frontend Dependencies
echo.
echo [*] Verifying frontend dependencies...
if not exist "%FRONTEND_DIR%\node_modules" (
    echo     Installing frontend packages via npm install...
    echo [%DATE% %TIME%] [INFO] Installing frontend packages via npm install >> "%LOG_FILE%"
    cd /d "%FRONTEND_DIR%"
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to install frontend packages.
        echo [%DATE% %TIME%] [ERROR] npm install failed >> "%LOG_FILE%"
        cd /d "%PROJECT_ROOT%"
        echo.
        pause
        exit /b 1
    )
    cd /d "%PROJECT_ROOT%"
    echo     Frontend packages installed successfully.
) else (
    echo     Frontend packages verified.
)

:: 8. Inspect and Resolve Network Ports
echo.
echo [*] Inspecting network ports 8000 and 5173...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_ROOT%scripts\check_ports.ps1"
if %ERRORLEVEL% EQU 2 (
    echo [ERROR] Port conflict detected. An external application is occupying port 8000 or 5173.
    echo         Please close the conflicting application or configure alternate ports.
    echo [%DATE% %TIME%] [ERROR] Port conflict on 8000 or 5173 >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)

:: 9. Launch Backend Server in Dedicated Window
echo.
echo [*] Launching JobPulse AI Backend Server on http://127.0.0.1:8000 ...
echo [%DATE% %TIME%] [INFO] Starting Backend Server window >> "%LOG_FILE%"
start "JobPulse AI - Backend Server" cmd /k "call "%BACKEND_DIR%\start_backend.bat""

:: 10. Launch Frontend Server in Dedicated Window
echo [*] Launching JobPulse AI Frontend Server on http://localhost:5173 ...
echo [%DATE% %TIME%] [INFO] Starting Frontend Server window >> "%LOG_FILE%"
start "JobPulse AI - Frontend Server" cmd /k call "%FRONTEND_DIR%\start_frontend.bat"

:: 11. Verify Service Health
echo.
echo [*] Waiting for services to initialize...
"%VENV_PYTHON%" "%PROJECT_ROOT%scripts\health_check.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ======================================================================
    echo   [ERROR] Services did not become healthy within the timeout window.
    echo ======================================================================
    echo   Troubleshooting steps:
    echo   1. Inspect the "JobPulse AI - Backend Server" window for Python errors.
    echo   2. Inspect the "JobPulse AI - Frontend Server" window for Node errors.
    echo   3. Inspect detailed logs in: logs\run.log
    echo   4. Run stop.bat to cleanly release all resources before retrying.
    echo ======================================================================
    echo [%DATE% %TIME%] [ERROR] Health check failed >> "%LOG_FILE%"
    echo.
    pause
    exit /b 1
)

:: 12. Open Browser and Display Success Dashboard
echo.
echo [*] Opening JobPulse AI in your default web browser...
start http://localhost:5173

echo.
echo ======================================================================
echo   SUCCESS: JobPulse AI is running!
echo   Frontend : http://localhost:5173
echo   Backend  : http://127.0.0.1:8000  (API Documentation at /docs)
echo.
echo   - Backend and Frontend are running in their own labeled windows.
echo   - Diagnostic logs are recorded in logs\run.log
echo   - To safely stop all services and release ports, run: stop.bat
echo ======================================================================
echo.
echo Press any key to close this launch controller window.
echo (The backend and frontend services will continue running in their own windows.)
pause >nul
exit /b 0
