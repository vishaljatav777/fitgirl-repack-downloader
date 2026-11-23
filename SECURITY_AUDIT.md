# SECURITY AUDIT REPORT
**Target System**: FitGirl Repack Downloader  
**Evaluation Date**: November 23, 2026  
**Auditor**: Senior Software Architect & Security Lead  
**Classification**: Strict Security Assessment  
**Governing Standard**: `Agents.md` Section 6 (Security & Trust Boundaries)

---

## 1. Threat Model & Trust Boundaries

The FitGirl Repack Downloader interacts with third-party web services, dynamic browser automation environments, multi-part mirror hosts, and external system binaries.

```text
[ UNTRUSTED INTERNET ]
       │  • External Web Pages (fitgirl-repacks.site)
       │  • Mirror Host & Cloudflare Challenge (fuckingfast.co)
       │  • Download Streams & Filename Headers
       ▼
┌────────────────────────────────────────────────────────┐
│ APPLICATION TRUST BOUNDARY                             │
│                                                        │
│   1. Input Sanitization (URLs, Filenames, Parameters)  │
│   2. Network Client (TLS Validation, Range Guard)      │
│   3. Process Isolation (Playwright Chromium, Archiver) │
│   4. Local Persistence (SQLite, Filesystem Writes)     │
└────────────────────────────────────────────────────────┘
       ▼
[ HOST SYSTEM & USER ENVIRONMENT ]
       │  • Operating System Filesystem (C:\, AppData)
       │  • External Executables (WinRAR, 7-Zip, Browser)
```

---

## 2. Vulnerability Assessment Findings

### SEC-01: Path Traversal Vulnerability (CWE-22)
- **Severity**: **HIGH** (CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:N/I:H/A:H)
- **Affected File**: `scraper.py` (lines 46, 85) & `downloader.py` (line 177)
- **Vulnerability Description**:
  The application extracts filenames directly from URL hash fragments and HTML link texts:
  ```python
  # scraper.py
  if "#" in href:
      base_url, fragment = href.split("#", 1)
      filename = fragment
  ```
  The target file path is constructed via simple path joining:
  ```python
  # downloader.py
  file_path = self.dest_dir / item.filename
  ```
  In Python, `Path("/dest/dir") / "../../Windows/System32/payload.dll"` resolves to `/Windows/System32/payload.dll`.
  If a scraped web page or mirror URL is tampered with or manipulated to include relative path traversal sequences (`../`), the downloader will write files outside the intended download directory, potentially overwriting critical user or system files.
- **Remediation**:
  1. Enforce strict sanitization using `Path(filename).name` to strip all directory components.
  2. Reject filenames containing path separators (`/`, `\`) or null bytes (`\x00`).
  3. Validate that the resolved target path is strictly within `dest_dir`:
     ```python
     target_path = (self.dest_dir / sanitized_name).resolve()
     if not str(target_path).startswith(str(self.dest_dir.resolve())):
         raise SecurityError(f"Path traversal detected: {filename}")
     ```
  4. Sanitize Windows reserved file names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`).

---

### SEC-02: Promotion & Execution Boundary of Untrusted Executables (CWE-73 / CWE-494)
- **Severity**: **MEDIUM**
- **Affected File**: `extractor.py` (lines 113-115)
- **Vulnerability Description**:
  After extracting archives, `extractor.py` automatically searches for executables:
  ```python
  setups = list(self.extract_dir.glob("setup*.exe")) + list(self.extract_dir.glob("*.exe"))
  if setups:
      console.print(f"[bold cyan]Installer found:[/] [bold yellow]{setups[0]}[/]")
  ```
  `Agents.md` Section 6 explicitly states:
  > *"Treat downloaded files as untrusted. Never automatically execute downloaded installers."*
  While the current code prints the installer path rather than executing it via `subprocess`, promoting and identifying unverified `.exe` files extracted from third-party repacks creates a false sense of security. If future modifications add auto-launching, users would be vulnerable to executing malicious or compromised binaries.
- **Remediation**:
  - Never automatically launch downloaded `.exe` files.
  - Present explicit security warnings when informing users that an installer has been extracted.
  - Suggest hash verification against known repack release databases where available.

---

### SEC-03: Subprocess Argument Injection Boundaries (CWE-88)
- **Severity**: **LOW**
- **Affected File**: `extractor.py` (lines 83-100)
- **Vulnerability Description**:
  `ArchiveVerifierExtractor` executes external extraction tools using `subprocess.run(cmd, ...)`:
  ```python
  cmd = [
      self.unrar_path,
      "x",
      "-y",
      f"-o{str(self.extract_dir)}",
      str(first_part)
  ]
  ```
  Because `shell=True` is NOT used, standard command injection via shell metacharacters (`&`, `|`, `;`) is prevented.
  However, if an archive part filename begins with a hyphen (e.g. `-u-`), command-line utilities like `7z.exe` or `UnRAR.exe` may interpret the filename as a command-line switch rather than an input file.
- **Remediation**:
  Use the standard argument termination delimiter `--` supported by 7-Zip and command-line tools to signify the end of command options before passing file paths:
  ```python
  cmd = [self.unrar_path, "x", "-y", f"-o{self.extract_dir}", "--", str(first_part)]
  ```

---

### SEC-04: Transport Layer Security & Redirect Validation (CWE-295 / CWE-918)
- **Severity**: **LOW**
- **Affected File**: `scraper.py`, `downloader.py`
- **Audit Assessment**:
  1. **TLS Certificate Verification**: `requests.Session` is used without modifying `verify=False`. TLS verification remains active and enforced by default, complying with `Agents.md` Section 6 ("Never disable TLS verification").
  2. **Redirect Validation**: `requests.get` and `requests.head` permit redirects (`allow_redirects=True`). When downloading from mirror services, redirects must be validated to ensure they remain within HTTPS and do not redirect to local host interfaces (`127.0.0.1`, `localhost`, `169.254.169.254`).
- **Remediation**:
  Implement a custom redirect handler that strictly requires `https://` schemes and blocks loopback or private RFC 1918 IP addresses.

---

### SEC-05: Hardcoded Credentials & Secrets Review (CWE-798)
- **Severity**: **NONE / PASS**
- **Audit Assessment**:
  No hardcoded API keys, bearer tokens, passwords, or personal access tokens were identified in any source files or git history. The cache file `resolved_cache.json` stores only transient public mirror direct download URLs and timestamps.

---

### SEC-06: Browser Automation Security & Privacy
- **Severity**: **LOW**
- **Affected File**: `resolver.py`
- **Audit Assessment**:
  The resolver launches Chromium with:
  ```python
  args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
  ```
  1. `--no-sandbox`: While often used in headless Linux containers, using `--no-sandbox` on Windows weakens browser sandbox protection against malicious JavaScript exploits hosted on third-party sites.
  2. The browser instance creates an in-memory browser context (`browser.new_context`) without reusing personal user profiles, preventing leakage of existing user session cookies or stored browser credentials.
- **Remediation**:
  Remove the `--no-sandbox` argument on Windows environments where standard sandboxing operates cleanly.

---

## 3. Security Recommendations & Hardening Matrix

| Priority | Vulnerability / Concern | Required Hardening Action |
| :--- | :--- | :--- |
| **P0** | Path Traversal (CWE-22) | Implement `sanitize_filename()` and assert destination boundary containment. |
| **P0** | Archive Integrity Check | Validate RAR/7z magic bytes before passing files to unpackers. |
| **P1** | Subprocess Safety (CWE-88) | Insert `--` argument switch delimiter in all archiver CLI invocations. |
| **P1** | Untrusted Installer Policy | Add explicit user warning against auto-executing downloaded `.exe` files. |
| **P2** | Browser Sandbox | Remove `--no-sandbox` flag on Windows desktop executions. |
| **P2** | Atomic Cache Writes | Replace direct JSON file writes with atomic temporary file renaming. |
