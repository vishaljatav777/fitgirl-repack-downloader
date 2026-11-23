"""
Structured application logging for the FitGirl Repack Downloader.
Provides consistent formatting, level filtering, console handlers,
and rotating file logging.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from collections.abc import Callable
from pathlib import Path

# Default log format with microsecond precision and component identity
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_ROOT_LOGGER_INITIALIZED = False


class CallbackHandler(logging.Handler):
    """Logging handler that routes formatted log records to a custom callback."""

    def __init__(self, callback: Callable[[str], None]):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.callback(msg)
        except Exception:
            self.handleError(record)


def configure_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    console: bool = True,
    fmt: str = DEFAULT_LOG_FORMAT,
    datefmt: str = DEFAULT_DATE_FORMAT,
) -> logging.Logger:
    """Configures the root application logger.

    Args:
        level: Minimum log severity level (e.g. logging.DEBUG, logging.INFO).
        log_file: Optional path to write rotating file logs.
        console: Whether to attach a stdout console handler.
        fmt: Log record format string.
        datefmt: Date/time format string.

    Returns:
        The configured root logger.
    """
    global _ROOT_LOGGER_INITIALIZED

    root_logger = logging.getLogger("fitgirl")
    root_logger.setLevel(level)

    # Avoid duplicate handlers on re-configuration
    root_logger.handlers.clear()

    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # 10 MB max per file, 5 rotated backups
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _ROOT_LOGGER_INITIALIZED = True
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Returns a namespaced child logger under 'fitgirl'.

    Example:
        >>> logger = get_logger("downloader")
        >>> logger.name
        'fitgirl.downloader'
    """
    global _ROOT_LOGGER_INITIALIZED
    if not _ROOT_LOGGER_INITIALIZED:
        # Initialize default console logging if not explicitly configured
        configure_logging(level=logging.INFO, console=False)

    if name.startswith("fitgirl."):
        return logging.getLogger(name)
    return logging.getLogger(f"fitgirl.{name}")
