from __future__ import annotations

import os
import shutil
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import requests

from config import CHUNK_SIZE, MAX_CONCURRENT_DOWNLOADS, MAX_RETRIES, TIMEOUT, USER_AGENT
from exceptions import (
    DiskSpaceError,
    DownloadError,
    IncompleteDownloadError,
)
from logger import get_logger
from scraper import DownloadItem
from security import sanitize_filename, validate_destination_path
from storage import JobStatus, JobStorage, PartStatus

logger = get_logger("downloader")


@dataclass
class ActiveFileProgress:
    filename: str
    downloaded_bytes: int
    total_bytes: int
    speed_bytes_sec: float
    percentage: float


@dataclass
class DownloadTelemetry:
    total_bytes: int = 0
    downloaded_bytes: int = 0
    completed_files: int = 0
    total_files: int = 0
    current_speed_bytes: float = 0.0
    net_bandwidth_mbps: float = 0.0
    peak_speed_bytes: float = 0.0
    average_speed_bytes: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float = 0.0
    disk_free_bytes: int = 0
    active_files: dict[str, ActiveFileProgress] = field(default_factory=dict)


class ResumableDownloader:
    """Thread-safe, resumable multi-part download engine with SQLite persistence,

    Range verification, and atomic file operations.
    """

    def __init__(
        self,
        dest_dir: Path,
        max_workers: int = MAX_CONCURRENT_DOWNLOADS,
        job_id: str | None = None,
        job_title: str = "Download Job",
        page_url: str = "",
        storage: JobStorage | None = None,
        log_callback: Callable[[str], None] | None = None,
        telemetry_callback: Callable[[DownloadTelemetry], None] | None = None,
    ):
        self.dest_dir = Path(dest_dir)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max(1, min(max_workers, 5))
        self.job_id = job_id or self.dest_dir.name
        self.job_title = job_title
        self.page_url = page_url
        self.storage = storage

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        self.log_callback = log_callback
        self.telemetry_callback = telemetry_callback

        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Telemetry state
        self.telemetry = DownloadTelemetry()
        self._file_bytes_map: dict[str, int] = {}
        self._file_total_map: dict[str, int] = {}
        self._active_files_map: dict[str, ActiveFileProgress] = {}
        self._start_time = 0.0
        self._last_calc_time = 0.0
        self._last_total_downloaded = 0
        self._peak_speed = 0.0

    def log(self, message: str) -> None:
        logger.info(message)
        if self.log_callback:
            try:
                self.log_callback(message)
            except Exception:
                pass

    def stop(self) -> None:
        """Signals the downloader to stop gracefully."""
        self._stop_event.set()
        logger.debug("Stop signal received by ResumableDownloader.")

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def get_remote_file_info(self, url: str) -> tuple[int, bool]:
        """Queries remote URL headers to determine file size and Range support.

        Returns:
            tuple of (total_length_bytes, supports_range)
        """
        try:
            head_resp = self.session.head(url, timeout=TIMEOUT, allow_redirects=True)
            if head_resp.status_code == 200:
                length = int(head_resp.headers.get("Content-Length", 0))
                accept_ranges = head_resp.headers.get("Accept-Ranges", "").lower() == "bytes"
                return length, accept_ranges
        except Exception as e:
            logger.debug(f"HEAD request failed for {url}: {e}")

        try:
            range_resp = self.session.get(
                url,
                headers={"Range": "bytes=0-0"},
                timeout=TIMEOUT,
                stream=True
            )
            if range_resp.status_code == 206:
                content_range = range_resp.headers.get("Content-Range", "")
                if "/" in content_range:
                    total = int(content_range.split("/")[-1])
                    return total, True
            elif range_resp.status_code == 200:
                length = int(range_resp.headers.get("Content-Length", 0))
                return length, False
        except Exception as e:
            logger.debug(f"Range probe request failed for {url}: {e}")

        return 0, False

    def _telemetry_worker(self) -> None:
        """Background thread updating telemetry at smooth 4Hz intervals."""
        while not self.is_stopped():
            time.sleep(0.25)
            now = time.time()
            if self._start_time == 0:
                continue

            with self._lock:
                current_total_downloaded = sum(self._file_bytes_map.values())
                dt = now - self._last_calc_time
                if dt >= 0.25:
                    delta_bytes = current_total_downloaded - self._last_total_downloaded
                    instant_speed = max(0.0, delta_bytes / dt)
                    self._last_calc_time = now
                    self._last_total_downloaded = current_total_downloaded

                    # Smooth speed calculation
                    current_speed = (self.telemetry.current_speed_bytes * 0.7) + (instant_speed * 0.3)
                    if current_speed > self._peak_speed:
                        self._peak_speed = current_speed

                    elapsed = now - self._start_time
                    avg_speed = current_total_downloaded / elapsed if elapsed > 0 else 0.0

                    # Network line bandwidth (Mbps)
                    net_mbps = (current_speed * 8) / 1_000_000

                    remaining_bytes = max(0, self.telemetry.total_bytes - current_total_downloaded)
                    effective_speed = current_speed if current_speed > 1024 else avg_speed
                    eta = (remaining_bytes / effective_speed) if effective_speed > 1024 else 0.0

                    try:
                        free_disk = shutil.disk_usage(self.dest_dir).free
                    except Exception:
                        free_disk = 0

                    self.telemetry.downloaded_bytes = current_total_downloaded
                    self.telemetry.current_speed_bytes = current_speed
                    self.telemetry.net_bandwidth_mbps = net_mbps
                    self.telemetry.peak_speed_bytes = self._peak_speed
                    self.telemetry.average_speed_bytes = avg_speed
                    self.telemetry.elapsed_seconds = elapsed
                    self.telemetry.eta_seconds = eta
                    self.telemetry.disk_free_bytes = free_disk
                    self.telemetry.active_files = dict(self._active_files_map)

            if self.telemetry_callback:
                try:
                    self.telemetry_callback(self.telemetry)
                except Exception:
                    pass

    def download_file(self, item: DownloadItem) -> bool:
        """Downloads a single part safely with Range verification and atomic rename."""
        if not item.direct_url or self.is_stopped():
            return False

        # Validate destination and sanitize filename against path traversal
        clean_name = sanitize_filename(item.filename)
        final_file_path = validate_destination_path(self.dest_dir, clean_name)
        part_file_path = final_file_path.with_name(f"{clean_name}.part")

        # Check remote size and Range support
        total_size, supports_range = self.get_remote_file_info(item.direct_url)
        item.size_bytes = total_size

        # Check if already complete
        if final_file_path.exists():
            existing_final_size = final_file_path.stat().st_size
            if total_size > 0 and existing_final_size == total_size:
                size_mb = existing_final_size / (1024 * 1024)
                self.log(f"✔ Skipping {clean_name} (already downloaded, {size_mb:.1f} MB)")
                with self._lock:
                    self._file_bytes_map[item.filename] = existing_final_size
                    self._file_total_map[item.filename] = total_size
                    self.telemetry.completed_files += 1
                if self.storage:
                    self.storage.update_part_progress(
                        self.job_id, clean_name, existing_final_size, total_size, PartStatus.COMPLETED
                    )
                return True

        # Check available disk space
        try:
            free_space = shutil.disk_usage(self.dest_dir).free
            required_space = total_size if total_size > 0 else 500 * 1024 * 1024
            if free_space < required_space + (50 * 1024 * 1024):  # 50 MB buffer
                raise DiskSpaceError(
                    f"Insufficient disk space on {self.dest_dir}: {free_space / (1024 ** 2):.1f} MB available, "
                    f"need {required_space / (1024 ** 2):.1f} MB"
                )
        except OSError:
            pass

        # Determine existing partially downloaded bytes from .part file
        existing_part_size = part_file_path.stat().st_size if part_file_path.exists() else 0

        with self._lock:
            self._file_bytes_map[item.filename] = existing_part_size
            if total_size > 0:
                self._file_total_map[item.filename] = total_size
                self.telemetry.total_bytes = sum(self._file_total_map.values())

        tot_mb = total_size / (1024 * 1024) if total_size else 0
        if existing_part_size > 0 and supports_range:
            part_mb = existing_part_size / (1024 * 1024)
            self.log(f"Resuming {clean_name} from {part_mb:.1f} MB / {tot_mb:.1f} MB")
        else:
            self.log(f"Downloading: {clean_name} ({tot_mb:.1f} MB)")

        retries = 0
        success = False
        max_attempts = max(1, MAX_RETRIES)

        while retries < max_attempts and not success and not self.is_stopped():
            headers: dict[str, str] = {}
            mode = "wb"
            current_downloaded = existing_part_size

            # If resuming with Range
            if existing_part_size > 0 and supports_range:
                headers["Range"] = f"bytes={existing_part_size}-"
                mode = "ab"
            else:
                existing_part_size = 0
                current_downloaded = 0
                mode = "wb"

            try:
                last_check = time.time()
                bytes_at_last_check = current_downloaded
                file_speed = 0.0

                with self.session.get(
                    item.direct_url,
                    headers=headers,
                    stream=True,
                    timeout=TIMEOUT
                ) as resp:
                    # Handle rate limiting (HTTP 429)
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get("Retry-After", 5))
                        self.log(f"⚠️ Rate limited (HTTP 429). Backing off for {retry_after}s...")
                        time.sleep(retry_after)
                        retries += 1
                        continue

                    # Handle Range Not Satisfiable (HTTP 416)
                    if resp.status_code == 416:
                        if total_size > 0 and existing_part_size == total_size:
                            # File is already complete in .part
                            success = True
                            break
                        # Otherwise range request was invalid; restart from byte 0
                        existing_part_size = 0
                        current_downloaded = 0
                        mode = "wb"
                        retries += 1
                        continue

                    # Critical HTTP Range verification:
                    # If we requested a Range but the server responded with HTTP 200 (Full Content),
                    # the server ignored the Range header. We MUST NOT append to the partial file!
                    if "Range" in headers:
                        if resp.status_code == 206:
                            mode = "ab"
                        elif resp.status_code == 200:
                            self.log(f"ℹ️ Server does not support resume for {clean_name}; restarting from 0 MB.")
                            mode = "wb"
                            existing_part_size = 0
                            current_downloaded = 0
                        else:
                            raise DownloadError(f"HTTP Status {resp.status_code} for Range request")
                    elif resp.status_code != 200:
                        raise DownloadError(f"HTTP Status {resp.status_code}")

                    # Stream into temporary .part file
                    with open(part_file_path, mode) as f:
                        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
                            if self.is_stopped():
                                with self._lock:
                                    self._active_files_map.pop(item.filename, None)
                                return False

                            if chunk:
                                f.write(chunk)
                                current_downloaded += len(chunk)

                                now = time.time()
                                if now - last_check >= 0.5:
                                    file_speed = (current_downloaded - bytes_at_last_check) / (now - last_check)
                                    bytes_at_last_check = current_downloaded
                                    last_check = now

                                pct = (current_downloaded / total_size) if total_size > 0 else 0.0
                                with self._lock:
                                    self._file_bytes_map[item.filename] = current_downloaded
                                    self._active_files_map[item.filename] = ActiveFileProgress(
                                        filename=clean_name,
                                        downloaded_bytes=current_downloaded,
                                        total_bytes=total_size,
                                        speed_bytes_sec=file_speed,
                                        percentage=pct
                                    )

                    # Verify final downloaded size before accepting file
                    actual_downloaded = part_file_path.stat().st_size
                    if total_size > 0 and actual_downloaded != total_size:
                        raise IncompleteDownloadError(
                            f"Downloaded size mismatch for {clean_name}: expected {total_size} bytes, "
                            f"got {actual_downloaded} bytes"
                        )

                    # Atomically rename .part to final destination
                    if final_file_path.exists():
                        final_file_path.unlink()
                    os.replace(part_file_path, final_file_path)

                    success = True
                    self.log(f"✔ Completed {clean_name}")
                    with self._lock:
                        self.telemetry.completed_files += 1
                        self._active_files_map.pop(item.filename, None)

                    if self.storage:
                        self.storage.update_part_progress(
                            self.job_id, clean_name, actual_downloaded, total_size, PartStatus.COMPLETED
                        )

            except Exception as e:
                retries += 1
                if self.is_stopped():
                    with self._lock:
                        self._active_files_map.pop(item.filename, None)
                    return False

                # Calculate exponential backoff delay (0.5s, 1s, 2s, 4s...)
                backoff_delay = min(10.0, 0.5 * (2 ** (retries - 1)))
                self.log(f"⚠️ Retry {retries}/{max_attempts} for {clean_name}: {e} (waiting {backoff_delay:.1f}s)")
                time.sleep(backoff_delay)

                if part_file_path.exists():
                    existing_part_size = part_file_path.stat().st_size
                    current_downloaded = existing_part_size

        with self._lock:
            self._active_files_map.pop(item.filename, None)

        if not success and self.storage:
            self.storage.update_part_progress(
                self.job_id, clean_name, existing_part_size, total_size, PartStatus.FAILED
            )

        return success

    def download_all(self, items: list[DownloadItem]) -> list[DownloadItem]:
        """Downloads all queued items concurrently with progress telemetry and persistence."""
        self._stop_event.clear()
        valid_items = [i for i in items if i.direct_url]
        total = len(valid_items)
        if total == 0:
            self.log("No valid items to download.")
            return []

        # Initialize or update SQLite persistent job
        if self.storage:
            self.storage.create_or_update_job(
                job_id=self.job_id,
                title=self.job_title,
                page_url=self.page_url,
                download_dir=self.dest_dir,
                total_files=total,
                status=JobStatus.DOWNLOADING,
            )
            part_dicts = [
                {
                    "filename": sanitize_filename(item.filename),
                    "share_url": item.share_url,
                    "direct_url": item.direct_url,
                    "total_bytes": item.size_bytes,
                }
                for item in valid_items
            ]
            self.storage.save_parts(self.job_id, part_dicts)

        # Initialize telemetry state
        with self._lock:
            self._file_bytes_map.clear()
            self._file_total_map.clear()
            self._active_files_map.clear()
            self._start_time = time.time()
            self._last_calc_time = self._start_time
            self._last_total_downloaded = 0
            self._peak_speed = 0.0

            initial_downloaded = 0
            for item in valid_items:
                clean_name = sanitize_filename(item.filename)
                final_path = self.dest_dir / clean_name
                part_path = self.dest_dir / f"{clean_name}.part"

                if final_path.exists():
                    sz = final_path.stat().st_size
                elif part_path.exists():
                    sz = part_path.stat().st_size
                else:
                    sz = 0

                self._file_bytes_map[item.filename] = sz
                initial_downloaded += sz

                if item.size_bytes > 0:
                    self._file_total_map[item.filename] = item.size_bytes

            total_known_bytes = sum(self._file_total_map.values())

            try:
                free_disk = shutil.disk_usage(self.dest_dir).free
            except Exception:
                free_disk = 0

            self.telemetry = DownloadTelemetry(
                total_bytes=total_known_bytes,
                downloaded_bytes=initial_downloaded,
                completed_files=0,
                total_files=total,
                current_speed_bytes=0.0,
                net_bandwidth_mbps=0.0,
                peak_speed_bytes=0.0,
                average_speed_bytes=0.0,
                elapsed_seconds=0.0,
                eta_seconds=0.0,
                disk_free_bytes=free_disk,
                active_files={}
            )

        # Start telemetry heartbeat thread
        telemetry_thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        telemetry_thread.start()

        completed_items: list[DownloadItem] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {
                executor.submit(self.download_file, item): item
                for item in valid_items
            }

            for future in as_completed(future_to_item):
                item = future_to_item[future]
                if self.is_stopped():
                    break
                try:
                    ok = future.result()
                    if ok:
                        completed_items.append(item)
                except Exception as e:
                    self.log(f"✘ Error downloading {item.filename}: {e}")

        # Update final job status in persistent storage
        if self.storage:
            final_status = JobStatus.COMPLETED if len(completed_items) == total else JobStatus.PAUSED
            self.storage.update_job_status(self.job_id, final_status)

        # Stop telemetry thread
        self._stop_event.set()
        return completed_items
