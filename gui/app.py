"""
Application lifecycle and GUI runner for PySide6 desktop.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from logger import get_logger

logger = get_logger("gui.app")


def run_gui() -> int:
    """Launches the PySide6 desktop application."""
    logger.info("Initializing PySide6 Desktop GUI...")
    app = QApplication(sys.argv)
    app.setApplicationName("FitGirl Repack Downloader")
    app.setOrganizationName("DeepMind")

    window = MainWindow()
    window.show()

    return app.exec()
