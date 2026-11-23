"""
Dashboard View - Metrics, Quick Download, and Activity Feed.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DashboardView(QWidget):
    """Primary dashboard displaying aggregate statistics and quick start."""

    start_download_requested = Signal(str)  # Emits URL to download

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = QLabel("Dashboard")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Overview of download telemetry, network throughput, and quick links.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Metric Cards Row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(14)

        self.speed_card = self._create_metric_card("DOWNLOAD SPEED", "0.0 MB/s", "#00a4ef")
        self.net_card = self._create_metric_card("NETWORK LINE", "0.0 Mbps", "#7fba00")
        self.transferred_card = self._create_metric_card("DATA TRANSFERRED", "0.0 B", "#f25022")
        self.completed_card = self._create_metric_card("COMPLETED GAMES", "0", "#ffb900")

        metrics_layout.addWidget(self.speed_card)
        metrics_layout.addWidget(self.net_card)
        metrics_layout.addWidget(self.transferred_card)
        metrics_layout.addWidget(self.completed_card)
        layout.addLayout(metrics_layout)

        # Quick Download Card
        quick_card = QFrame()
        quick_card.setObjectName("card")
        quick_layout = QVBoxLayout(quick_card)
        quick_layout.setSpacing(10)

        quick_title = QLabel("⚡ Quick Download")
        quick_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #ffffff;")
        quick_desc = QLabel("Paste any FitGirl repack URL or FuckingFast mirror link to start:")
        quick_desc.setStyleSheet("color: #888888;")

        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://fitgirl-repacks.site/game-title/ ...")
        self.start_btn = QPushButton("Start Download")
        self.start_btn.setObjectName("primaryButton")
        self.start_btn.clicked.connect(self._on_start_clicked)

        input_layout.addWidget(self.url_input, stretch=1)
        input_layout.addWidget(self.start_btn)

        quick_layout.addWidget(quick_title)
        quick_layout.addWidget(quick_desc)
        quick_layout.addLayout(input_layout)
        layout.addWidget(quick_card)

        # Recent Activity Feed
        feed_title = QLabel("📜 Live Activity Feed")
        feed_title.setStyleSheet("font-weight: 700; font-size: 14px; color: #ffffff; margin-top: 10px;")
        layout.addWidget(feed_title)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Live download and engine events will appear here...")
        layout.addWidget(self.log_view, stretch=1)

    def _create_metric_card(self, title: str, default_val: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("metricCard")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(12, 12, 12, 12)
        c_layout.setSpacing(6)

        t_lbl = QLabel(title)
        t_lbl.setObjectName("metricTitle")
        v_lbl = QLabel(default_val)
        v_lbl.setObjectName("metricValue")
        v_lbl.setStyleSheet(f"color: {color};")

        c_layout.addWidget(t_lbl)
        c_layout.addWidget(v_lbl)
        card.value_label = v_lbl  # type: ignore[attr-defined]
        return card

    def _on_start_clicked(self) -> None:
        url = self.url_input.text().strip()
        if url:
            self.start_download_requested.emit(url)
            self.url_input.clear()

    def update_metrics(self, speed_mb: float, net_mbps: float, transferred_str: str, completed_count: int) -> None:
        self.speed_card.value_label.setText(f"{speed_mb:.1f} MB/s")  # type: ignore[attr-defined]
        self.net_card.value_label.setText(f"{net_mbps:.1f} Mbps")  # type: ignore[attr-defined]
        self.transferred_card.value_label.setText(transferred_str)  # type: ignore[attr-defined]
        self.completed_card.value_label.setText(str(completed_count))  # type: ignore[attr-defined]

    def append_log(self, text: str) -> None:
        self.log_view.append(text)
