"""
Main Application Window for the FitGirl Repack Downloader GUI.
Features sidebar navigation, QStackedWidget view switching, non-blocking workers,
and a safe cooperative shutdown sequence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gui.styles import DARK_THEME_QSS
from gui.views.about_view import AboutView
from gui.views.active_view import ActiveDownloadsView
from gui.views.dashboard_view import DashboardView
from gui.views.diagnostics_view import DiagnosticsView
from gui.views.extract_view import ExtractView
from gui.views.history_view import HistoryView
from gui.views.queue_view import QueueView
from gui.views.settings_view import SettingsView
from gui.workers import DownloadWorker, ExtractionWorker, ResolverWorker
from logger import get_logger
from scraper import GameRepack
from services import DownloadManagerService

logger = get_logger("gui.main_window")


class MainWindow(QMainWindow):
    """Primary desktop application window."""

    def __init__(self, service: DownloadManagerService | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.service = service or DownloadManagerService()
        self.active_download_worker: DownloadWorker | None = None
        self.active_resolver_worker: ResolverWorker | None = None
        self.active_extraction_worker: ExtractionWorker | None = None

        self.setWindowTitle("FitGirl Repack Downloader - Commercial Edition")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_ui()
        self._load_initial_data()

    def _init_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar Navigation
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        s_layout = QVBoxLayout(sidebar)
        s_layout.setContentsMargins(10, 16, 10, 16)
        s_layout.setSpacing(6)

        # App Brand
        brand_btn = QPushButton("⚡ FitGirl Repacks")
        brand_btn.setStyleSheet("font-size: 15px; font-weight: 800; color: #00a4ef; padding: 10px; text-align: left; background: transparent; border: none;")
        s_layout.addWidget(brand_btn)
        s_layout.addSpacing(10)

        # Nav Buttons
        self.nav_buttons: list[QPushButton] = []
        nav_items = [
            ("📊  Dashboard", 0),
            ("⚡  Active Downloads", 1),
            ("📥  Download Queue", 2),
            ("📜  Download History", 3),
            ("📦  Verify & Extract", 4),
            ("⚙️  Settings", 5),
            ("🩺  Diagnostics", 6),
            ("ℹ️  About", 7),
        ]

        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self.switch_view(i))
            s_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        s_layout.addStretch()
        main_layout.addWidget(sidebar)

        # 2. Stacked Content Views
        self.stack = QStackedWidget()
        self.dashboard_view = DashboardView()
        self.active_view = ActiveDownloadsView()
        self.queue_view = QueueView()
        self.history_view = HistoryView()
        self.extract_view = ExtractView()
        self.settings_view = SettingsView()
        self.diagnostics_view = DiagnosticsView()
        self.about_view = AboutView()

        self.stack.addWidget(self.dashboard_view)    # 0
        self.stack.addWidget(self.active_view)       # 1
        self.stack.addWidget(self.queue_view)        # 2
        self.stack.addWidget(self.history_view)      # 3
        self.stack.addWidget(self.extract_view)      # 4
        self.stack.addWidget(self.settings_view)     # 5
        self.stack.addWidget(self.diagnostics_view)  # 6
        self.stack.addWidget(self.about_view)        # 7

        main_layout.addWidget(self.stack, stretch=1)

        # Connect View Signals
        self.dashboard_view.start_download_requested.connect(self.start_download_flow)
        self.queue_view.search_requested.connect(self._on_search_catalog)
        self.queue_view.download_requested.connect(self.start_download_flow)
        self.history_view.resume_job_requested.connect(self._on_resume_job)
        self.extract_view.verify_requested.connect(self._on_verify_archive)
        self.extract_view.extract_requested.connect(self._on_extract_archive)
        self.settings_view.settings_saved.connect(self._on_save_settings)
        self.diagnostics_view.refresh_requested.connect(self._on_refresh_diagnostics)
        self.active_view.pause_requested.connect(self._on_pause_download)
        self.active_view.cancel_requested.connect(self._on_cancel_download)

        # Default View: Dashboard (0)
        self.switch_view(0)

    def switch_view(self, index: int) -> None:
        """Switches the active content view in QStackedWidget."""
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        # View-specific refreshes
        if index == 3:
            self._refresh_history()
        elif index == 6:
            self._on_refresh_diagnostics()

    def _load_initial_data(self) -> None:
        self.settings_view.load_settings(self.service.settings)
        self.diagnostics_view.update_diagnostics(self.service.get_diagnostics())
        self._refresh_history()

    def _refresh_history(self) -> None:
        jobs = self.service.list_jobs()
        self.history_view.display_jobs(jobs)

        # Update dashboard metrics
        completed = [j for j in jobs if j.status.value == "COMPLETED"]
        total_dl = sum(j.downloaded_bytes for j in jobs)
        from terminal_ui import format_bytes
        self.dashboard_view.update_metrics(
            speed_mb=0.0,
            net_mbps=0.0,
            transferred_str=format_bytes(total_dl),
            completed_count=len(completed)
        )

    def start_download_flow(self, url: str) -> None:
        """Initiates the scrape -> resolve -> download pipeline."""
        self.dashboard_view.append_log(f"Fetching repack metadata for: {url}")
        self.switch_view(1)  # Switch to Active Downloads view

        try:
            repack = self.service.scrape_repack(url)
            self.active_view.set_game_title(repack.title)
            self.dashboard_view.append_log(f"Found repack: {repack.title} ({len(repack.parts)} parts)")

            items = list(repack.parts)
            if self.service.settings.include_optionals and repack.optionals:
                items.extend(repack.optionals)

            # Spawn ResolverWorker
            self.dashboard_view.append_log("Launching stealth resolver in background worker...")
            self.active_resolver_worker = ResolverWorker(self.service, items, parent=self)
            self.active_resolver_worker.progress.connect(
                lambda cur, tot, name: self.dashboard_view.append_log(f"Resolving ({cur}/{tot}): {name}")
            )
            self.active_resolver_worker.resolved.connect(lambda res: self._on_links_resolved(repack, res))
            self.active_resolver_worker.failed.connect(self._on_worker_error)
            self.active_resolver_worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Scraper Error", f"Failed to scrape repack:\n{e}")

    def _on_links_resolved(self, repack: GameRepack, resolved_items: list[Any]) -> None:
        valid_resolved = [i for i in resolved_items if i.direct_url]
        self.dashboard_view.append_log(f"✔ Successfully resolved {len(valid_resolved)}/{len(resolved_items)} direct links!")

        if not valid_resolved:
            QMessageBox.warning(self, "Resolution Incomplete", "Could not resolve any direct links. Aborting download.")
            return

        # Spawn DownloadWorker
        self.active_download_worker = DownloadWorker(
            service=self.service,
            repack=repack,
            items=valid_resolved,
            parent=self,
        )
        self.active_download_worker.telemetry_updated.connect(self._on_telemetry_updated)
        self.active_download_worker.log_emitted.connect(self.dashboard_view.append_log)
        self.active_download_worker.job_completed.connect(self._on_download_completed)
        self.active_download_worker.job_failed.connect(self._on_worker_error)
        self.active_download_worker.job_paused.connect(self._on_download_paused)
        self.active_download_worker.start()

    def _on_telemetry_updated(self, telemetry: Any) -> None:
        self.active_view.update_telemetry(telemetry)
        from terminal_ui import format_bytes
        self.dashboard_view.update_metrics(
            speed_mb=telemetry.current_speed_bytes / (1024 ** 2),
            net_mbps=telemetry.net_bandwidth_mbps,
            transferred_str=format_bytes(telemetry.downloaded_bytes),
            completed_count=telemetry.completed_files
        )

    def _on_download_completed(self, items: list[Any]) -> None:
        self.dashboard_view.append_log(f"✔ All {len(items)} download parts finished successfully!")
        self._refresh_history()

        # Trigger auto-extract if enabled
        if self.service.settings.auto_extract:
            target_dir = self.service.settings.download_dir / self.active_view.title_lbl.text().replace("🎮 ", "")
            if target_dir.exists():
                self._on_extract_archive(target_dir, self.service.settings.extract_dir / target_dir.name)

        QMessageBox.information(self, "Download Complete", "All game parts have finished downloading!")

    def _on_download_paused(self) -> None:
        self.dashboard_view.append_log("⏹ Download paused. All progress preserved safely in SQLite.")
        self.active_view.pause_btn.setVisible(False)
        self.active_view.resume_btn.setVisible(True)
        self._refresh_history()

    def _on_pause_download(self) -> None:
        if self.active_download_worker and self.active_download_worker.isRunning():
            self.active_download_worker.stop()

    def _on_cancel_download(self) -> None:
        reply = QMessageBox.question(
            self, "Cancel Download", "Are you sure you want to cancel this download?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.active_download_worker and self.active_download_worker.isRunning():
                self.active_download_worker.stop()
            self.dashboard_view.append_log("Download canceled by user.")

    def _on_resume_job(self, job_id: str) -> None:
        self.dashboard_view.append_log(f"Resuming job from history: {job_id}")
        self.switch_view(1)
        job = self.service.get_job(job_id)
        if job:
            self.active_view.set_game_title(job.title)
            # Use background worker to resume
            repack = GameRepack(title=job.title, page_url=job.page_url)
            parts = self.service.get_job_parts(job_id)
            from scraper import DownloadItem
            items = [DownloadItem(filename=p.filename, share_url=p.share_url, direct_url=p.direct_url, size_bytes=p.total_bytes) for p in parts]
            self._on_links_resolved(repack, items)

    def _on_search_catalog(self, query: str) -> None:
        try:
            results = self.service.search_repacks(query)
            self.queue_view.display_results(results)
        except Exception as e:
            QMessageBox.warning(self, "Search Error", f"Failed to search FitGirl catalog:\n{e}")

    def _on_verify_archive(self, directory: Path) -> None:
        if not directory.exists():
            QMessageBox.warning(self, "Invalid Path", "Selected folder does not exist.")
            return

        is_complete, parts, missing = self.service.verify_archive(directory)
        self.extract_view.set_verification_result(is_complete, len(parts), missing)

    def _on_extract_archive(self, download_dir: Path, extract_dir: Path) -> None:
        self.extract_view.append_log(f"Starting extraction from {download_dir} to {extract_dir}...")
        self.active_extraction_worker = ExtractionWorker(download_dir, extract_dir, parent=self)
        self.active_extraction_worker.log_emitted.connect(self.extract_view.append_log)
        self.active_extraction_worker.finished.connect(lambda ok: QMessageBox.information(self, "Extraction Finished", "Game setup files extracted successfully!"))
        self.active_extraction_worker.failed.connect(lambda err: QMessageBox.critical(self, "Extraction Error", f"Extraction failed:\n{err}"))
        self.active_extraction_worker.start()

    def _on_save_settings(self, data: dict[str, Any]) -> None:
        for k, v in data.items():
            self.service.update_setting(k, v)
        self._on_refresh_diagnostics()

    def _on_refresh_diagnostics(self) -> None:
        diag = self.service.get_diagnostics()
        self.diagnostics_view.update_diagnostics(diag)

    def _on_worker_error(self, err_msg: str) -> None:
        self.dashboard_view.append_log(f"✘ Error: {err_msg}")
        QMessageBox.critical(self, "Operation Error", f"An error occurred:\n{err_msg}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Safe shutdown sequence preserving database state and stopping worker threads."""
        has_active = (self.active_download_worker and self.active_download_worker.isRunning())

        if has_active:
            reply = QMessageBox.question(
                self, "Active Download",
                "A download is currently in progress.\nDo you want to safely pause and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

            # Gracefully signal worker and wait up to 3000ms
            logger.info("Application close requested. Stopping active download worker...")
            if self.active_download_worker:
                self.active_download_worker.stop()
                self.active_download_worker.wait(3000)

        if self.active_resolver_worker and self.active_resolver_worker.isRunning():
            self.active_resolver_worker.stop()
            self.active_resolver_worker.wait(2000)

        logger.info("Application shutdown complete.")
        event.accept()
