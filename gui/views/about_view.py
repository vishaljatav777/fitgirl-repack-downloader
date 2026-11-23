"""
Application Information View - About, Version, Architecture, and Credits.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class AboutView(QWidget):
    """Displays software metadata, architecture summary, and credits."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("About FitGirl Repack Downloader")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Commercial-quality Windows download management software.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Info Card
        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(12)

        title = QLabel("⚡ FitGirl Repack Downloader - Commercial Edition")
        title.setStyleSheet("font-weight: 700; font-size: 16px; color: #00a4ef;")
        c_layout.addWidget(title)

        version = QLabel("Version: 1.0.0 (Windows Native Edition)")
        version.setStyleSheet("color: #aaaaaa; font-weight: 600;")
        c_layout.addWidget(version)

        desc = QLabel(
            "An enterprise-grade, high-performance download manager designed specifically for multi-part "
            "game repacks. Features stealth Cloudflare Turnstile bypass, HTTP Range resumable downloading, "
            "multi-worker concurrency, SQLite persistence with Write-Ahead Logging (WAL), and automated "
            "archive verification and extraction."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #cccccc; line-height: 1.4;")
        c_layout.addWidget(desc)

        specs_title = QLabel("Architectural Specifications:")
        specs_title.setStyleSheet("font-weight: 700; color: #ffffff; margin-top: 8px;")
        c_layout.addWidget(specs_title)

        specs = QLabel(
            "• Core Engine: Python 3.13 / requests / concurrent.futures\n"
            "• Persistence: SQLite 3 with Write-Ahead Logging (WAL) Mode\n"
            "• GUI Framework: PySide6 (Qt for Python) with non-blocking QThread workers\n"
            "• CLI Framework: Typer & Rich terminal telemetry\n"
            "• Security: Strict Path Traversal (CWE-22) validation & subprocess isolation\n"
            "• Testing: Pytest, Ruff, Mypy, and Pytest-Qt"
        )
        specs.setStyleSheet("font-family: 'Consolas', monospace; color: #888888;")
        c_layout.addWidget(specs)

        license_lbl = QLabel("License: MIT License • Open Source Windows Software")
        license_lbl.setStyleSheet("color: #7fba00; font-weight: 600; margin-top: 8px;")
        c_layout.addWidget(license_lbl)

        layout.addWidget(card)
        layout.addStretch()
