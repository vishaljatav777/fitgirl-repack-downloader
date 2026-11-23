"""
Settings View - User preferences, custom folders, and worker concurrency limits.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from settings import AppSettings


class SettingsView(QWidget):
    """Configuration management view."""

    settings_saved = Signal(dict)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("Settings")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Configure download directories, concurrency, and automated extraction.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Settings Form Card
        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(14)

        # Download Directory
        c_layout.addWidget(QLabel("Default Download Directory:"))
        d_layout = QHBoxLayout()
        self.download_dir_input = QLineEdit()
        self.browse_d_btn = QPushButton("Browse...")
        self.browse_d_btn.clicked.connect(self._on_browse_download)
        d_layout.addWidget(self.download_dir_input, stretch=1)
        d_layout.addWidget(self.browse_d_btn)
        c_layout.addLayout(d_layout)

        # Extract Directory
        c_layout.addWidget(QLabel("Default Extraction Directory:"))
        e_layout = QHBoxLayout()
        self.extract_dir_input = QLineEdit()
        self.browse_e_btn = QPushButton("Browse...")
        self.browse_e_btn.clicked.connect(self._on_browse_extract)
        e_layout.addWidget(self.extract_dir_input, stretch=1)
        e_layout.addWidget(self.browse_e_btn)
        c_layout.addLayout(e_layout)

        # Concurrency Slider
        c_layout.addWidget(QLabel("Concurrent Download Workers (Streams):"))
        slider_layout = QHBoxLayout()
        self.workers_slider = QSlider(Qt.Orientation.Horizontal)
        self.workers_slider.setRange(1, 10)
        self.workers_slider.setValue(3)
        self.workers_lbl = QLabel("3 workers")
        self.workers_lbl.setStyleSheet("font-weight: 600; color: #00a4ef;")
        self.workers_slider.valueChanged.connect(lambda v: self.workers_lbl.setText(f"{v} workers"))
        slider_layout.addWidget(self.workers_slider, stretch=1)
        slider_layout.addWidget(self.workers_lbl)
        c_layout.addLayout(slider_layout)

        # Auto-Extract Toggle
        self.auto_extract_cb = QCheckBox("Automatically verify and extract multi-part archives after download")
        self.auto_extract_cb.setChecked(True)
        c_layout.addWidget(self.auto_extract_cb)

        # Include Optionals Toggle
        self.optionals_cb = QCheckBox("Download optional voice & selective language packs by default")
        self.optionals_cb.setChecked(False)
        c_layout.addWidget(self.optionals_cb)

        layout.addWidget(card)

        # Save Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

    def load_settings(self, settings: AppSettings) -> None:
        self.download_dir_input.setText(str(settings.download_dir))
        self.extract_dir_input.setText(str(settings.extract_dir))
        self.workers_slider.setValue(settings.max_concurrent_downloads)
        self.workers_lbl.setText(f"{settings.max_concurrent_downloads} workers")
        self.auto_extract_cb.setChecked(settings.auto_extract)
        self.optionals_cb.setChecked(settings.include_optionals)

    def _on_browse_download(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Download Directory")
        if folder:
            self.download_dir_input.setText(folder)

    def _on_browse_extract(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Extraction Directory")
        if folder:
            self.extract_dir_input.setText(folder)

    def _on_save(self) -> None:
        data = {
            "download_dir": Path(self.download_dir_input.text().strip()),
            "extract_dir": Path(self.extract_dir_input.text().strip()),
            "max_concurrent_downloads": self.workers_slider.value(),
            "auto_extract": self.auto_extract_cb.isChecked(),
            "include_optionals": self.optionals_cb.isChecked(),
        }
        self.settings_saved.emit(data)
        QMessageBox.information(self, "Settings Saved", "Application settings updated successfully!")
