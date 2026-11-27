# ⚡ FitGirl Repack Downloader — Version 1.0.0 Release Notes

**Release Version:** `v1.0.0`  
**Release Date:** November 25, 2026  
**Target Platform:** Microsoft Windows (Windows 10, Windows 11 — 64-bit)  
**License:** MIT  

---

## 🚀 Overview

FitGirl Repack Downloader `v1.0.0` is the inaugural commercial-quality release of the automated multi-part download manager designed specifically for FitGirl game repacks hosted on `fuckingfast.co`.

Featuring both a native **Windows 11 Fluent Desktop GUI (PySide6)** and a **Terminal CLI (Typer + Rich)**, the application provides enterprise-grade reliability, resumable chunk transfers, stealth Cloudflare Turnstile link resolution, and automated archive integrity verification and extraction.

---

## 🌟 Key Highlights

### 1. Dual Interface Architecture
- **Windows Desktop GUI (`FitGirlDownloader.exe`)**:
  - Windows 11 Fluent dark theme with high-DPI scaling support.
  - 8 modular views: Dashboard, Active Downloads, Queue & Repack Catalog Search, Download History, Archive Verification & Extraction, Settings, System Diagnostics, and About.
  - Non-blocking asynchronous worker threads (`QThread`) with Qt signal/slot telemetry.
  - Graceful cooperative application shutdown (`closeEvent`) with SQLite transaction safety.
- **Terminal CLI (`FitGirlDownloaderCLI.exe`)**:
  - Typer and Rich command suite (`download`, `search`, `jobs`, `history`, `verify`, `extract`, `diagnostics`, `config`, `gui`).
  - Real-time 4Hz terminal telemetry dashboard rendering live speeds, ETA, network line throughput, and multi-stream progress bars.

### 2. High-Performance Resumable Download Engine
- **HTTP Range (RFC 7233) Resumption**: Validates server HTTP 206 Partial Content responses before appending data. If a server ignores range requests and sends HTTP 200, the partial file is cleanly truncated to prevent corruption.
- **Atomic `.part` File Commit**: Streams chunks to temporary `.part` files with size validation before atomic rename (`os.replace`) to final destination.
- **Dynamic Exponential Backoff**: Automatic retries for transient HTTP errors and rate-limiting (HTTP 429 backoff using `Retry-After` headers).
- **Disk Space Pre-Flight Guard**: Rejects downloads with `DiskSpaceError` if the destination volume lacks sufficient space plus a 50 MB safety margin.

### 3. Persistent SQLite Job Management
- **Write-Ahead Logging (WAL)**: Embedded SQLite database with concurrent reader/writer access and transactional ACID integrity.
- **Job Recovery Across Restarts**: Preserves individual part states (`PENDING`, `DOWNLOADING`, `COMPLETED`, `FAILED`). Resuming a job skips already-completed parts and resumes interrupted chunks.
- **Link Expiry Re-Resolution**: Automatically re-resolves expired direct download links when resuming jobs after system downtime.

### 4. Hardened Security & Archive Integrity
- **Path Traversal Defense (CWE-22)**: Strict sanitization rejects `../`, absolute paths, and Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
- **Archive Magic Bytes Inspection**: Pre-extraction validation verifying RAR5 (`52 61 72 21 1A 07 01 00`) and 7-Zip (`37 7A BC AF 27 1C`) binary signatures.
- **Safe Subprocess Unpacking**: Sanitized command arguments with explicit `--` boundary delimiters invoking WinRAR or 7-Zip. Downloaded game installers (`setup.exe`) are never executed automatically.

---

## 📦 Distribution Packages

| Package | Format | Description |
|---|---|---|
| **Installer** | `FitGirlDownloader-Setup-1.0.0.exe` | Standard Windows Setup wizard with Desktop & Start Menu shortcuts and uninstaller. |
| **Portable ZIP** | `FitGirlDownloader-1.0.0-windows-x64-portable.zip` | Standalone portable folder. Extract and run without installation. |
| **Source Archive** | `v1.0.0.zip` / `v1.0.0.tar.gz` | Clean source code repository. |

---

## 🔒 Verification & Integrity (SHA-256)

All binary distribution packages are published with cryptographic SHA-256 checksums available in `checksums.sha256`:

```text
621762469ded5e005895bef6dd7dd75fb2e867efd8fac125e14f7b110d6a0776  FitGirlDownloader-1.0.0-windows-x64-portable.zip
```

---

## 🧪 Quality Assurance & Test Matrix

- **Unit & Integration Tests**: 99 automated tests passed (100% pass rate).
- **Code Coverage**: >= 83% overall coverage (Service facade: 94%, Extractor: 99%, Downloader: 85%, Storage: 96%).
- **Static Analysis**: Ruff (0 lint errors) and Mypy (strict type checking across 43 source files).
- **Clean Environment Test**: Standalone binary execution verified outside development environment on Windows 11.
