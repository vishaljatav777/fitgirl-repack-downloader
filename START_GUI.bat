@echo off
title FitGirl Repack Downloader (Desktop GUI)
cd /d "%~dp0"

echo ===================================================
echo   FitGirl Repack Downloader - Desktop GUI
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

echo Launching Desktop GUI...
start "" ".venv\Scripts\pythonw.exe" gui_launcher.py %*
if %ERRORLEVEL% neq 0 (
    .venv\Scripts\python.exe gui_launcher.py %*
)
