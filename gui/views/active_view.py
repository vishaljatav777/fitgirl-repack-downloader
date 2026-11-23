"""
Active Downloads View - Master Progress, Concurrent Worker Streams, and Controls.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from terminal_ui import format_bytes, format_seconds


class ActiveDownloadsView(QWidget):
    """Displays real-time multi-stream download meters and controls."""

    pause_requested = Signal()
    resume_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Active Downloads")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Real-time telemetry and individual concurrent worker streams.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Master Game Card
        self.game_card = QFrame()
        self.game_card.setObjectName("card")
        g_layout = QVBoxLayout(self.game_card)
        g_layout.setSpacing(10)

        top_row = QHBoxLayout()
        self.title_lbl = QLabel("No active download in progress")
        self.title_lbl.setStyleSheet("font-weight: 700; font-size: 15px; color: #ffffff;")
        self.eta_lbl = QLabel("ETA: --:--")
        self.eta_lbl.setStyleSheet("color: #ffb900; font-weight: 600;")
        top_row.addWidget(self.title_lbl, stretch=1)
        top_row.addWidget(self.eta_lbl)
        g_layout.addLayout(top_row)

        self.overall_bar = QProgressBar()
        self.overall_bar.setValue(0)
        g_layout.addWidget(self.overall_bar)

        info_row = QHBoxLayout()
        self.bytes_lbl = QLabel("0.0 B / 0.0 B (0%)")
        self.bytes_lbl.setStyleSheet("color: #888888;")
        self.speed_lbl = QLabel("0.0 MB/s")
        self.speed_lbl.setStyleSheet("color: #00a4ef; font-weight: 600;")
        info_row.addWidget(self.bytes_lbl, stretch=1)
        info_row.addWidget(self.speed_lbl)
        g_layout.addLayout(info_row)

        # Control Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.pause_btn = QPushButton("Pause Download")
        self.pause_btn.clicked.connect(self.pause_requested.emit)
        self.resume_btn = QPushButton("Resume")
        self.resume_btn.setObjectName("primaryButton")
        self.resume_btn.clicked.connect(self.resume_requested.emit)
        self.resume_btn.setVisible(False)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("color: #ff6b6b;")
        self.cancel_btn.clicked.connect(self.cancel_requested.emit)

        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.resume_btn)
        btn_row.addWidget(self.cancel_btn)
        g_layout.addLayout(btn_row)

        layout.addWidget(self.game_card)

        # Streams Table
        streams_title = QLabel("🔄 Active Concurrent Download Streams")
        streams_title.setStyleSheet("font-weight: 700; font-size: 14px; margin-top: 8px;")
        layout.addWidget(streams_title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Worker", "File Name", "Progress", "Speed", "Downloaded / Total"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

    def set_game_title(self, title: str) -> None:
        self.title_lbl.setText(f"🎮 {title}")

    def update_telemetry(self, telemetry: Any) -> None:
        # Master bar
        pct = (telemetry.downloaded_bytes / telemetry.total_bytes * 100) if telemetry.total_bytes > 0 else 0.0
        self.overall_bar.setValue(int(pct))
        cur_str = format_bytes(telemetry.downloaded_bytes)
        tot_str = format_bytes(telemetry.total_bytes)
        self.bytes_lbl.setText(f"{cur_str} / {tot_str} ({pct:.1f}%) • {telemetry.completed_files}/{telemetry.total_files} parts complete")

        speed_mb = telemetry.current_speed_bytes / (1024 ** 2)
        self.speed_lbl.setText(f"{speed_mb:.1f} MB/s")
        self.eta_lbl.setText(f"ETA: {format_seconds(telemetry.eta_seconds)}")

        # Streams Table
        active_items = list(telemetry.active_files.values())
        self.table.setRowCount(len(active_items))
        for row, af in enumerate(active_items):
            self.table.setItem(row, 0, QTableWidgetItem(f"Worker #{row + 1}"))
            self.table.setItem(row, 1, QTableWidgetItem(af.filename))

            pct_bar = QProgressBar()
            pct_bar.setValue(int(af.percentage * 100))
            pct_bar.setStyleSheet("max-height: 14px;")
            self.table.setCellWidget(row, 2, pct_bar)

            sp_str = f"{af.speed_bytes_sec / (1024 ** 2):.1f} MB/s"
            self.table.setItem(row, 3, QTableWidgetItem(sp_str))

            dl_str = f"{format_bytes(af.downloaded_bytes)} / {format_bytes(af.total_bytes)}"
            self.table.setItem(row, 4, QTableWidgetItem(dl_str))
