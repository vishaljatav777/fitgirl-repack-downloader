import os
import time
import shutil
import requests
import threading
from pathlib import Path
from typing import List, Optional, Callable, Dict
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import (
    CHUNK_SIZE,
    TIMEOUT,
    MAX_RETRIES,
    MAX_CONCURRENT_DOWNLOADS,
    USER_AGENT
)
from scraper import DownloadItem

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
    active_files: Dict[str, ActiveFileProgress] = field(default_factory=dict)

class ResumableDownloader:
    def __init__(
        self,
        dest_dir: Path,
        max_workers: int = MAX_CONCURRENT_DOWNLOADS,
        log_callback: Optional[Callable[[str], None]] = None,
        telemetry_callback: Optional[Callable[[DownloadTelemetry], None]] = None
    ):
        self.dest_dir = Path(dest_dir)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max(1, min(max_workers, 5))
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

        self.log_callback = log_callback
        self.telemetry_callback = telemetry_callback

        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Telemetry state
        self.telemetry = DownloadTelemetry()
        self._file_bytes_map: Dict[str, int] = {}
        self._file_total_map: Dict[str, int] = {}
        self._active_files_map: Dict[str, ActiveFileProgress] = {}
        self._start_time = 0.0
        self._last_calc_time = 0.0
        self._last_total_downloaded = 0
        self._peak_speed = 0.0

    def log(self, message: str):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def stop(self):
        """Signals the downloader to stop gracefully."""
        self._stop_event.set()

    def is_stopped(self) -> bool:
        return self._stop_event.is_set()

    def get_remote_file_info(self, url: str) -> tuple[int, bool]:
        """Returns (total_size, supports_range)."""
        try:
            head_resp = self.session.head(url, timeout=TIMEOUT, allow_redirects=True)
            if head_resp.status_code == 200:
                length = int(head_resp.headers.get("Content-Length", 0))
                accept_ranges = head_resp.headers.get("Accept-Ranges", "") == "bytes"
                return length, accept_ranges
        except Exception:
            pass

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
        except Exception:
            pass

        return 0, False

    def _telemetry_worker(self):
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

                    # Free disk space
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
        if not item.direct_url or self.is_stopped():
            return False

        file_path = self.dest_dir / item.filename
        existing_size = file_path.stat().st_size if file_path.exists() else 0

        total_size, supports_range = self.get_remote_file_info(item.direct_url)
        item.size_bytes = total_size

        with self._lock:
            self._file_bytes_map[item.filename] = existing_size
            if total_size > 0:
                self._file_total_map[item.filename] = total_size
                self.telemetry.total_bytes = sum(self._file_total_map.values())

        # Check if already complete
        if total_size > 0 and existing_size == total_size:
            size_mb = existing_size / (1024 * 1024)
            self.log(f"✔ Skipping {item.filename} (already downloaded, {size_mb:.1f} MB)")
            with self._lock:
                self.telemetry.completed_files += 1
            return True

        if existing_size > 0 and supports_range:
            size_mb = existing_size / (1024 * 1024)
            tot_mb = total_size / (1024 * 1024) if total_size else 0
            self.log(f"Resuming {item.filename} from {size_mb:.1f} MB / {tot_mb:.1f} MB")
        else:
            tot_mb = total_size / (1024 * 1024) if total_size else 0
            self.log(f"Downloading: {item.filename} ({tot_mb:.1f} MB)")

        headers = {}
        mode = "wb"
        current_downloaded = existing_size

        if existing_size > 0 and supports_range:
            headers["Range"] = f"bytes={existing_size}-"
            mode = "ab"
        else:
            existing_size = 0
            current_downloaded = 0

        retries = 0
        success = False
        max_attempts = 3

        while retries < max_attempts and not success and not self.is_stopped():
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
                    if resp.status_code not in (200, 206):
                        raise RuntimeError(f"HTTP Status {resp.status_code}")

                    with open(file_path, mode) as f:
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
                                        filename=item.filename,
                                        downloaded_bytes=current_downloaded,
                                        total_bytes=total_size,
                                        speed_bytes_sec=file_speed,
                                        percentage=pct
                                    )

                    success = True
                    self.log(f"✔ Completed {item.filename}")
                    with self._lock:
                        self.telemetry.completed_files += 1
                        self._active_files_map.pop(item.filename, None)
            except Exception as e:
                retries += 1
                if self.is_stopped():
                    with self._lock:
                        self._active_files_map.pop(item.filename, None)
                    return False
                self.log(f"⚠️ Retry {retries}/{max_attempts} for {item.filename}: {e}")
                time.sleep(2)
                if file_path.exists():
                    existing_size = file_path.stat().st_size
                    current_downloaded = existing_size
                    headers["Range"] = f"bytes={existing_size}-"
                    mode = "ab"

        with self._lock:
            self._active_files_map.pop(item.filename, None)

        return success

    def download_all(self, items: List[DownloadItem]) -> List[DownloadItem]:
        self._stop_event.clear()
        valid_items = [i for i in items if i.direct_url]
        total = len(valid_items)
        if total == 0:
            self.log("No valid items to download.")
            return []

        # Initialize telemetry
        with self._lock:
            self._file_bytes_map.clear()
            self._file_total_map.clear()
            self._active_files_map.clear()
            self._start_time = time.time()
            self._last_calc_time = self._start_time
            self._last_total_downloaded = 0
            self._peak_speed = 0.0

            # Scan existing local file sizes
            initial_downloaded = 0
            for item in valid_items:
                fp = self.dest_dir / item.filename
                sz = fp.stat().st_size if fp.exists() else 0
                self._file_bytes_map[item.filename] = sz
                initial_downloaded += sz
                # If size already known, store it
                if item.size_bytes > 0:
                    self._file_total_map[item.filename] = item.size_bytes
                else:
                    self._file_total_map[item.filename] = 2 * 1024 * 1024 * 1024  # 2 GB default part estimate

            total_est = sum(self._file_total_map.values())

            try:
                free_disk = shutil.disk_usage(self.dest_dir).free
            except Exception:
                free_disk = 0

            self.telemetry = DownloadTelemetry(
                total_bytes=total_est,
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

        completed_items = []
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

        # Stop telemetry thread
        self._stop_event.set()
        return completed_items
