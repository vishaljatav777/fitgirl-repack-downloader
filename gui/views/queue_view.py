"""
Download Queue & Catalog Search View.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class QueueView(QWidget):
    """Allows searching FitGirl repacks, inspecting parts, and selecting downloads."""

    search_requested = Signal(str)
    download_requested = Signal(str)  # URL of repack to fetch & download

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        header = QLabel("Download Queue & Catalog Search")
        header.setObjectName("viewHeader")
        subtitle = QLabel("Search repack catalog, select language packs, and enqueue downloads.")
        subtitle.setObjectName("viewSubtitle")
        layout.addWidget(header)
        layout.addWidget(subtitle)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search game titles (e.g. Elden Ring, Cyberpunk)...")
        self.search_input.returnPressed.connect(self._on_search)
        self.search_btn = QPushButton("Search Catalog")
        self.search_btn.setObjectName("primaryButton")
        self.search_btn.clicked.connect(self._on_search)

        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)

        # Search Results Table
        self.results_table = QTableWidget(0, 2)
        self.results_table.setHorizontalHeaderLabels(["Game Title", "URL"])
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.doubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.results_table, stretch=1)

        # Enqueue Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.download_btn = QPushButton("Download Selected Game")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.clicked.connect(self._on_download_selected)
        btn_layout.addWidget(self.download_btn)
        layout.addLayout(btn_layout)

    def _on_search(self) -> None:
        q = self.search_input.text().strip()
        if q:
            self.search_requested.emit(q)

    def display_results(self, results: list[dict[str, str]]) -> None:
        self.results_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self.results_table.setItem(row, 0, QTableWidgetItem(r["title"]))
            self.results_table.setItem(row, 1, QTableWidgetItem(r["url"]))

    def _on_download_selected(self) -> None:
        selected = self.results_table.selectedItems()
        if selected:
            row = selected[0].row()
            item = self.results_table.item(row, 1)
            if item:
                self.download_requested.emit(item.text())

    def _on_item_double_clicked(self) -> None:
        self._on_download_selected()
