@echo off
title FitGirl Repack Downloader (Terminal CLI)
cd /d "%~dp0"

echo ==============================================================
echo   FitGirl Repack Downloader - Terminal CLI
echo ==============================================================
echo.

if exist "FitGirlDownloaderCLI.exe" (
    "FitGirlDownloaderCLI.exe" %*
) else if exist "fitgirl-cli.exe" (
    "fitgirl-cli.exe" %*
) else (
    echo [ERROR] FitGirlDownloaderCLI.exe was not found in this folder.
    echo Please ensure all files were extracted properly.
    pause
    exit /b 1
)

if %ERRORLEVEL% neq 0 (
    echo.
    echo Execution finished with code %ERRORLEVEL%.
    pause
)

