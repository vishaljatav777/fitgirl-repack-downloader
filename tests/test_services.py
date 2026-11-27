"""
Integration tests for DownloadManagerService facade layer.
Covers:
- Scraping and catalog search orchestration
- Browser requirement validation on link resolution
- Multi-stream download coordination and callbacks
- Pause and graceful stop propagation
- System diagnostics calculations
- Dynamic settings updates and validation
- Archive verification and extraction delegations
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from exceptions import BrowserNotFoundError, ConfigurationError
from scraper import DownloadItem, GameRepack
from services import DownloadManagerService
from settings import AppSettings
from storage import JobStorage


def test_service_scrape_and_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = JobStorage(Path(tmpdir) / "s.db")
        service = DownloadManagerService(storage=storage)

        with patch.object(service.scraper, "scrape_url") as mock_scrape, \
             patch.object(service.scraper, "search_game") as mock_search:

            mock_repack = GameRepack(title="Test Game", page_url="https://site.co/game", parts=[])
            mock_scrape.return_value = mock_repack

            repack = service.scrape_repack("https://site.co/game")
            assert repack.title == "Test Game"

            mock_search.return_value = [{"title": "Test Game", "url": "https://site.co/game"}]
            results = service.search_repacks("Test")
            assert len(results) == 1
            assert results[0]["title"] == "Test Game"


def test_service_resolve_links_missing_browser():
    """Test that resolving links without a detected browser raises BrowserNotFoundError."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = AppSettings(
            download_dir=Path(tmpdir) / "dl",
            extract_dir=Path(tmpdir) / "ext",
            browser_path="",  # No browser detected
        )
        service = DownloadManagerService(settings=settings, storage=JobStorage(Path(tmpdir) / "s.db"))

        item = DownloadItem(filename="part01.rar", share_url="https://ff.co/1")
        with pytest.raises(BrowserNotFoundError) as exc_info:
            service.resolve_links([item])

        assert "No compatible browser" in str(exc_info.value)


def test_service_resolve_links_authorized_direct_bypasses_browser():
    """Test that items with direct_url bypass browser resolution entirely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = AppSettings(
            download_dir=Path(tmpdir) / "dl",
            extract_dir=Path(tmpdir) / "ext",
            browser_path="",  # No browser needed
        )
        service = DownloadManagerService(settings=settings, storage=JobStorage(Path(tmpdir) / "s.db"))

        direct_item = DownloadItem(
            filename="game.part01.rar",
            share_url="https://authorized.example.com/game.part01.rar",
            direct_url="https://authorized.example.com/game.part01.rar"
        )
        resolved = service.resolve_links([direct_item])
        assert len(resolved) == 1
        assert resolved[0].direct_url == "https://authorized.example.com/game.part01.rar"



def test_service_resolve_links_success():
    """Test successful resolution batch through FuckingFastResolver mock."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = AppSettings(
            download_dir=Path(tmpdir) / "dl",
            extract_dir=Path(tmpdir) / "ext",
            browser_path="C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe",
        )
        service = DownloadManagerService(settings=settings, storage=JobStorage(Path(tmpdir) / "s.db"))

        with patch("services.FuckingFastResolver") as mock_resolver_cls:
            mock_resolver = MagicMock()
            mock_resolver_cls.return_value = mock_resolver
            mock_resolver.resolve_batch.return_value = [
                DownloadItem(filename="part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1", size_bytes=1000)
            ]

            items = [DownloadItem(filename="part01.rar", share_url="https://ff.co/1")]
            resolved = service.resolve_links(items)

            assert len(resolved) == 1
            assert resolved[0].direct_url == "https://dl.co/1"


def test_service_start_download_and_pause():
    """Test starting download and pausing active downloader."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        storage = JobStorage(tmp_path / "s.db")
        service = DownloadManagerService(storage=storage)

        repack = GameRepack(title="Awesome Game", page_url="https://site.co/game", parts=[])
        items = [DownloadItem(filename="game.part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1")]

        with patch("downloader.ResumableDownloader.download_all") as mock_dl_all:
            mock_dl_all.return_value = items
            completed = service.start_download(repack, items, dest_dir=tmp_path / "Awesome Game")
            assert len(completed) == 1

        # Test pause_active_download when active
        mock_downloader = MagicMock()
        mock_downloader.is_stopped.return_value = False
        service._active_downloader = mock_downloader

        service.pause_active_download()
        assert mock_downloader.stop.called


def test_service_diagnostics():
    """Test get_diagnostics dictionary formatting."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = AppSettings(
            download_dir=Path(tmpdir) / "dl",
            extract_dir=Path(tmpdir) / "ext",
            browser_path="C:/fake/browser.exe",
            unrar_path="C:/fake/7z.exe",
        )
        service = DownloadManagerService(settings=settings, storage=JobStorage(Path(tmpdir) / "s.db"))

        diag = service.get_diagnostics()
        assert diag["browser_ready"] is True
        assert diag["unrar_ready"] is True
        assert "storage_free_gb" in diag
        assert "storage_total_gb" in diag


def test_service_update_setting():
    """Test dynamic settings update and error on invalid key."""
    with tempfile.TemporaryDirectory() as tmpdir:
        service = DownloadManagerService(storage=JobStorage(Path(tmpdir) / "s.db"))

        service.update_setting("max_concurrent_downloads", 4)
        assert service.settings.max_concurrent_downloads == 4

        service.update_setting("auto_extract", True)
        assert service.settings.auto_extract is True

        with pytest.raises(ConfigurationError):
            service.update_setting("non_existent_key_12345", "val")


def test_service_archive_verification_and_extraction():
    """Test delegation of verify_archive and extract_archive to verifier/extractor."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        service = DownloadManagerService(storage=JobStorage(tmp_path / "s.db"))

        with patch("services.ArchiveVerifierExtractor") as mock_arch_cls:
            mock_instance = MagicMock()
            mock_instance.verify_parts.return_value = (True, [tmp_path / "part01.rar"], [])
            mock_instance.extract.return_value = True
            mock_arch_cls.return_value = mock_instance

            is_complete, files, missing = service.verify_archive(tmp_path)
            assert is_complete is True
            assert len(files) == 1

            ok = service.extract_archive(tmp_path)
            assert ok is True
