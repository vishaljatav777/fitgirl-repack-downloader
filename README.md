# ⚡ FitGirl Repack Downloader (Desktop GUI & Pure CLI Edition)

A high-speed, fully automated, commercial-quality Windows application to download and unpack multi-part FitGirl repacks from **fuckingfast.co**.

Features both a native **Windows 11 Fluent Desktop GUI (PySide6)** and a **Professional Terminal CLI (Typer + Rich)** powered by a shared, multi-threaded SQLite-backed core engine.

---

## 🖥️ Desktop GUI Quick Start

Double-click `START_GUI.bat` or run in PowerShell:
```powershell
python gui_launcher.py
# Or via CLI subcommand:
python main.py gui
```

### 🌟 Desktop GUI Views
1. **Dashboard**: Real-time aggregate download speed, network line throughput, total transferred data, completed games counter, quick download link bar, and live diagnostic activity log.
2. **Active Downloads**: Live stream telemetry per worker thread, overall progress bar, ETA, and cancellation controls.
3. **Queue & Catalog Search**: Built-in FitGirl repacks search engine with direct download triggers and selective optional pack options.
4. **Download History**: SQLite-backed history table with direct "Open Folder" explorer actions and one-click resumption.
5. **Archive Verification & Extraction**: Standalone folder scanner for multi-part archives (`part01` to `partN`) with one-click 7-Zip/WinRAR extraction.
6. **Settings**: Graphical configuration for download directories, worker streams (1–10), auto-extract toggles, and optional language bin filters.
7. **System Diagnostics**: Real-time readiness check of browser automation (Brave/Chrome/Edge), unpacker binaries, storage volume free space, and SQLite database integrity.
8. **Application Information**: Version info, commercial architecture overview, and legal disclaimers.

---

## ⚡ Terminal CLI Quick Start

Double-click `START.bat` or run in PowerShell:
```powershell
# Interactive wizard
python main.py

# Direct download with live terminal dashboard
python main.py download "https://fitgirl-repacks.site/call-of-duty-modern-warfare-4/"
```

### 📊 Terminal Live Telemetry Dashboard
While downloading, `main.py` renders a live, updating terminal dashboard:

```
┌─────────────────── 📊 Live Telemetry & Network Bandwidth ───────────────────┐
│ 🚀 Download Speed: 24.5 MB/s  •  🌐 Net Line: 196.0 Mbps                    │
│ ⚡ Peak Speed: 32.0 MB/s      •  📈 Average: 22.0 MB/s                      │
│ 💾 Data Transferred: 15.00 GB / 60.00 GB (25.0%)                            │
│ 📦 Parts Completed: 7 of 30 parts (23.3%)                                   │
│ ⏱️  Estimated Time (ETA): 20m 00s   ⏳ Elapsed Time: 6m 00s                 │
│ 💽 Target Drive Free: 120.0 GB (Drive C:)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
┌───────────────────── 🚀 Overall Game Download Progress ─────────────────────┐
│ ██████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  25.0% (15.00 GB / 60.00 GB)     │
└─────────────────────────────────────────────────────────────────────────────┘
┌─────────────── 🔄 Active Download Streams (Batch Workers: 3) ───────────────┐
│  Worker  Downloaded / Size     Speed       Stream Progress                  │
│  #1      1.12 GB / 1.86 GB     13.4 MB/s   ████████████░░░░░░░░  60%        │
│  #2      572.2 MB / 1.86 GB    10.0 MB/s   ██████░░░░░░░░░░░░░░  30%        │
│  #3      120.0 MB / 1.86 GB     5.2 MB/s   ██░░░░░░░░░░░░░░░░░░  10%        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Professional Typer CLI Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `python main.py` | Launch interactive wizard & menu | `python main.py` |
| `python main.py gui` | Launch native Windows PySide6 GUI | `python main.py gui` |
| `python main.py download <url>` | Download repack with live dashboard | `python main.py download "https://fitgirl..." -w 4` |
| `python main.py search <query>` | Search FitGirl catalog | `python main.py search "Elden Ring"` |
| `python main.py jobs list` | List all tracked download jobs | `python main.py jobs list --status PAUSED` |
| `python main.py jobs show <id>` | Show individual parts of a job | `python main.py jobs show "Elden Ring"` |
| `python main.py jobs resume <id>` | Resume an interrupted job | `python main.py jobs resume "Elden Ring"` |
| `python main.py jobs cancel <id>` | Cancel an active or paused job | `python main.py jobs cancel "Elden Ring"` |
| `python main.py history` | View completed download history | `python main.py history` |
| `python main.py verify <folder>` | Check multi-part RAR sequence | `python main.py verify "./downloads/Game"` |
| `python main.py extract <folder>` | Extract archive with 7z/WinRAR | `python main.py extract "./downloads/Game"` |
| `python main.py diagnostics` | Full system readiness check | `python main.py diagnostics` |
| `python main.py config show` | View current configuration | `python main.py config show` |
| `python main.py config set <k> <v>` | Update application setting | `python main.py config set max_concurrent_downloads 4` |

---

## 🛡️ Core Reliability & Safety Architecture

1. **HTTP 206 Range Resumption**: Validates server partial-content response before appending chunks, preventing corrupted `.part` downloads if a server resets.
2. **Atomic Transfers & Storage Protection**: Writes to `.part` files and commits atomic rename only after full file size matches header specifications.
3. **Path Traversal Defense (CWE-22)**: Strict `security.py` filename sanitization rejects directory traversal sequences and reserved Windows device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
4. **SQLite WAL Persistence**: Transactions stored in SQLite with Write-Ahead Logging for zero UI blocking and full recovery across system reboots.
5. **Thread Safety**: Complete separation between PySide6 GUI main thread and background worker threads (`DownloadWorker`, `ResolverWorker`, `ExtractionWorker`) communicating strictly through Qt signals and slots.

---

## 📦 Windows Portable Release

A standalone, zero-installation portable distribution is available for Windows 10/11 (x64). It bundles the complete Python runtime, PySide6 desktop GUI, Typer/Rich CLI, and Playwright automation without requiring Python to be installed.

### Quick Start (Portable)
1. Download `FitGirlDownloader-1.0.0-windows-x64-portable.zip` from Releases and extract it anywhere (e.g. `D:\FitGirlDownloader`).
2. Double-click **`FitGirlDownloader.exe`** to launch the Desktop GUI.
3. Or open a terminal inside the folder and run **`.\FitGirlDownloaderCLI.exe`** for the command-line interface.

> [!NOTE]
> All downloads, extracted archives, settings, and SQLite databases are stored in the portable application folder (or custom directory configured in Settings), keeping your system clean.

### Building the Portable Package from Source
Run the included build script:
```powershell
# Using PowerShell:
.\build_portable.ps1

# Or via Command Prompt / Batch:
build_portable.bat
```
The output will be compiled into `dist/FitGirlDownloader/` and packaged into `dist/FitGirlDownloader-1.0.0-windows-x64-portable.zip`.

### ⚠️ Packaging & System Limitations
- **OS Support**: 64-bit Windows 10 or Windows 11.
- **Browser Requirement for Cloudflare**: Uses the local system browser (Microsoft Edge, Google Chrome, or Brave) to resolve `fuckingfast.co` share links via Playwright CDP. Microsoft Edge is pre-installed on all Windows 10/11 systems.
- **Archive Extraction**: Auto-extraction requires either WinRAR (`UnRAR.exe` / `WinRAR.exe`) or 7-Zip (`7z.exe`) installed on the host system. If not present, downloads complete safely and can be extracted manually.

---

## 🧪 Testing & Verification

Run the full automated test suite (unit tests, CLI integration tests, and headless GUI smoke tests):
```powershell
.venv\Scripts\ruff.exe check .
.venv\Scripts\mypy.exe logger.py settings.py exceptions.py config.py security.py storage.py downloader.py services.py terminal_ui.py cli.py main.py gui_launcher.py gui/ tests/
.venv\Scripts\pytest -v
```
All 99 tests pass with zero errors.
