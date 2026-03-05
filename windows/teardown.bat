@echo off
setlocal enabledelayedexpansion

:: Switch to project root
cd /d "%~dp0.."

echo ===================================================
echo     llms.txt Generator - Windows Teardown Script
echo ===================================================
echo.
echo WARNING: This will completely remove:
echo  1. The Python virtual environment (venv)
echo  2. Any saved progress (state.json)
echo  3. Any generated llms.txt files
echo.
set /p choice="Are you sure you want to continue? (Y/N): "
if /I not "%choice%"=="Y" (
    echo [INFO] Teardown cancelled.
    pause
    exit /b 0
)

echo.
echo [INFO] Starting teardown...

:: Remove venv directory
if exist "venv\" (
    echo [1/3] Removing virtual environment...
    rmdir /s /q venv
    if exist "venv\" (
        echo [ERROR] Failed to remove venv. Close any running scripts or terminals using it and try again.
    ) else (
        echo [OK] Virtual environment removed.
    )
) else (
    echo [1/3] Virtual environment not found, skipping.
)

:: Remove state file
if exist "state.json" (
    echo [2/3] Removing state.json...
    del /q state.json
    echo [OK] State removed.
) else (
    echo [2/3] State file not found, skipping.
)

:: Remove generated files
if exist "llms.txt" (
    echo [3/3] Removing generated llms.txt...
    del /q llms.txt
    echo [OK] Generated llms.txt removed.
) else (
    echo [3/3] llms.txt not found, skipping.
)

echo.
echo ===================================================
echo Teardown Complete! 
echo You can now run windows\setup.bat again from a clean slate.
echo ===================================================
pause
