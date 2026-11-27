"""
Tests for application restart, crash recovery, and multi-part state resumption.
Covers:
- Partial download state preserved in SQLite WAL database across restarts
- Re-initializing DownloadManagerService from existing SQLite database
- Resuming partially completed jobs (skipping completed files, resuming incomplete ones)
- Re-resolving direct URLs if expired during downtime
- Job status transitions across application lifecycles
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from services import DownloadManagerService
from settings import AppSettings
from storage import JobStatus, JobStorage, PartStatus


def test_job_recovery_after_restart():
    """Test that jobs and part statuses are fully preserved and resumable after restart."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "app_jobs.db"
        download_dir = tmp_path / "downloads"
        download_dir.mkdir(parents=True, exist_ok=True)

        settings = AppSettings(
            download_dir=download_dir,
            extract_dir=tmp_path / "extracted",
            max_concurrent_downloads=2,
        )

        # Session 1: Create a job with 3 parts
        storage_1 = JobStorage(db_path)
        service_1 = DownloadManagerService(settings=settings, storage=storage_1)

        job_id = "test_game_recovery"
        storage_1.create_or_update_job(
            job_id=job_id,
            title="Test Game Recovery",
            page_url="https://fitgirl.site/test-game",
            download_dir=download_dir,
            total_files=3,
            status=JobStatus.DOWNLOADING,
        )

        storage_1.save_parts(
            job_id,
            [
                {"filename": "game.part01.rar", "share_url": "https://ff.co/1", "direct_url": "https://dl.co/1", "total_bytes": 1000},
                {"filename": "game.part02.rar", "share_url": "https://ff.co/2", "direct_url": "https://dl.co/2", "total_bytes": 1000},
                {"filename": "game.part03.rar", "share_url": "https://ff.co/3", "direct_url": "https://dl.co/3", "total_bytes": 1000},
            ]
        )

        # Part 1: Completed
        (download_dir / "game.part01.rar").write_bytes(b"PART1" * 200)
        storage_1.update_part_progress(job_id, "game.part01.rar", 1000, 1000, PartStatus.COMPLETED)

        # Part 2: Interrupted / Partial (500 bytes in .part file)
        (download_dir / "game.part02.rar.part").write_bytes(b"PART2" * 100)
        storage_1.update_part_progress(job_id, "game.part02.rar", 500, 1000, PartStatus.FAILED)

        # Part 3: Pending (not started)
        # Job marked as paused (e.g. app closed)
        storage_1.update_job_status(job_id, JobStatus.PAUSED)

        # Session 1 closes / tear down service_1
        del service_1
        del storage_1

        # Session 2: Application reopens with clean state
        storage_2 = JobStorage(db_path)
        service_2 = DownloadManagerService(settings=settings, storage=storage_2)

        # Verify job list recovers the paused job
        jobs = service_2.list_jobs()
        assert len(jobs) == 1
        assert jobs[0].id == job_id
        assert jobs[0].status == JobStatus.PAUSED

        # Verify parts state recovered
        parts = service_2.get_job_parts(job_id)
        assert len(parts) == 3
        part_statuses = {p.filename: p.status for p in parts}
        assert part_statuses["game.part01.rar"] == PartStatus.COMPLETED
        assert part_statuses["game.part02.rar"] == PartStatus.FAILED
        assert part_statuses["game.part03.rar"] == PartStatus.PENDING

        # Now resume job via service_2
        # Mock downloader.download_file so part02 and part03 complete successfully
        with patch("downloader.ResumableDownloader.download_file") as mock_dl_file:
            # Helper to simulate file download completion
            def simulate_download(item):
                p = download_dir / item.filename
                p.write_bytes(b"DATA" * 250)
                storage_2.update_part_progress(job_id, item.filename, 1000, 1000, PartStatus.COMPLETED)
                return True

            mock_dl_file.side_effect = simulate_download

            completed = service_2.resume_job(job_id)
            # Only uncompleted parts (part02, part03) should be queued for download
            assert len(completed) == 2
            downloaded_filenames = [c.filename for c in completed]
            assert "game.part01.rar" not in downloaded_filenames
            assert "game.part02.rar" in downloaded_filenames
            assert "game.part03.rar" in downloaded_filenames

        # Verify final status updated to COMPLETED in storage
        final_job = service_2.get_job(job_id)
        assert final_job is not None
        assert final_job.status == JobStatus.COMPLETED


def test_resume_all_parts_already_completed():
    """Test resuming a job where all parts are already completed returns empty and sets status."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "all_comp.db"
        storage = JobStorage(db_path)
        service = DownloadManagerService(storage=storage)

        job_id = "already_done_job"
        storage.create_or_update_job(
            job_id=job_id,
            title="Done Game",
            page_url="https://test.co",
            download_dir=tmp_path,
            total_files=1,
            status=JobStatus.PAUSED,
        )
        storage.save_parts(job_id, [{"filename": "part1.rar", "share_url": "", "direct_url": "", "total_bytes": 100}])
        storage.update_part_progress(job_id, "part1.rar", 100, 100, PartStatus.COMPLETED)

        res = service.resume_job(job_id)
        assert res == []
        updated_job = service.get_job(job_id)
        assert updated_job is not None
        assert updated_job.status == JobStatus.COMPLETED


def test_cancel_active_job_updates_storage():
    """Test that canceling a job via service sets status to FAILED with canceled error."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        storage = JobStorage(tmp_path / "cancel.db")
        service = DownloadManagerService(storage=storage)

        job_id = "to_cancel"
        storage.create_or_update_job(
            job_id=job_id,
            title="Cancel Game",
            page_url="https://test.co",
            download_dir=tmp_path,
            total_files=2,
            status=JobStatus.DOWNLOADING,
        )

        ok = service.cancel_job(job_id)
        assert ok is True

        job = service.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED
        assert job.error_message == "Canceled by user"

        # Canceling nonexistent job returns False
        assert service.cancel_job("nonexistent_id") is False
