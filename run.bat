@echo off
title MercariBOT - Japan Listing Watchdog
cd /d "%~dp0"

echo ===================================================
echo               MercariBOT Launcher
echo ===================================================

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please download and install Python from https://www.python.org/
    pause
    exit /b 1
)

:: Check for .env file
if not exist ".env" (
    echo [WARNING] No .env file found!
    echo Creating .env from template .env.example...
    copy .env.example .env >nul
    echo Please edit .env with your Telegram bot credentials before starting.
    notepad .env
    pause
    exit /b 1
)

:: Check for virtual environment
if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install --upgrade pip
    pip install -e .
) else (
    call .venv\Scripts\activate.bat
)

echo Starting MercariBOT...
python main.py

if errorlevel 1 (
    echo.
    echo MercariBOT stopped with an error.
    pause
)
