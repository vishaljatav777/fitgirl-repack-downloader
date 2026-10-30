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

## ⚙️ Command-Line Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `url` | FitGirl repack page URL (positional argument) | Optional |
| `--workers N` | Concurrent files downloading in parallel (1 to 5) | `3` |
| `--dir <path>` | Custom folder to save downloads | `./downloads` |
| `--all-optionals` | Download optional language packs (by default they are skipped) | `False` |
| `--no-extract` | Skip automatic WinRAR/7-Zip archive extraction | `False` |

### Examples:
- **Fast 4-stream download**:
  ```powershell
  python main.py "https://fitgirl-repacks.site/game-url-here/" --workers 4
  ```
- **Save to custom folder**:
  ```powershell
  python main.py "https://fitgirl-repacks.site/game-url-here/" --dir "D:\MyGames"
  ```
- **Download without auto-extracting**:
  ```powershell
  python main.py "https://fitgirl-repacks.site/game-url-here/" --no-extract
  ```

---

## 🌟 Key Features

1. **Auto-Skips Language Packs**: Skips `fg-optional-*.bin` voice packs automatically to save bandwidth.
2. **Resumable & Safe**: Skips already completed files and resumes interrupted chunks with HTTP `Range` headers.
3. **Auto-Retry**: Retries broken connections up to 3 times before failing.
4. **Cloudflare Stealth Resolver**: Resolves `fuckingfast.co` share links automatically using headless Brave/Chrome.
5. **Auto-Extract with WinRAR / 7-Zip**: Automatically checks that all parts (`part01` to `partN`) are present and complete, then unpacks the archive into `extracted/<GameTitle>`.
6. **Graceful Pause**: Press `Ctrl+C` anytime to pause safely without corrupting files.
