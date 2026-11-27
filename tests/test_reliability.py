"""
Reliability and robustness tests for ResumableDownloader.
Covers:
- Interrupted downloads & connection drops mid-stream
- HTTP 429 rate limiting & exponential backoff
- HTTP 416 Range Not Satisfiable edge cases
- HTTP 500 server errors & retry exhaustion
- Corrupted file detection (size mismatch, magic bytes)
- Insufficient disk space (DiskSpaceError)
- Cancellation & graceful shutdown
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from downloader import ResumableDownloader
from exceptions import DiskSpaceError
from scraper import DownloadItem
from security import verify_archive_magic_bytes
from storage import JobStatus, JobStorage, PartStatus


def test_download_interrupted_connection_resumes():
    """Test that if a connection drops mid-stream, the partial file is saved and resumed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part01.rar"
        part_path = dest / f"{filename}.part"
        final_path = dest / filename

        downloader = ResumableDownloader(dest_dir=dest)

        # Total size: 1000 bytes
        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "1000", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # First GET attempt: streams 400 bytes then raises ConnectionError
            first_resp = MagicMock()
            first_resp.status_code = 200
            first_resp.headers = {"Content-Length": "1000"}

            def broken_iter(chunk_size=1024):
                yield b"A" * 400
                raise requests.exceptions.ConnectionError("Network connection abruptly closed")

            first_resp.iter_content = broken_iter
            first_resp.__enter__.return_value = first_resp

            # Second GET attempt: server supports Range, responds 206 with remaining 600 bytes
            second_resp = MagicMock()
            second_resp.status_code = 206
            second_resp.headers = {"Content-Range": "bytes 400-999/1000"}
            second_resp.iter_content = MagicMock(return_value=[b"B" * 600])
            second_resp.__enter__.return_value = second_resp

            mock_get.side_effect = [first_resp, second_resp]

            item = DownloadItem(filename=filename, share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is True
            assert final_path.exists()
            assert final_path.stat().st_size == 1000
            assert final_path.read_bytes() == (b"A" * 400 + b"B" * 600)
            assert not part_path.exists()


def test_download_rate_limit_http_429():
    """Test that HTTP 429 invokes backoff using Retry-After header and succeeds on next attempt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part02.rar"
        final_path = dest / filename

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get, \
             patch("time.sleep") as mock_sleep:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "500", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Attempt 1: 429 Too Many Requests
            resp_429 = MagicMock()
            resp_429.status_code = 429
            resp_429.headers = {"Retry-After": "2"}
            resp_429.__enter__.return_value = resp_429

            # Attempt 2: 200 OK
            resp_200 = MagicMock()
            resp_200.status_code = 200
            resp_200.headers = {"Content-Length": "500"}
            resp_200.iter_content = MagicMock(return_value=[b"Z" * 500])
            resp_200.__enter__.return_value = resp_200

            mock_get.side_effect = [resp_429, resp_200]

            item = DownloadItem(filename=filename, share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is True
            assert final_path.exists()
            assert final_path.stat().st_size == 500
            mock_sleep.assert_any_call(2)


def test_download_range_416_file_already_complete_in_part():
    """Test HTTP 416 when partial file is already 100% downloaded in .part."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part03.rar"
        part_path = dest / f"{filename}.part"
        final_path = dest / filename

        # Existing .part is already full 800 bytes
        part_path.write_bytes(b"FULL" * 200)

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "800", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Request with Range: bytes=800- results in 416 Range Not Satisfiable
            resp_416 = MagicMock()
            resp_416.status_code = 416
            resp_416.__enter__.return_value = resp_416
            mock_get.return_value = resp_416

            item = DownloadItem(filename=filename, share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is True
            assert final_path.exists()
            assert final_path.stat().st_size == 800


def test_download_range_416_content_range_fallback():
    """Test HTTP 416 fallback when total size is obtained from Content-Range header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part04.rar"
        part_path = dest / f"{filename}.part"
        final_path = dest / filename

        part_path.write_bytes(b"DATA" * 150)  # 600 bytes

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            # Initial probe has Accept-Ranges: bytes but Content-Length <= 0 (e.g. 0 or missing)
            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "0", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # GET with Range: bytes=600- returns 416 with Content-Range
            resp_416 = MagicMock()
            resp_416.status_code = 416
            resp_416.headers = {"Content-Range": "bytes */600"}
            resp_416.__enter__.return_value = resp_416
            mock_get.return_value = resp_416

            item = DownloadItem(filename=filename, share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is True
            assert final_path.exists()
            assert final_path.stat().st_size == 600



def test_download_server_500_retries_and_fails():
    """Test that repeated HTTP 500 errors exhaust retries and mark part failed in storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        storage_db = dest / "test.db"
        storage = JobStorage(storage_db)

        storage.create_or_update_job(
            job_id="test_job",
            title="Test Job",
            page_url="https://test.co",
            download_dir=dest,
            total_files=1,
            status=JobStatus.DOWNLOADING,
        )
        storage.save_parts("test_job", [{"filename": "game.part04.rar", "share_url": "", "direct_url": "", "total_bytes": 500}])
        downloader = ResumableDownloader(dest_dir=dest, storage=storage, job_id="test_job")

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get, \
             patch("time.sleep"):

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "500", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            resp_500 = MagicMock()
            resp_500.status_code = 500
            resp_500.__enter__.return_value = resp_500
            mock_get.return_value = resp_500

            item = DownloadItem(filename="game.part04.rar", share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is False
            parts = storage.get_parts("test_job")
            assert len(parts) == 1
            assert parts[0].status == PartStatus.FAILED


def test_download_corrupted_size_mismatch():
    """Test that if stream finishes with size mismatch, IncompleteDownloadError is handled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get, \
             patch("time.sleep"):

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "1000", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Server declares 1000 bytes but only delivers 600 bytes on every attempt
            resp = MagicMock()
            resp.status_code = 200
            resp.headers = {"Content-Length": "1000"}
            resp.iter_content = MagicMock(return_value=[b"X" * 600])
            resp.__enter__.return_value = resp
            mock_get.return_value = resp

            item = DownloadItem(filename="game.part05.rar", share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is False
            assert not (dest / "game.part05.rar").exists()


def test_download_insufficient_disk_space():
    """Test that DiskSpaceError is raised when available disk space is insufficient."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch("shutil.disk_usage") as mock_disk:

            head_resp = MagicMock()
            head_resp.status_code = 200
            # 5 GB file
            head_resp.headers = {"Content-Length": str(5 * 1024 * 1024 * 1024), "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Only 100 MB free disk space
            mock_usage = MagicMock()
            mock_usage.free = 100 * 1024 * 1024
            mock_disk.return_value = mock_usage

            item = DownloadItem(filename="big_game.part01.rar", share_url="https://test.co/s", direct_url="https://test.co/d")

            with pytest.raises(DiskSpaceError) as exc_info:
                downloader.download_file(item)

            assert "Insufficient disk space" in str(exc_info.value)


def test_download_cancellation_during_stream():
    """Test that calling stop() mid-stream aborts file write and leaves partial file intact."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part06.rar"
        part_path = dest / f"{filename}.part"
        final_path = dest / filename

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "2000", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            def chunk_generator():
                yield b"CHUNK_1" * 100
                # User requests cancellation
                downloader.stop()
                yield b"CHUNK_2" * 100

            resp = MagicMock()
            resp.status_code = 200
            resp.headers = {"Content-Length": "2000"}
            resp.iter_content = MagicMock(return_value=chunk_generator())
            resp.__enter__.return_value = resp
            mock_get.return_value = resp

            item = DownloadItem(filename=filename, share_url="https://test.co/s", direct_url="https://test.co/d")
            ok = downloader.download_file(item)

            assert ok is False
            assert not final_path.exists()
            # Partial file must exist with first chunk written
            assert part_path.exists()
            assert part_path.stat().st_size == len(b"CHUNK_1" * 100)


def test_archive_magic_bytes_detection():
    """Test verification of archive magic bytes for RAR5, 7z, and corrupted headers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Valid RAR5 header
        rar5_file = tmp_path / "valid.rar"
        rar5_file.write_bytes(b"\x52\x61\x72\x21\x1a\x07\x01\x00" + b"\x00" * 100)
        assert verify_archive_magic_bytes(rar5_file) is True

        # Valid 7z header
        sevenz_file = tmp_path / "valid.7z"
        sevenz_file.write_bytes(b"\x37\x7a\xbc\xaf\x27\x1c" + b"\x00" * 100)
        assert verify_archive_magic_bytes(sevenz_file) is True

        # Corrupted / unknown binary header
        corrupt_file = tmp_path / "corrupt.rar"
        corrupt_file.write_bytes(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        assert verify_archive_magic_bytes(corrupt_file) is False

        # Truncated header (< 6 bytes)
        short_file = tmp_path / "short.rar"
        short_file.write_bytes(b"\x52\x61")
        assert verify_archive_magic_bytes(short_file) is False
