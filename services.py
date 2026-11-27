"""
Application service layer (facade) for the FitGirl Repack Downloader.
Coordinates scraper, resolver, downloader, extractor, storage, and settings.
Provides a headless API consumed by both the Typer CLI and PySide6 GUI.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from downloader import DownloadTelemetry, ResumableDownloader
from exceptions import (
    BrowserNotFoundError,
    ConfigurationError,
    FitGirlDownloaderError,
)
from extractor import ArchiveVerifierExtractor
from logger import get_logger
from resolver import FuckingFastResolver
from scraper import DownloadItem, FitGirlScraper, GameRepack
from security import sanitize_filename
from settings import AppSettings, get_settings
from storage import JobRecord, JobStatus, JobStorage, PartRecord, PartStatus

logger = get_logger("service")


class DownloadManagerService:
    """Unified application service facade for download orchestration and job management."""

    def __init__(
        self,
        settings: AppSettings | None = None,
        storage: JobStorage | None = None,
    ):
        self.settings = settings or get_settings()
        self.storage = storage or JobStorage(self.settings.download_dir / "jobs.db")
        self.scraper = FitGirlScraper()
        self._active_downloader: ResumableDownloader | None = None

    def scrape_repack(self, url: str) -> GameRepack:
        """Scrapes repack metadata and all download links from a URL."""
        logger.info(f"Scraping repack URL: {url}")
        return self.scraper.scrape_url(url)

    def search_repacks(self, query: str) -> list[dict[str, str]]:
        """Searches FitGirl site for game titles."""
        logger.info(f"Searching repack catalog for: {query}")
        return self.scraper.search_game(query)

    def resolve_links(
        self,
        items: list[DownloadItem],
        progress_callback: Callable[[int, int, DownloadItem], None] | None = None,
    ) -> list[DownloadItem]:
        """Resolves direct download links for the provided items via background browser automation."""
        # Fast path: If all items already have direct_url (e.g. authorized direct sources), return immediately
        if items and all(item.direct_url for item in items):
            logger.info("All download items already have direct URLs; skipping browser resolver.")
            if progress_callback:
                for idx, item in enumerate(items, 1):
                    progress_callback(idx, len(items), item)
            return items

        if not self.settings.browser_path:
            raise BrowserNotFoundError(
                "No compatible browser (Brave / Chrome / Edge) detected on your system.",
                details="Please install a Chromium-based browser to resolve fuckingfast.co links."
            )

        resolver = FuckingFastResolver(headless=True)
        return resolver.resolve_batch(items, progress_callback=progress_callback)

    def start_download(
        self,
        repack: GameRepack,
        items: list[DownloadItem],
        dest_dir: Path | None = None,
        workers: int | None = None,
        telemetry_callback: Callable[[DownloadTelemetry], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> list[DownloadItem]:
        """Starts multi-stream download of items under the given repack title."""
        target_dir = dest_dir or (self.settings.download_dir / sanitize_filename(repack.title))
        target_dir.mkdir(parents=True, exist_ok=True)
        concurrency = workers or self.settings.max_concurrent_downloads

        clean_id = sanitize_filename(repack.title)

        downloader = ResumableDownloader(
            dest_dir=target_dir,
            max_workers=concurrency,
            job_id=clean_id,
            job_title=repack.title,
            page_url=repack.page_url,
            storage=self.storage,
            log_callback=log_callback,
            telemetry_callback=telemetry_callback,
        )
        self._active_downloader = downloader
        try:
            return downloader.download_all(items)
        finally:
            self._active_downloader = None

    def pause_active_download(self) -> None:
        """Signals active downloader to pause gracefully."""
        if self._active_downloader and not self._active_downloader.is_stopped():
            self._active_downloader.stop()
            logger.info("Active download stopped.")

    def resume_job(
        self,
        job_id: str,
        workers: int | None = None,
        telemetry_callback: Callable[[DownloadTelemetry], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> list[DownloadItem]:
        """Resumes an incomplete or paused job from storage."""
        job = self.storage.get_job(job_id)
        if not job:
            raise FitGirlDownloaderError(f"Job '{job_id}' not found in database.")

        parts = self.storage.get_parts(job_id)
        uncompleted_parts = [p for p in parts if p.status != PartStatus.COMPLETED]

        if not uncompleted_parts:
            logger.info(f"All parts for job '{job_id}' are already completed.")
            self.storage.update_job_status(job_id, JobStatus.COMPLETED)
            return []

        # Convert PartRecords back to DownloadItems
        download_items: list[DownloadItem] = []
        for p in uncompleted_parts:
            download_items.append(
                DownloadItem(
                    filename=p.filename,
                    share_url=p.share_url,
                    direct_url=p.direct_url,
                    size_bytes=p.total_bytes,
                )
            )

        # Re-resolve any expired direct links
        items_needing_resolution = [i for i in download_items if not i.direct_url]
        if items_needing_resolution:
            logger.info(f"Re-resolving {len(items_needing_resolution)} uncompleted direct links...")
            resolved = self.resolve_links(items_needing_resolution)
            # Update storage with new direct links
            for r in resolved:
                if r.direct_url:
                    self.storage.update_part_progress(
                        job_id, r.filename, 0, r.size_bytes, PartStatus.PENDING
                    )

        target_dir = Path(job.download_dir)
        concurrency = workers or self.settings.max_concurrent_downloads

        downloader = ResumableDownloader(
            dest_dir=target_dir,
            max_workers=concurrency,
            job_id=job.id,
            job_title=job.title,
            page_url=job.page_url,
            storage=self.storage,
            log_callback=log_callback,
            telemetry_callback=telemetry_callback,
        )
        self._active_downloader = downloader
        try:
            return downloader.download_all(download_items)
        finally:
            self._active_downloader = None

    def cancel_job(self, job_id: str) -> bool:
        """Marks a job as canceled."""
        job = self.storage.get_job(job_id)
        if not job:
            return False

        if self._active_downloader and self._active_downloader.job_id == job_id:
            self._active_downloader.stop()

        self.storage.update_job_status(job_id, JobStatus.FAILED, error_message="Canceled by user")
        return True

    def list_jobs(self, status: JobStatus | None = None) -> list[JobRecord]:
        """Returns all persistent jobs matching optional status filter."""
        return self.storage.list_jobs(status=status)

    def get_job(self, job_id: str) -> JobRecord | None:
        """Retrieves a job by its ID."""
        return self.storage.get_job(job_id)

    def get_job_parts(self, job_id: str) -> list[PartRecord]:
        """Retrieves parts belonging to a job."""
        return self.storage.get_parts(job_id)

    def verify_archive(self, directory: Path) -> tuple[bool, list[Path], list[int]]:
        """Verifies multi-part archive integrity in a folder."""
        verifier = ArchiveVerifierExtractor(download_dir=directory, extract_dir=self.settings.extract_dir)
        return verifier.verify_parts()

    def extract_archive(self, download_dir: Path, extract_dir: Path | None = None) -> bool:
        """Extracts an archive to destination."""
        target_extract = extract_dir or (self.settings.extract_dir / download_dir.name)
        extractor = ArchiveVerifierExtractor(download_dir=download_dir, extract_dir=target_extract)
        return extractor.extract()

    def get_diagnostics(self) -> dict[str, Any]:
        """Performs full system readiness check."""
        browser = self.settings.browser_path
        unrar = self.settings.unrar_path

        try:
            usage = shutil.disk_usage(self.settings.download_dir)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
        except Exception:
            free_gb = 0.0
            total_gb = 0.0

        return {
            "browser_ready": bool(browser),
            "browser_path": browser or "None detected (Brave/Chrome/Edge required)",
            "unrar_ready": bool(unrar),
            "unrar_path": unrar or "None detected (WinRAR or 7-Zip recommended)",
            "download_dir": str(self.settings.download_dir),
            "extract_dir": str(self.settings.extract_dir),
            "storage_free_gb": free_gb,
            "storage_total_gb": total_gb,
            "max_workers": self.settings.max_concurrent_downloads,
            "timeout_sec": self.settings.timeout,
        }

    def update_setting(self, key: str, value: Any) -> None:
        """Updates an application setting in memory."""
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            self.settings.__post_init__()
        else:
            raise ConfigurationError(f"Unknown configuration key: {key}")
