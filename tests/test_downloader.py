from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from downloader import ResumableDownloader
from scraper import DownloadItem
from storage import JobStorage


def test_download_file_skip_already_completed():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part01.rar"
        file_path = dest / filename
        data = b"x" * 1024
        file_path.write_bytes(data)

        downloader = ResumableDownloader(dest_dir=dest)

        # Mock HEAD response returning Content-Length: 1024
        with patch.object(downloader.session, "head") as mock_head:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"Content-Length": "1024", "Accept-Ranges": "bytes"}
            mock_head.return_value = mock_resp

            item = DownloadItem(filename=filename, share_url="https://test.co/share", direct_url="https://dl.test.co/f")
            ok = downloader.download_file(item)

            assert ok is True
            # File should remain unchanged and not re-downloaded
            assert file_path.stat().st_size == 1024
            assert downloader.telemetry.completed_files == 1


def test_download_file_range_206_resume():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part02.rar"
        part_path = dest / f"{filename}.part"

        # Existing 500 bytes downloaded
        part_path.write_bytes(b"A" * 500)

        downloader = ResumableDownloader(dest_dir=dest)

        # Mock HEAD response: total size 1000 bytes, supports Range
        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "1000", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Mock GET response with 206 Partial Content (remaining 500 bytes)
            get_resp = MagicMock()
            get_resp.status_code = 206
            get_resp.headers = {"Content-Range": "bytes 500-999/1000"}
            get_resp.iter_content = MagicMock(return_value=[b"B" * 500])
            get_resp.__enter__.return_value = get_resp
            mock_get.return_value = get_resp

            item = DownloadItem(filename=filename, share_url="https://test.co/share", direct_url="https://dl.test.co/f")
            ok = downloader.download_file(item)

            assert ok is True
            final_file = dest / filename
            assert final_file.exists()
            assert final_file.stat().st_size == 1000
            content = final_file.read_bytes()
            assert content == (b"A" * 500 + b"B" * 500)
            assert not part_path.exists()  # .part atomically renamed


def test_download_file_range_ignored_200_clean_truncate():
    """If server responds with 200 OK to a Range request, it ignored the Range.

    The downloader MUST NOT append full payload to the existing partial file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "game.part03.rar"
        part_path = dest / f"{filename}.part"

        # Existing 400 bytes
        part_path.write_bytes(b"OLD_TRASH" * 40)

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "600", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Server returns HTTP 200 with full 600 bytes
            get_resp = MagicMock()
            get_resp.status_code = 200
            get_resp.iter_content = MagicMock(return_value=[b"FRESH_DATA" * 60])
            get_resp.__enter__.return_value = get_resp
            mock_get.return_value = get_resp

            item = DownloadItem(filename=filename, share_url="https://test.co/share", direct_url="https://dl.test.co/f")
            ok = downloader.download_file(item)

            assert ok is True
            final_file = dest / filename
            assert final_file.exists()
            # File MUST be 600 bytes (clean), NOT 600 + 360 bytes (corrupted)
            assert final_file.stat().st_size == 600
            assert final_file.read_bytes() == b"FRESH_DATA" * 60


def test_download_file_size_mismatch_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        filename = "corrupted.rar"

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "1000", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            # Server delivers only 300 bytes then ends stream
            get_resp = MagicMock()
            get_resp.status_code = 200
            get_resp.iter_content = MagicMock(return_value=[b"Z" * 300])
            get_resp.__enter__.return_value = get_resp
            mock_get.return_value = get_resp

            item = DownloadItem(filename=filename, share_url="https://test.co/share", direct_url="https://dl.test.co/f")
            ok = downloader.download_file(item)

            assert ok is False
            final_file = dest / filename
            # Final file must NOT be created when incomplete
            assert not final_file.exists()


def test_download_file_path_traversal_sanitization():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        malicious_filename = "../../System32/malicious.dll"

        downloader = ResumableDownloader(dest_dir=dest)

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "100", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            get_resp = MagicMock()
            get_resp.status_code = 200
            get_resp.iter_content = MagicMock(return_value=[b"M" * 100])
            get_resp.__enter__.return_value = get_resp
            mock_get.return_value = get_resp

            item = DownloadItem(filename=malicious_filename, share_url="https://test.co", direct_url="https://dl.test.co/m")
            ok = downloader.download_file(item)

            assert ok is True
            # Sanitized file must be inside dest
            safe_file = dest / "malicious.dll"
            assert safe_file.exists()
            assert safe_file.stat().st_size == 100


def test_download_all_with_storage():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        storage = JobStorage(dest / "jobs.db")

        downloader = ResumableDownloader(
            dest_dir=dest,
            job_id="batch_job_1",
            job_title="Batch Test",
            storage=storage,
        )

        with patch.object(downloader.session, "head") as mock_head, \
             patch.object(downloader.session, "get") as mock_get:

            head_resp = MagicMock()
            head_resp.status_code = 200
            head_resp.headers = {"Content-Length": "200", "Accept-Ranges": "bytes"}
            mock_head.return_value = head_resp

            get_resp = MagicMock()
            get_resp.status_code = 200
            get_resp.iter_content = MagicMock(return_value=[b"P" * 200])
            get_resp.__enter__.return_value = get_resp
            mock_get.return_value = get_resp

            items = [
                DownloadItem(filename="part01.rar", share_url="https://ff.co/1", direct_url="https://dl.co/1"),
                DownloadItem(filename="part02.rar", share_url="https://ff.co/2", direct_url="https://dl.co/2"),
            ]

            completed = downloader.download_all(items)
            assert len(completed) == 2

            # Verify SQLite records
            job_rec = storage.get_job("batch_job_1")
            assert job_rec is not None
            assert job_rec.status.value == "COMPLETED"
            assert job_rec.downloaded_bytes == 400

            parts_rec = storage.get_parts("batch_job_1")
            assert len(parts_rec) == 2
            assert all(p.status.value == "COMPLETED" for p in parts_rec)
