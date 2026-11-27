@echo off
title FitGirl Repack Downloader (Desktop GUI)
cd /d "%~dp0"

echo Launching FitGirl Repack Downloader Desktop GUI...
if exist "FitGirlDownloader.exe" (
    start "" "FitGirlDownloader.exe" %*
) else (
    echo [ERROR] FitGirlDownloader.exe was not found in this folder.
    echo Please ensure all files were extracted properly.
    pause
)

