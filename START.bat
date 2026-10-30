@echo off
title FitGirl Repack Downloader (Terminal Edition)
cd /d "%~dp0"

echo ===================================================
echo   FitGirl Repack Downloader - Terminal Edition
echo ===================================================
echo.

:: Check for virtualenv
if not exist ".venv\Scripts\python.exe" (
    echo Setting up virtual environment .venv...
    python -m venv .venv
    echo Installing dependencies...
    .venv\Scripts\python.exe -m pip install --quiet --upgrade pip
    .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
)

echo Launching main.py in terminal...
echo.
.venv\Scripts\python.exe main.py %*

if %ERRORLEVEL% neq 0 (
    pause
)
