"""
Thread-safe background worker threads for the PySide6 desktop GUI.
Isolates all network, browser automation, chunk writes, and subprocess execution
from the main Qt event loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal

from downloader import DownloadTelemetry, ResumableDownloader
from extractor import ArchiveVerifierExtractor
from logger import get_logger
from resolver import FuckingFastResolver
from scraper import DownloadItem, GameRepack
from security import sanitize_filename
from services import DownloadManagerService

logger = get_logger("gui.workers")


class DownloadWorker(QThread):
    """Executes multi-stream downloads in a dedicated background QThread."""

    telemetry_updated = Signal(object)      # DownloadTelemetry snapshot
    log_emitted = Signal(str)               # Real-time log message
    part_completed = Signal(str)            # Part filename
    job_completed = Signal(list)            # List of completed DownloadItems
    job_failed = Signal(str)                # Error message
    job_paused = Signal()                   # Emitted on graceful pause

    def __init__(
        self,
        service: DownloadManagerService,
        repack: GameRepack,
        items: list[DownloadItem],
        dest_dir: Path | None = None,
        workers: int | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.repack = repack
        self.items = items
        self.dest_dir = dest_dir or (service.settings.download_dir / sanitize_filename(repack.title))
        self.workers = workers or service.settings.max_concurrent_downloads
        self._downloader: ResumableDownloader | None = None
        self._is_paused = False

    def stop(self) -> None:
        """Cooperatively signals the downloader to abort or pause."""
        self._is_paused = True
        if self._downloader:
            self._downloader.stop()
        logger.info("DownloadWorker received stop signal.")

    def run(self) -> None:
        """Executes the download process on the worker thread."""
        logger.info(f"Starting DownloadWorker for repack: {self.repack.title}")
        clean_id = sanitize_filename(self.repack.title)

        def log_relay(msg: str) -> None:
            self.log_emitted.emit(msg)

        def telemetry_relay(telemetry: DownloadTelemetry) -> None:
            self.telemetry_updated.emit(telemetry)

        self._downloader = ResumableDownloader(
            dest_dir=self.dest_dir,
            max_workers=self.workers,
            job_id=clean_id,
            job_title=self.repack.title,
            page_url=self.repack.page_url,
            storage=self.service.storage,
            log_callback=log_relay,
            telemetry_callback=telemetry_relay,
        )

        try:
            completed = self._downloader.download_all(self.items)
            if self._is_paused or self._downloader.is_stopped():
                logger.info("DownloadWorker completed with pause state.")
                self.job_paused.emit()
            else:
                logger.info(f"DownloadWorker finished successfully: {len(completed)} parts.")
                self.job_completed.emit(completed)
        except Exception as e:
            logger.exception("Error in DownloadWorker execution.")
            self.job_failed.emit(str(e))
        finally:
            self._downloader = None


class ResolverWorker(QThread):
    """Executes Playwright browser automation in an isolated QThread."""

    progress = Signal(int, int, str)    # current, total, filename
    resolved = Signal(list)             # list of resolved DownloadItem
    failed = Signal(str)                # error message

    def __init__(
        self,
        service: DownloadManagerService,
        items: list[DownloadItem],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.service = service
        self.items = items
        self._resolver: FuckingFastResolver | None = None

    def stop(self) -> None:
        if self._resolver:
            self._resolver.stop()

    def run(self) -> None:
        logger.info(f"Starting ResolverWorker for {len(self.items)} items.")
        if not self.service.settings.browser_path:
            self.failed.emit("Compatible browser (Brave / Chrome / Edge) not detected on your system.")
            return

        self._resolver = FuckingFastResolver(headless=True)

        def progress_relay(current: int, total: int, item: Any) -> None:
            self.progress.emit(current, total, item.filename)

        try:
            results = self._resolver.resolve_batch(self.items, progress_callback=progress_relay)
            self.resolved.emit(results)
        except Exception as e:
            logger.exception("Error in ResolverWorker.")
            self.failed.emit(str(e))
        finally:
            self._resolver = None


class ExtractionWorker(QThread):
    """Executes external 7-Zip or WinRAR extraction in a background QThread."""

    log_emitted = Signal(str)
    finished = Signal(bool)
    failed = Signal(str)

    def __init__(
        self,
        download_dir: Path,
        extract_dir: Path,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.download_dir = Path(download_dir)
        self.extract_dir = Path(extract_dir)

    def run(self) -> None:
        logger.info(f"Starting ExtractionWorker for: {self.download_dir}")
        self.log_emitted.emit(f"Scanning archive parts in: {self.download_dir}")
        verifier = ArchiveVerifierExtractor(self.download_dir, self.extract_dir)

        is_complete, parts, missing = verifier.verify_parts()
        if not is_complete:
            err_msg = f"Archive missing or incomplete parts: {missing}"
            self.log_emitted.emit(err_msg)
            self.failed.emit(err_msg)
            return

        self.log_emitted.emit(f"Sequence verified ({len(parts)} parts). Extracting to: {self.extract_dir}...")
        try:
            ok = verifier.extract()
            if ok:
                self.log_emitted.emit("✔ Extraction completed successfully!")
                self.finished.emit(True)
            else:
                self.failed.emit("Extraction process returned a non-zero exit code.")
        except Exception as e:
            self.failed.emit(str(e))
