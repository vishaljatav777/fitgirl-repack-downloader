"""
Unit and smoke tests for PySide6 background worker threads:
- DownloadWorker: lifecycle, telemetry, pause, completion, failure signals
- ResolverWorker: browser validation, batch progress, resolved, failure signals
- ExtractionWorker: archive verification, progress log, extraction results
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from gui.workers import DownloadWorker, ExtractionWorker, ResolverWorker
from scraper import DownloadItem, GameRepack
from services import DownloadManagerService
from settings import AppSettings
from storage import JobStorage


def test_download_worker_success(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        service = DownloadManagerService(storage=JobStorage(tmp_path / "w.db"))
        repack = GameRepack(title="Worker Game", page_url="https://site.co/g", parts=[])
        items = [DownloadItem(filename="game.part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1")]

        worker = DownloadWorker(service=service, repack=repack, items=items, dest_dir=tmp_path)

        with patch("downloader.ResumableDownloader.download_all") as mock_dl:
            mock_dl.return_value = items

            with qtbot.waitSignal(worker.job_completed, timeout=3000) as blocker:
                worker.start()

            completed_items = blocker.args[0]
            assert len(completed_items) == 1
            assert completed_items[0].filename == "game.part01.rar"


def test_download_worker_pause(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        service = DownloadManagerService(storage=JobStorage(tmp_path / "w.db"))
        repack = GameRepack(title="Pause Game", page_url="https://site.co/g", parts=[])
        items = [DownloadItem(filename="game.part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1")]

        worker = DownloadWorker(service=service, repack=repack, items=items, dest_dir=tmp_path)

        with patch("downloader.ResumableDownloader.download_all") as mock_dl:
            def stop_and_return(its):
                worker.stop()
                return []
            mock_dl.side_effect = stop_and_return

            with qtbot.waitSignal(worker.job_paused, timeout=3000):
                worker.start()


def test_download_worker_failure(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        service = DownloadManagerService(storage=JobStorage(tmp_path / "w.db"))
        repack = GameRepack(title="Fail Game", page_url="https://site.co/g", parts=[])
        items = [DownloadItem(filename="game.part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1")]

        worker = DownloadWorker(service=service, repack=repack, items=items, dest_dir=tmp_path)

        with patch("downloader.ResumableDownloader.download_all", side_effect=RuntimeError("Disk crash")):
            with qtbot.waitSignal(worker.job_failed, timeout=3000) as blocker:
                worker.start()

            err_msg = blocker.args[0]
            assert "Disk crash" in err_msg


def test_resolver_worker_missing_browser(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        settings = AppSettings(download_dir=tmp_path, extract_dir=tmp_path, browser_path="")
        service = DownloadManagerService(settings=settings, storage=JobStorage(tmp_path / "w.db"))

        items = [DownloadItem(filename="part01.rar", share_url="https://ff.co/1")]
        worker = ResolverWorker(service=service, items=items)

        with qtbot.waitSignal(worker.failed, timeout=3000) as blocker:
            worker.start()

        err_msg = blocker.args[0]
        assert "not detected" in err_msg


def test_resolver_worker_success(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        settings = AppSettings(download_dir=tmp_path, extract_dir=tmp_path, browser_path="C:/fake/browser.exe")
        service = DownloadManagerService(settings=settings, storage=JobStorage(tmp_path / "w.db"))

        items = [DownloadItem(filename="part01.rar", share_url="https://ff.co/1")]
        worker = ResolverWorker(service=service, items=items)

        with patch("gui.workers.FuckingFastResolver") as mock_res_cls:
            mock_res = MagicMock()
            mock_res_cls.return_value = mock_res
            resolved_item = DownloadItem(filename="part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1")
            mock_res.resolve_batch.return_value = [resolved_item]

            with qtbot.waitSignal(worker.resolved, timeout=3000) as blocker:
                worker.start()

            res_items = blocker.args[0]
            assert len(res_items) == 1
            assert res_items[0].direct_url == "https://dl.co/1"


def test_extraction_worker_incomplete_parts(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Empty folder -> incomplete sequence
        worker = ExtractionWorker(download_dir=tmp_path, extract_dir=tmp_path / "ext")

        with qtbot.waitSignal(worker.failed, timeout=3000) as blocker:
            worker.start()

        assert "incomplete" in blocker.args[0].lower()


def test_extraction_worker_success(qtbot):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"DATA")
        worker = ExtractionWorker(download_dir=tmp_path, extract_dir=tmp_path / "ext")

        with patch("gui.workers.ArchiveVerifierExtractor.extract", return_value=True):
            with qtbot.waitSignal(worker.finished, timeout=3000) as blocker:
                worker.start()

            assert blocker.args[0] is True
