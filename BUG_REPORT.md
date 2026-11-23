# BUG REPORT & DEFECT CATALOG
**Target System**: FitGirl Repack Downloader  
**Date**: November 23, 2026  
**Auditor**: Lead Python Engineer & Senior Architect  
**Status**: Confirmed Audit Catalog  
**Governing Standard**: `Agents.md` Section 9 (Debugging & Quality Assurance)

---

## 1. Summary of Identified Defects

| Defect ID | Affected Component | Classification | Severity | Impact |
| :--- | :--- | :--- | :--- | :--- |
| **BUG-01** | `downloader.py` | Confirmed Bug | **CRITICAL** | Silent multi-gigabyte archive corruption on resumed downloads. |
| **BUG-02** | `scraper.py` / `downloader.py` | Confirmed Bug | **HIGH** | Path Traversal vulnerability allowing arbitrary filesystem write. |
| **BUG-03** | `downloader.py` | Confirmed Bug | **MEDIUM** | Arbitrary 2 GB placeholder size distorts telemetry, progress, and ETA. |
| **BUG-04** | `config.py` | Confirmed Bug | **MEDIUM** | Import-time side effects create directories on disk during tests. |
| **BUG-05** | `START.bat` | Confirmed Bug | **MEDIUM** | Missing Playwright browser bootstrap causes fatal crash on clean systems. |
| **BUG-06** | `downloader.py` | Confirmed Bug | **LOW** | Telemetry `completed_files` double-counts skipped files. |
| **RISK-01** | `downloader.py` | Potential Risk | **MEDIUM** | Mutex lock contention on every 1 MB chunk write degrades download speed. |
| **RISK-02** | `resolver.py` | Potential Risk | **MEDIUM** | Synchronous Playwright execution blocks worker threads on Cloudflare stall. |
| **RISK-03** | `resolver.py` | Potential Risk | **LOW** | Direct non-atomic write to `resolved_cache.json` risks cache corruption. |
| **RISK-04** | `extractor.py` | Potential Risk | **MEDIUM** | Verification fails to catch truncated or corrupted non-zero parts. |
| **RISK-05** | `.github/workflows/` | Potential Risk | **LOW** | Duplicate CI workflows waste runner minutes; test only on Ubuntu. |

---

## 2. Confirmed Bugs (Detailed Analysis)

### BUG-01: Silent Archive Corruption via Missing HTTP 206 Verification on Resume
- **File**: `downloader.py`
- **Lines**: 209-235
- **Classification**: Confirmed Bug
- **Severity**: **CRITICAL**
- **Evidence**:
  ```python
  if existing_size > 0 and supports_range:
      headers["Range"] = f"bytes={existing_size}-"
      mode = "ab"
  ...
  with self.session.get(
      item.direct_url,
      headers=headers,
      stream=True,
      timeout=TIMEOUT
  ) as resp:
      if resp.status_code not in (200, 206):
          raise RuntimeError(f"HTTP Status {resp.status_code}")

      with open(file_path, mode) as f:
          for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
              if chunk:
                  f.write(chunk)
  ```
- **Root Cause**:
  When resuming an interrupted download (`existing_size > 0`), the client requests `Range: bytes={existing_size}-` and opens the file in append mode (`mode = "ab"`).
  However, the code allows `resp.status_code` to be **either 200 or 206**. If the mirror server ignores the `Range` request header (due to CDN caching rules, token renewal, or mirror configuration) and returns `HTTP 200 OK`, the server transmits the entire file from byte 0.
  Because the local file is opened in `"ab"` mode, the complete stream is appended onto the existing partial file. For example, an interrupted 1.5 GB part resumes and receives 2.0 GB, resulting in a 3.5 GB corrupted file that fails archive extraction.
- **Recommended Solution**:
  Strictly validate that when `headers.get("Range")` is sent, `resp.status_code == 206`. If the server responds with `200 OK`, switch `mode = "wb"`, reset `current_downloaded = 0`, and truncate the local file to prevent corruption:
  ```python
  if "Range" in headers:
      if resp.status_code == 206:
          mode = "ab"
      elif resp.status_code == 200:
          mode = "wb"
          current_downloaded = 0
      else:
          raise RuntimeError(f"Unexpected status code {resp.status_code} for Range request")
  ```

---

### BUG-02: Path Traversal via Unsanitized Download Filename (CWE-22)
- **File**: `scraper.py` (lines 46-50, 84-92) & `downloader.py` (line 177)
- **Classification**: Confirmed Bug / Security Vulnerability
- **Severity**: **HIGH**
- **Evidence**:
  In `scraper.py`:
  ```python
  if "#" in href:
      base_url, fragment = href.split("#", 1)
      filename = fragment
  else:
      base_url = href
      
  if not filename:
      filename = text or base_url.split("/")[-1]
  ```
  In `downloader.py`:
  ```python
  file_path = self.dest_dir / item.filename
  ```
- **Root Cause**:
  The filename is extracted directly from the URL hash fragment (`#fragment`) or the anchor tag's text content without sanitization. In Python `pathlib.Path`, `Path("downloads/game") / "../../Windows/System32/evil.dll"` resolves to `Windows/System32/evil.dll`.
  If an attacker controls or proxies a repack page or link fragment, they can escape the designated download directory and write arbitrary files anywhere the current user has write permissions.
- **Recommended Solution**:
  Enforce strict filename sanitization using `os.path.basename`, stripping leading dots, path separators (`/`, `\`), null bytes, and Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`):
  ```python
  import re
  from pathlib import Path

  def sanitize_filename(filename: str) -> str:
      base = Path(filename).name
      # Strip directory traversal characters and invalid Windows characters
      clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', base).strip(" .")
      if not clean or clean.upper() in {"CON", "PRN", "AUX", "NUL"}:
          return "unnamed_part.bin"
      return clean
  ```

---

### BUG-03: Arbitrary 2 GB Placeholder Distorting Telemetry & ETA
- **File**: `downloader.py`
- **Lines**: 316-318
- **Classification**: Confirmed Bug
- **Severity**: **MEDIUM**
- **Evidence**:
  ```python
  if item.size_bytes > 0:
      self._file_total_map[item.filename] = item.size_bytes
  else:
      self._file_total_map[item.filename] = 2 * 1024 * 1024 * 1024  # 2 GB default part estimate
  ```
- **Root Cause**:
  Before downloading, `item.size_bytes` is often `0` because remote sizes are only resolved when `download_file` executes. `download_all` arbitrarily assigns 2 GB to every part.
  For a repack with thirty 500 MB parts, `total_bytes` is estimated as 60 GB instead of 15 GB. The overall progress bar displays 25% when the game is 100% complete, and ETA calculations fluctuate wildly.
- **Recommended Solution**:
  Query remote headers (`HEAD` or `bytes=0-0`) during the resolution phase or use the FitGirl page metadata to populate accurate part sizes. When sizes are unknown, explicitly flag `total_bytes` as indeterminate rather than assuming arbitrary numbers.

---

### BUG-04: Import-Time Filesystem Directory Creation
- **File**: `config.py`
- **Lines**: 10-11
- **Classification**: Confirmed Bug
- **Severity**: **MEDIUM**
- **Evidence**:
  ```python
  DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
  EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
  ```
- **Root Cause**:
  Directories are created at module top-level execution. Whenever any module (`scraper`, `main`, `extractor`) is imported during unit testing or CLI `--help`, `downloads/` and `extracted/` directories are silently created in the working directory.
- **Recommended Solution**:
  Encapsulate directory creation inside an explicit initialization function (e.g., `ensure_directories()`) called only during actual application execution, never at import time.

---

### BUG-05: Missing Playwright Chromium Bootstrap in `START.bat`
- **File**: `START.bat`
- **Lines**: 11-17
- **Classification**: Confirmed Bug
- **Severity**: **MEDIUM**
- **Evidence**:
  ```batch
  .venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
  ```
- **Root Cause**:
  The setup script installs `playwright` via pip, but never executes `playwright install chromium`. While the application attempts to use local Brave/Chrome/Edge, if the user has non-standard paths or only installed Python, `resolver.py` crashes with `RuntimeError: No compatible browser found`.
- **Recommended Solution**:
  Add an automatic browser check and bootstrap step in `START.bat` or within the application startup diagnostics to install Playwright Chromium if no compatible local browser is detected.

---

### BUG-06: Telemetry `completed_files` Double Increment on Skip vs Finish
- **File**: `downloader.py`
- **Lines**: 193-195, 265-267, 344-360
- **Classification**: Confirmed Bug
- **Severity**: **LOW**
- **Evidence**:
  Line 194:
  ```python
  with self._lock:
      self.telemetry.completed_files += 1
  return True
  ```
  Line 266:
  ```python
  with self._lock:
      self.telemetry.completed_files += 1
  ```
- **Root Cause**:
  `self.telemetry.completed_files` tracks completed files across threads, but `completed_items` in `download_all` only appends when `future.result()` is truthy. When downloads are retried or resumed, inconsistencies arise between the telemetry counter and the job completion state.
- **Recommended Solution**:
  Centralize job and part status updates inside a single state tracking entity or database transaction rather than ad-hoc counter increments across worker threads.

---

## 3. Potential Risks & Architectural Weaknesses

### RISK-01: Lock Contention on High-Speed Multi-Worker Chunk Writes
- **File**: `downloader.py` (lines 253-261)
- **Risk**: Every 1 MB chunk write across up to 5 worker threads acquires `self._lock` to update `_file_bytes_map` and construct an `ActiveFileProgress` dataclass.
- **Impact**: On high-speed NVMe and multi-gigabit connections, lock contention introduces CPU overhead and throttles aggregate I/O throughput.
- **Mitigation**: Use thread-local byte counters and let the background telemetry heartbeat thread poll atomic progress snapshots without locking per chunk.

---

### RISK-02: Synchronous Playwright Execution Blocking Calling Threads
- **File**: `resolver.py` (lines 149-179)
- **Risk**: `sync_playwright()` blocks the executing thread. If Cloudflare initiates an interactive challenge or the page stalls, the thread is blocked for up to 30 seconds.
- **Impact**: In a GUI or interactive environment, calling this synchronously freezes the user interface.
- **Mitigation**: Move the resolver to a dedicated background `QThread` or `QRunnable` with asynchronous Playwright (`async_playwright`) and cooperative cancellation.

---

### RISK-03: Non-Atomic Overwrite of `resolved_cache.json`
- **File**: `resolver.py` (lines 54-59)
- **Risk**: Cache writes use standard `open(CACHE_FILE, "w")` without atomic replacement (`tempfile` + `os.replace`).
- **Impact**: If the process is terminated while writing the JSON cache, the file becomes corrupted and subsequent runs fail or wipe cache data.
- **Mitigation**: Implement atomic file writing using a temporary file and atomic rename.

---

### RISK-04: Superficial Archive Part Verification
- **File**: `extractor.py` (lines 46-52)
- **Risk**: Verification only checks that file size is non-zero (`stat().st_size > 0`).
- **Impact**: A partially downloaded or truncated 500 MB part will pass verification. When extraction begins, WinRAR fails midway, leaving extracted partial games in an unusable state.
- **Mitigation**: Implement magic byte validation for RAR/7z headers and run non-destructive integrity testing (`unrar t` / `7z t`) before extracting.

---

### RISK-05: Redundant CI Workflows Testing Only on Linux
- **File**: `.github/workflows/python-app.yml` & `python-package.yml`
- **Risk**: Two nearly identical workflows run on every push and pull request, testing exclusively on `ubuntu-latest`.
- **Impact**: Wastes GitHub Actions quota; fails to validate Windows-specific paths, binaries, or GUI dependencies.
- **Mitigation**: Consolidate into a single parameterized workflow running on `windows-latest` alongside `ubuntu-latest`.
