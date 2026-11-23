"""
Application settings and environment configuration with validation.
Prevents import-time side effects (no automatic directory creation).
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from exceptions import ConfigurationError

# Default browser execution paths on Windows
DEFAULT_BROWSER_PATHS: list[str] = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

# Default UnRAR / 7-Zip execution paths on Windows
DEFAULT_UNRAR_PATHS: list[str] = [
    r"C:\Program Files\WinRAR\UnRAR.exe",
    r"C:\Program Files\WinRAR\WinRAR.exe",
    r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
]


def detect_executable(candidates: list[str], which_name: str | None = None) -> str | None:
    """Finds an executable path from candidates or system PATH."""
    for path in candidates:
        if os.path.isfile(path):
            return path
    if which_name:
        found = shutil.which(which_name)
        if found:
            return found
    return None


@dataclass
class AppSettings:
    """Validated configuration for the FitGirl Downloader application."""

    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent)
    download_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "downloads")
    extract_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "extracted")
    max_concurrent_downloads: int = 3
    chunk_size: int = 1024 * 1024  # 1 MB
    timeout: int = 30  # seconds
    max_retries: int = 5
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    browser_path: str | None = None
    unrar_path: str | None = None
    auto_extract: bool = True
    include_optionals: bool = False

    def __post_init__(self) -> None:
        """Validates configuration parameters."""
        self.download_dir = Path(self.download_dir)
        self.extract_dir = Path(self.extract_dir)
        self.base_dir = Path(self.base_dir)

        if not (1 <= self.max_concurrent_downloads <= 10):
            raise ConfigurationError(
                f"max_concurrent_downloads must be between 1 and 10, got {self.max_concurrent_downloads}"
            )

        if self.chunk_size < 64 * 1024:
            raise ConfigurationError(
                f"chunk_size must be at least 64 KB (65536 bytes), got {self.chunk_size}"
            )

        if self.timeout < 5:
            raise ConfigurationError(
                f"timeout must be at least 5 seconds, got {self.timeout}"
            )

        if self.max_retries < 0:
            raise ConfigurationError(
                f"max_retries cannot be negative, got {self.max_retries}"
            )

        # Detect default paths if not explicitly provided
        if self.browser_path is None:
            self.browser_path = detect_executable(DEFAULT_BROWSER_PATHS, "brave") or ""
        if self.unrar_path is None:
            self.unrar_path = detect_executable(DEFAULT_UNRAR_PATHS, "7z") or ""

    def ensure_directories(self) -> None:
        """Safely creates target download and extraction directories on demand."""
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir.mkdir(parents=True, exist_ok=True)


# Global default settings instance (lazy directories)
_DEFAULT_SETTINGS: AppSettings | None = None


def get_settings() -> AppSettings:
    """Returns the singleton application settings instance."""
    global _DEFAULT_SETTINGS
    if _DEFAULT_SETTINGS is None:
        _DEFAULT_SETTINGS = AppSettings()
    return _DEFAULT_SETTINGS
