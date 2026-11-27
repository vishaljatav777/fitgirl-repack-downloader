# Changelog

All notable changes to the **FitGirl Repack Downloader** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-25

### Added
- **PySide6 Native Desktop GUI**: Windows 11 Fluent dark theme desktop application with 8 modular views:
  - `DashboardView`: Aggregate metrics (speed, network throughput, transferred data, completed games) and activity feed.
  - `ActiveDownloadsView`: Multi-worker stream table, overall progress bar, and cancellation controls.
  - `QueueView`: FitGirl repacks catalog search with one-click download enqueuing.
  - `HistoryView`: SQLite-backed job history table with native Windows Explorer folder opener and resume triggers.
  - `ExtractView`: Multi-part archive sequence verifier and automated 7-Zip/WinRAR extraction trigger.
  - `SettingsView`: Interactive sliders, spinboxes, and directory pickers (`QFileDialog`).
  - `DiagnosticsView`: Live subsystem readiness status badges (Browser, Unpacker, Storage, SQLite).
  - `AboutView`: Architectural specifications, thread-safety disclosures, and license terms.
- **Thread-Safe Worker Layer**: Background `QThread` workers (`DownloadWorker`, `ResolverWorker`, `ExtractionWorker`) communicating strictly via Qt signals and slots.
- **Typer & Rich CLI**: Full command-line suite (`download`, `search`, `jobs`, `history`, `verify`, `extract`, `diagnostics`, `config`, `gui`) with real-time terminal telemetry dashboard.
- **SQLite WAL Persistence**: Embedded SQLite job storage with Write-Ahead Logging for zero UI blocking and full recovery across system restarts.
- **Reliability & Resilience Engine**:
  - HTTP Range (206 vs 200) resume validation preventing archive corruption.
  - Atomic `.part` file commit with pre-flight file size checks.
  - Exponential backoff retry policies for transient network drops and rate limits (HTTP 429).
  - Disk space guard (`DiskSpaceError`) enforcing a 50 MB volume safety buffer.
- **Security Hardening**:
  - Path traversal (CWE-22) sanitization protecting against directory escape sequences and Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).
  - Archive magic bytes verification for RAR5 and 7-Zip headers.
- **Automated Test Suite**: 99 tests covering unit models, services, storage recovery, downloader reliability, and headless GUI smoke tests (`pytest-qt`).
- **Packaging & Distribution**:
  - PyInstaller multi-target build specification generating `FitGirlDownloader.exe` (GUI) and `FitGirlDownloaderCLI.exe` (CLI).
  - Inno Setup installer script (`installer.iss`) for standard Windows installation.
  - Portable distribution generator (`build_portable.py`) producing self-contained zip archives with SHA-256 checksums.
  - GitHub Actions CI/CD workflows for quality linting, multi-OS testing, and automated release publication.
