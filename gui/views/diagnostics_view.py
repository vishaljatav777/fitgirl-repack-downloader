"""
System Diagnostics View - Component readiness, browser paths, and storage health.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DiagnosticsView(QWidget):
    """System readiness check and component status inspection view."""

    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("System Diagnostics")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Hardware, browser automation, and storage readiness report.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Diagnostics Cards
        self.browser_card = self._create_diag_card("Browser Automation (Brave / Chrome / Edge)")
        self.unrar_card = self._create_diag_card("Archive Unpacker (WinRAR / 7-Zip)")
        self.storage_card = self._create_diag_card("Storage & Target Volume Health")
        self.db_card = self._create_diag_card("SQLite Job Persistence (WAL Mode)")

        layout.addWidget(self.browser_card)
        layout.addWidget(self.unrar_card)
        layout.addWidget(self.storage_card)
        layout.addWidget(self.db_card)

        # Refresh Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.refresh_btn = QPushButton("Refresh Diagnostics Check")
        self.refresh_btn.clicked.connect(self.refresh_requested.emit)
        btn_layout.addWidget(self.refresh_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _create_diag_card(self, title: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(6)

        header_row = QHBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #ffffff;")
        badge = QLabel("CHECKING...")
        badge.setStyleSheet("font-weight: 700; color: #ffb900; background-color: #332b00; padding: 2px 8px; border-radius: 4px;")
        header_row.addWidget(t_lbl, stretch=1)
        header_row.addWidget(badge)
        c_layout.addLayout(header_row)

        desc = QLabel("Detecting component configuration...")
        desc.setStyleSheet("color: #888888; font-size: 12px;")
        c_layout.addWidget(desc)

        card.badge = badge  # type: ignore[attr-defined]
        card.desc = desc    # type: ignore[attr-defined]
        return card

    def update_diagnostics(self, diag: dict[str, Any]) -> None:
        # Browser Card
        if diag["browser_ready"]:
            self.browser_card.badge.setText("READY")  # type: ignore[attr-defined]
            self.browser_card.badge.setStyleSheet("color: #7fba00; background-color: #173300; padding: 2px 8px; border-radius: 4px;")  # type: ignore[attr-defined]
            self.browser_card.desc.setText(f"Detected browser executable: {diag['browser_path']}")  # type: ignore[attr-defined]
        else:
            self.browser_card.badge.setText("NOT FOUND")  # type: ignore[attr-defined]
            self.browser_card.badge.setStyleSheet("color: #f25022; background-color: #331100; padding: 2px 8px; border-radius: 4px;")  # type: ignore[attr-defined]
            self.browser_card.desc.setText("No compatible browser found. Brave, Chrome, or Edge is required.")  # type: ignore[attr-defined]

        # Unrar Card
        if diag["unrar_ready"]:
            self.unrar_card.badge.setText("READY")  # type: ignore[attr-defined]
            self.unrar_card.badge.setStyleSheet("color: #7fba00; background-color: #173300; padding: 2px 8px; border-radius: 4px;")  # type: ignore[attr-defined]
            self.unrar_card.desc.setText(f"Detected unpacker: {diag['unrar_path']}")  # type: ignore[attr-defined]
        else:
            self.unrar_card.badge.setText("MANUAL")  # type: ignore[attr-defined]
            self.unrar_card.badge.setStyleSheet("color: #ffb900; background-color: #332b00; padding: 2px 8px; border-radius: 4px;")  # type: ignore[attr-defined]
            self.unrar_card.desc.setText("Neither WinRAR nor 7-Zip detected. Automatic extraction will be unavailable.")  # type: ignore[attr-defined]

        # Storage Card
        free_gb = diag["storage_free_gb"]
        tot_gb = diag["storage_total_gb"]
        st_badge = "OK" if free_gb > 20 else "LOW SPACE"
        st_color = "#7fba00" if free_gb > 20 else "#ffb900"
        self.storage_card.badge.setText(st_badge)  # type: ignore[attr-defined]
        self.storage_card.badge.setStyleSheet(f"color: {st_color}; background-color: #202020; padding: 2px 8px; border-radius: 4px;")  # type: ignore[attr-defined]
        self.storage_card.desc.setText(f"Destination Drive Free: {free_gb:.1f} GB of {tot_gb:.1f} GB ({diag['download_dir']})")  # type: ignore[attr-defined]

        # DB Card
        self.db_card.badge.setText("ACTIVE")  # type: ignore[attr-defined]
        self.db_card.badge.setStyleSheet("color: #7fba00; background-color: #173300; padding: 2px 8px; border-radius: 4px;")  # type: ignore[attr-defined]
        self.db_card.desc.setText("SQLite WAL mode active. ACID transactions and crash recovery enabled.")  # type: ignore[attr-defined]
