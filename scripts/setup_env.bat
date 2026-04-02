@echo off
REM ============================================================================
REM Miko3 Talents Automation — Environment Setup (Windows)
REM ============================================================================
REM This script creates a Python virtual environment and installs dependencies.
REM
REM Usage:
REM   scripts\setup_env.bat
REM ============================================================================

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║       Miko3 Talents Automation — Environment Setup      ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Check Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo   Download from: https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

REM Check ADB is installed
adb version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] ADB is not installed or not in PATH.
    echo   Download from: https://developer.android.com/tools/releases/platform-tools
    echo   Extract and add the folder to your system PATH.
    echo.
)

REM Navigate to project root
cd /d "%~dp0\.."

REM Create virtual environment
echo [1/3] Creating virtual environment...
if not exist "venv" (
    python -m venv venv
    echo   ✓ Virtual environment created
) else (
    echo   ✓ Virtual environment already exists
)

REM Activate virtual environment
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [3/3] Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ════════════════════════════════════════════════════════════
echo   ✓ Environment setup complete!
echo.
echo   To activate the environment:
echo     venv\Scripts\activate.bat
echo.
echo   To run tests:
echo     python runner.py --help
echo     python runner.py --all
echo     python runner.py --discover
echo ════════════════════════════════════════════════════════════
echo.
pause
