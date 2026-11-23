"""
Download History View - SQLite-backed persistent download records.
"""

from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from terminal_ui import format_bytes


class HistoryView(QWidget):
    """Displays completed and past download jobs from SQLite."""

    resume_job_requested = Signal(str)  # job_id

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Download History")
        header.setObjectName("viewHeader")
        subtitle = QLabel("All past downloads recorded in persistent SQLite database.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Game Title", "Parts", "Size", "Status", "Destination Folder"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, stretch=1)

        # Actions Row
        btn_layout = QHBoxLayout()
        self.open_folder_btn = QPushButton("Open Folder in Explorer")
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        self.resume_btn = QPushButton("Resume Incomplete Job")
        self.resume_btn.setObjectName("primaryButton")
        self.resume_btn.clicked.connect(self._on_resume)
        btn_layout.addWidget(self.open_folder_btn)
        btn_layout.addWidget(self.resume_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def display_jobs(self, jobs: list[Any]) -> None:
        self.table.setRowCount(len(jobs))
        self._jobs = jobs
        for row, j in enumerate(jobs):
            self.table.setItem(row, 0, QTableWidgetItem(j.title))
            self.table.setItem(row, 1, QTableWidgetItem(str(j.total_files)))
            self.table.setItem(row, 2, QTableWidgetItem(format_bytes(j.total_bytes)))
            self.table.setItem(row, 3, QTableWidgetItem(j.status.value))
            self.table.setItem(row, 4, QTableWidgetItem(j.download_dir))

    def _on_open_folder(self) -> None:
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            item = self.table.item(row, 4)
            if item:
                folder = item.text()
                if os.path.exists(folder):
                    os.startfile(folder)  # Windows native file explorer opener

    def _on_resume(self) -> None:
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            job = self._jobs[row]
            self.resume_job_requested.emit(job.id)
