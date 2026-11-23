"""
Backward-compatibility configuration wrapper.
Integrates with the validated settings module while preserving existing constant names.
"""

from __future__ import annotations

from pathlib import Path

from settings import (
    DEFAULT_BROWSER_PATHS as POSSIBLE_BROWSER_PATHS,
)
from settings import (
    DEFAULT_UNRAR_PATHS as POSSIBLE_UNRAR_PATHS,
)
from settings import (
    detect_executable,
    get_settings,
)

_settings = get_settings()

# Base directories
BASE_DIR: Path = _settings.base_dir
DOWNLOAD_DIR: Path = _settings.download_dir
EXTRACT_DIR: Path = _settings.extract_dir

# Concurrency & Network Configuration
MAX_CONCURRENT_DOWNLOADS: int = _settings.max_concurrent_downloads
CHUNK_SIZE: int = _settings.chunk_size
TIMEOUT: int = _settings.timeout
MAX_RETRIES: int = _settings.max_retries
USER_AGENT: str = _settings.user_agent


def ensure_directories() -> None:
    """Explicitly ensures download and extract directories exist.

    Eliminates import-time filesystem side effects.
    """
    _settings.ensure_directories()


def get_browser_path() -> str:
    """Returns detected path to Brave, Chrome, or Edge executable."""
    return detect_executable(POSSIBLE_BROWSER_PATHS, "brave") or ""


def get_unrar_path() -> str:
    """Returns detected path to WinRAR or 7-Zip executable."""
    return detect_executable(POSSIBLE_UNRAR_PATHS, "7z") or ""
