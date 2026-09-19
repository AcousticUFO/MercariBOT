@echo off
title MercariBOT - Japan Listing Watchdog
cd /d "%~dp0"

echo ===================================================
echo               MercariBOT Launcher
echo ===================================================

:: 1. Detect Python 3.10 or higher
set "PY_CMD="
if not defined PY_CMD (
    py -3.12 --version >nul 2>&1 && set "PY_CMD=py -3.12"
)
if not defined PY_CMD (
    py -3.11 --version >nul 2>&1 && set "PY_CMD=py -3.11"
)
if not defined PY_CMD (
    py -3.10 --version >nul 2>&1 && set "PY_CMD=py -3.10"
)
if not defined PY_CMD (
    py -3 --version >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
    if exist "%LocalAppData%\Programs\Python\Python310\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python310\python.exe"
)
if not defined PY_CMD (
    if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python311\python.exe"
)
if not defined PY_CMD (
    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
)
if not defined PY_CMD (
    python --version >nul 2>&1 && set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [ERROR] Python is not installed.
    echo Please download and install Python 3.10+ from https://www.python.org/
    goto :error
)

:: 2. Verify that Python version is at least 3.10
%PY_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Found an outdated Python version.
    echo MercariBOT requires Python 3.10 or higher.
    goto :error
)

:: 3. Check for .env file
if exist ".env" goto :env_ok
echo [WARNING] No .env file found!
echo Creating .env from template .env.example...
copy .env.example .env >nul
echo Please edit .env with your Telegram bot credentials before starting.
notepad .env
goto :error

:env_ok

:: 4. Check virtual environment
if not exist ".venv" goto :create_venv

:: If .venv exists, verify it uses Python >= 3.10
.venv\Scripts\python.exe -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Detected incompatible or outdated .venv. Recreating...
    rd /s /q .venv
    goto :create_venv
)
goto :activate_venv

:create_venv
echo Creating Python virtual environment...
%PY_CMD% -m venv .venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    goto :error
)
call .venv\Scripts\activate.bat
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
goto :run_bot

:activate_venv
call .venv\Scripts\activate.bat

:run_bot
echo Starting MercariBOT...
python main.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo Press any key to exit...
pause >nul
exit /b 1
