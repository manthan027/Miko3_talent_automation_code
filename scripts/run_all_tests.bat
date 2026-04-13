@echo off
REM ============================================================================
REM Miko3 Talents Automation — Run All Tests (Windows)
REM ============================================================================
REM Activates venv and runs full test suite with report generation.
REM
REM Usage:
REM   scripts\run_all_tests.bat
REM   scripts\run_all_tests.bat --verbose
REM   scripts\run_all_tests.bat --talent mikoji
REM ============================================================================

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║         Miko3 Talents Automation — Test Runner          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

REM Navigate to project root
cd /d "%~dp0\.."

REM Activate virtual environment
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
    echo [✓] Virtual environment activated
) else (
    echo [WARNING] No virtual environment found. Run scripts\setup_env.bat first.
    echo   Attempting to run with system Python...
)

REM Check device connection
echo.
echo [1/2] Checking device connection...
adb devices
echo.

REM Run tests
echo [2/2] Running tests...
echo ────────────────────────────────────────────────────────────
echo.

if "%~1"=="" (
    python runner.py --all
) else (
    python runner.py %*
)

echo.
echo ════════════════════════════════════════════════════════════
echo   Test run complete. Check reports\ for HTML report.
echo ════════════════════════════════════════════════════════════
echo.
pause
