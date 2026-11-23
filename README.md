# ⚡ FitGirl Repack Terminal Downloader (Pure CLI Edition)

A high-speed, fully automated, pure Python terminal tool to download multi-part FitGirl repacks from **fuckingfast.co**.  
**No GUI or IDM required. Everything runs directly inside your terminal with real-time live telemetry.**

---

## 🚀 Quick Start (In PowerShell)

### Step 1: Activate Virtual Environment
```powershell
.venv\Scripts\Activate.ps1
```

### Step 2: Run `main.py`
You can run it in two ways:

#### A. Interactive Mode
```powershell
python main.py
```
This prints the diagnostics and asks you to paste any FitGirl repack URL or search for games.

#### B. Direct One-Line Download
```powershell
python main.py "https://fitgirl-repacks.site/call-of-duty-modern-warfare-4/"
```

---

## 📊 Terminal Live Telemetry Dashboard

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
┌────────────────────────── 📜 Recent Activity Feed ──────────────────────────┐
│ [15:40:01] ✔ Completed CoD_MW4...part07.rar                                 │
│ [15:40:02] Downloading: CoD_MW4...part08.rar (1.86 GB)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Professional Typer CLI Commands

The CLI is powered by Typer and Rich, offering rich subcommands alongside backward-compatible execution:

| Command | Description | Example |
| :--- | :--- | :--- |
| `python main.py` | Launch interactive wizard & menu | `python main.py` |
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

### Download Flags
- `--workers <1-10>`: Concurrent file streams (default: 3).
- `--dir <path>`: Custom destination folder.
- `--no-extract`: Skip auto-extracting archives after download.
- `--all-optionals`: Download optional voice/language packs.
- `--non-interactive`: Disable Live dashboard for clean plain-text log streaming (ideal for CI/scripts).

---

## 🌟 Key Features

1. **Auto-Skips Language Packs**: Skips `fg-optional-*.bin` voice packs automatically to save bandwidth.
2. **Resumable & Safe**: Skips already completed files and resumes interrupted chunks with HTTP `Range` headers.
3. **Auto-Retry**: Retries broken connections up to 3 times before failing.
4. **Cloudflare Stealth Resolver**: Resolves `fuckingfast.co` share links automatically using headless Brave/Chrome.
5. **Auto-Extract with WinRAR / 7-Zip**: Automatically checks that all parts (`part01` to `partN`) are present and complete, then unpacks the archive into `extracted/<GameTitle>`.
6. **Graceful Pause**: Press `Ctrl+C` anytime to pause safely without corrupting files.

---

## 🛠️ Developer & Quality Tooling (Phase 1 Foundation)

The repository implements strict engineering quality standards defined in `pyproject.toml` and `Agents.md`:

### Running Tests
```powershell
pytest
```
*Current test suite: 23 unit tests covering exceptions, settings validation, structured logging, scraper parsing, progress formatting, and archive part verification.*

### Code Formatting & Linting (Ruff)
```powershell
ruff check .
```

### Static Type Checking (Mypy)
```powershell
mypy logger.py settings.py exceptions.py config.py tests/ scraper.py resolver.py downloader.py extractor.py main.py
```

---

## 📚 Technical Documentation & Architecture

Comprehensive technical specifications and audit reports are available in the repository root:
- [PROJECT_AUDIT.md](PROJECT_AUDIT.md) — Exhaustive 12-domain codebase audit.
- [ARCHITECTURE.md](ARCHITECTURE.md) — Target commercial architecture, SQLite schema, state machine, and PySide6/Typer design.
- [BUG_REPORT.md](BUG_REPORT.md) — Catalog of confirmed defects vs potential risks.
- [SECURITY_AUDIT.md](SECURITY_AUDIT.md) — Threat model, Path Traversal analysis, and mitigation matrix.
- [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) — Phased engineering transformation plan.

