@echo off
setlocal enabledelayedexpansion

:: Switch to project root
cd /d "%~dp0.."

if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found. Please run windows\setup.bat first.
    pause
    exit /b 1
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Starting Streamlit Application...
python -m streamlit run src\app.py

pause
