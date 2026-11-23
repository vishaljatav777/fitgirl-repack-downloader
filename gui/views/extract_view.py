"""
Archive Verification & Extraction View.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ExtractView(QWidget):
    """Allows verifying multi-part RAR sequences and triggering 7-Zip/WinRAR extraction."""

    verify_requested = Signal(Path)
    extract_requested = Signal(Path, Path)  # download_dir, extract_dir

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Archive Verification & Extraction")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Inspect multi-part RAR/7z part integrity and extract game setups.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Folder Picker Card
        card = QFrame()
        card.setObjectName("card")
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(10)

        c_layout.addWidget(QLabel("Folder containing downloaded parts (.part01.rar, etc.):"))
        in_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText("Select folder...")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse)
        in_layout.addWidget(self.folder_input, stretch=1)
        in_layout.addWidget(self.browse_btn)
        c_layout.addLayout(in_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        self.verify_btn = QPushButton("Verify Archive Sequence")
        self.verify_btn.clicked.connect(self._on_verify)
        self.extract_btn = QPushButton("Extract Archive")
        self.extract_btn.setObjectName("primaryButton")
        self.extract_btn.clicked.connect(self._on_extract)
        btn_layout.addWidget(self.verify_btn)
        btn_layout.addWidget(self.extract_btn)
        btn_layout.addStretch()
        c_layout.addLayout(btn_layout)

        layout.addWidget(card)

        # Status Label
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(self.status_lbl)

        # Log Output
        layout.addWidget(QLabel("📜 Extraction Progress Log:"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText("Extraction logs will stream here in real-time...")
        layout.addWidget(self.log_view, stretch=1)

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Downloaded Parts")
        if folder:
            self.folder_input.setText(folder)

    def _on_verify(self) -> None:
        p_str = self.folder_input.text().strip()
        if p_str:
            self.verify_requested.emit(Path(p_str))

    def _on_extract(self) -> None:
        p_str = self.folder_input.text().strip()
        if p_str:
            p = Path(p_str)
            self.extract_requested.emit(p, p.parent / "extracted" / p.name)

    def set_verification_result(self, is_complete: bool, parts_count: int, missing: list[int]) -> None:
        if is_complete and parts_count > 0:
            self.status_lbl.setText(f"✔ Archive sequence verified complete! ({parts_count} parts found)")
            self.status_lbl.setStyleSheet("color: #7fba00; font-weight: 600;")
        else:
            if missing:
                self.status_lbl.setText(f"✘ Incomplete archive! Missing part numbers: {missing}")
            else:
                self.status_lbl.setText("✘ No multi-part RAR files found in folder.")
            self.status_lbl.setStyleSheet("color: #f25022; font-weight: 600;")

    def append_log(self, text: str) -> None:
        self.log_view.append(text)
