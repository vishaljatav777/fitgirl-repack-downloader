<#
.SYNOPSIS
    Builds the standalone portable Windows release of FitGirl Repack Downloader.
.DESCRIPTION
    Cleans previous build folders, runs PyInstaller with fitgirl_downloader.spec,
    copies essential documentation, and packages a zip-ready distribution into dist/.
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "  FitGirl Repack Downloader - Portable Release Builder (PS)   " -ForegroundColor Cyan
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host ""

$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment not found at $PythonExe. Please run START.bat first!"
}

# 1. Verify PyInstaller
Write-Host "[1/5] Verifying packaging dependencies..." -ForegroundColor Green
& $PythonExe -m pip install --quiet pyinstaller

# 2. Clean build directories
Write-Host "[2/5] Cleaning previous build artifacts..." -ForegroundColor Green
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist\FitGirlDownloader") { Remove-Item -Recurse -Force "dist\FitGirlDownloader" }

# 3. Execute PyInstaller build
Write-Host "[3/5] Compiling standalone Windows distribution with PyInstaller..." -ForegroundColor Green
& $PythonExe -m PyInstaller --noconfirm --clean packaging\fitgirl_downloader.spec

# 4. Copy documentation and launchers
Write-Host "[4/5] Copying release documentation and portable launchers..." -ForegroundColor Green
$DistApp = "dist\FitGirlDownloader"
if (Test-Path $DistApp) {
    Copy-Item "README.md" -Destination $DistApp -Force
    Copy-Item "LICENSE" -Destination $DistApp -Force
    Copy-Item "THIRD_PARTY_LICENSES.md" -Destination $DistApp -Force
    Copy-Item "packaging\launchers\START_GUI.bat" -Destination $DistApp -Force
    Copy-Item "packaging\launchers\START_CLI.bat" -Destination $DistApp -Force
}

# 5. Create ZIP package and checksums
Write-Host "[5/5] Creating release ZIP archive and checksums..." -ForegroundColor Green
& $PythonExe packaging\build_portable.py

Write-Host ""
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "  BUILD SUCCESSFUL!                                           " -ForegroundColor Green
Write-Host "==============================================================" -ForegroundColor Cyan
Write-Host "  Portable Folder: $DistApp"
Write-Host "  GUI Executable:  $DistApp\FitGirlDownloader.exe"
Write-Host "  CLI Executable:  $DistApp\FitGirlDownloaderCLI.exe"
Write-Host "==============================================================" -ForegroundColor Cyan
