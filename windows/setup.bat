@echo off
setlocal enabledelayedexpansion

:: Switch to the project root directory
cd /d "%~dp0.."

echo ===================================================
echo     llms.txt Generator - Windows Setup Script
echo ===================================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo.
    echo Please install Python 3.9 or higher:
    echo 1. Go to https://www.python.org/downloads/windows/
    echo 2. Download the latest Windows installer.
    echo 3. Run the installer.
    echo 4. IMPORTANT: Check the box "Add Python to PATH" at the bottom!
    echo 5. Restart your terminal and run this script again.
    echo.
    pause
    exit /b 1
)

echo [OK] Python is installed.

:: Create virtual environment if it doesn't exist
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
) else (
    echo [OK] Virtual environment already exists.
)

:: Activate and install requirements
echo [INFO] Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

if exist "requirements.txt" (
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed successfully.
) else (
    echo [WARNING] requirements.txt not found.
)

echo ===================================================
echo Setup Complete!
echo.
echo To start the application, run:
echo    windows\run.bat
echo ===================================================
pause
