from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from logger import CallbackHandler, configure_logging, get_logger


def test_get_logger_prefix():
    log = get_logger("scraper")
    assert log.name == "fitgirl.scraper"

    log_with_prefix = get_logger("fitgirl.downloader")
    assert log_with_prefix.name == "fitgirl.downloader"


def test_configure_logging_console():
    root = configure_logging(level=logging.DEBUG, console=True)
    assert root.level == logging.DEBUG
    assert len(root.handlers) >= 1
    for h in list(root.handlers):
        h.close()
        root.removeHandler(h)


def test_configure_logging_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "app.log"
        root = configure_logging(level=logging.INFO, log_file=log_file, console=False)
        test_logger = get_logger("test")
        test_logger.info("Test message for file verification")

        # Flush and explicitly close file handlers to release Windows file locks
        for h in list(root.handlers):
            h.flush()
            h.close()
            root.removeHandler(h)

        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test message for file verification" in content


def test_callback_handler():
    captured = []

    def callback(msg: str):
        captured.append(msg)

    handler = CallbackHandler(callback)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    record = logging.LogRecord(
        name="fitgirl.test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Callback test message",
        args=(),
        exc_info=None,
    )
    handler.emit(record)
    assert len(captured) == 1
    assert captured[0] == "Callback test message"
    handler.close()
