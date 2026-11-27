# 📥 Installation & Deployment Guide

This guide covers all methods for installing and running **FitGirl Repack Downloader** on Microsoft Windows.

---

## 🖥️ System Requirements

- **Operating System:** Microsoft Windows 10 or Windows 11 (64-bit)
- **Memory (RAM):** 4 GB minimum (8 GB recommended)
- **Disk Space:** 300 MB free space for the application, plus sufficient space for downloaded games
- **Prerequisites:**
  - A Chromium-based browser installed (**Brave**, **Google Chrome**, or **Microsoft Edge**) for Cloudflare link resolution.
  - (Optional) **7-Zip** or **WinRAR** installed for automated extraction.

---

## Option 1: Windows Installer (Recommended for Users)

The standard Windows installer configures shortcuts, file associations, and an uninstaller.

1. Download `FitGirlDownloader-Setup-1.0.0.exe` from the [Releases page](https://github.com/vishaljatav777/fitgirl-repack-downloader/releases).
2. Double-click the installer executable.
3. Follow the setup wizard to choose your installation directory (default: `C:\Program Files\FitGirl Downloader`).
4. (Optional) Check **Create a desktop shortcut**.
5. Click **Finish**.
6. Launch **FitGirl Repack Downloader** from your Desktop shortcut or Start Menu.

---

## Option 2: Standalone Portable ZIP (No Installation Required)

Ideal for USB drives or running without administrative privileges:

1. Download `FitGirlDownloader-1.0.0-windows-x64-portable.zip` from Releases.
2. Verify the archive's SHA-256 hash matches `checksums.sha256`:
   ```powershell
   Get-FileHash -Algorithm SHA256 .\FitGirlDownloader-1.0.0-windows-x64-portable.zip
   ```
3. Extract the ZIP archive to any folder (e.g. `D:\Tools\FitGirlDownloader`).
4. Inside the extracted folder:
   - Double-click `FitGirlDownloader.exe` to launch the **Desktop GUI**.
   - Or open PowerShell and run `.\FitGirlDownloaderCLI.exe` for the **Terminal CLI**.
   - Or double-click `START_GUI.bat` / `START_CLI.bat`.

---

## Option 3: Developer / Source Installation

For developers who want to run or contribute to the Python source code:

### 1. Clone the Repository
```powershell
git clone https://github.com/vishaljatav777/fitgirl-repack-downloader.git
cd fitgirl-repack-downloader
```

### 2. Set Up Python Virtual Environment (Python 3.10+)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```powershell
pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev]"
playwright install chromium
```

### 4. Launch Application
```powershell
# Launch PySide6 Desktop GUI
python gui_launcher.py
# Or via CLI
python main.py gui

# Launch Interactive CLI
python main.py

# Direct CLI Download
python main.py download "https://fitgirl-repacks.site/game-title/"
```

### 5. Run Automated Tests
```powershell
# Linting
ruff check .

# Static Type Checking
mypy logger.py settings.py exceptions.py config.py security.py storage.py downloader.py services.py terminal_ui.py cli.py main.py gui_launcher.py gui/ tests/

# Full Test Suite with Coverage
pytest -v --cov=. --cov-report=term-missing
```

---

## ⚙️ Upgrading & Uninstallation

- **Upgrading via Installer:** Run the newer `FitGirlDownloader-Setup-X.X.X.exe`. It will safely replace existing program files while preserving your download folder and SQLite job database.
- **Uninstallation:** Navigate to **Windows Settings > Apps > Installed apps**, locate **FitGirl Repack Downloader**, and click **Uninstall**.
