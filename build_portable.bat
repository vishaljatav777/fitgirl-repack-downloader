@echo off
setlocal enabledelayedexpansion
title Build FitGirl Downloader Portable Release
cd /d "%~dp0"

echo ==============================================================
echo   FitGirl Repack Downloader - Portable Release Builder
echo ==============================================================
echo.

:: 1. Check Python virtual environment
set PYTHON=.venv\Scripts\python.exe
if not exist "%PYTHON%" (
    echo [ERROR] Virtual environment not found at .venv!
    echo Please run START.bat first to set up the environment.
    pause
    exit /b 1
)

:: 2. Ensure PyInstaller is installed
echo [1/5] Verifying packaging dependencies...
"%PYTHON%" -m pip install --quiet pyinstaller

:: 3. Clean previous build artifacts
echo [2/5] Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist\FitGirlDownloader" rmdir /s /q "dist\FitGirlDownloader"

:: 4. Run PyInstaller
echo [3/5] Compiling standalone Windows distribution with PyInstaller...
"%PYTHON%" -m PyInstaller --noconfirm --clean packaging\fitgirl_downloader.spec
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] PyInstaller compilation failed!
    pause
    exit /b %ERRORLEVEL%
)

:: 5. Copy user resources
echo [4/5] Copying release documentation and portable launchers...
if exist "dist\FitGirlDownloader" (
    copy /y "README.md" "dist\FitGirlDownloader\" >nul
    copy /y "LICENSE" "dist\FitGirlDownloader\" >nul
    copy /y "THIRD_PARTY_LICENSES.md" "dist\FitGirlDownloader\" >nul
    copy /y "packaging\launchers\START_GUI.bat" "dist\FitGirlDownloader\" >nul
    copy /y "packaging\launchers\START_CLI.bat" "dist\FitGirlDownloader\" >nul
)

:: 6. Create ZIP package
echo [5/5] Creating release ZIP archive and checksums...
"%PYTHON%" packaging\build_portable.py

echo.
echo ==============================================================
echo  BUILD SUCCESSFUL!
echo ==============================================================
echo  Portable Folder: dist\FitGirlDownloader\
echo  GUI Executable:  dist\FitGirlDownloader\FitGirlDownloader.exe
echo  CLI Executable:  dist\FitGirlDownloader\FitGirlDownloaderCLI.exe
echo  ZIP Archive:     dist\FitGirlDownloader-1.0.0-windows-x64-portable.zip
echo ==============================================================
echo.
pause
