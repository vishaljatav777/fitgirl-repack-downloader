import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
EXTRACT_DIR = BASE_DIR / "extracted"

# Ensure directories exist
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

# Download configuration
MAX_CONCURRENT_DOWNLOADS = 3       # Files downloaded in parallel
CHUNK_SIZE = 1024 * 1024           # 1 MB buffer
TIMEOUT = 30                       # Request timeout in seconds
MAX_RETRIES = 5                    # Retries on broken connection

# Default User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Auto-detect Browser (Brave preferred, fallback to Chrome / Edge)
POSSIBLE_BROWSER_PATHS = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

def get_browser_path() -> str:
    for path in POSSIBLE_BROWSER_PATHS:
        if os.path.exists(path):
            return path
    return ""

# Auto-detect UnRAR / 7-Zip
POSSIBLE_UNRAR_PATHS = [
    r"C:\Program Files\WinRAR\UnRAR.exe",
    r"C:\Program Files\WinRAR\WinRAR.exe",
    r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
]

def get_unrar_path() -> str:
    for path in POSSIBLE_UNRAR_PATHS:
        if os.path.exists(path):
            return path
    return ""
