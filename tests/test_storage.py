from __future__ import annotations

import tempfile
from pathlib import Path

from storage import JobRecord, JobStatus, JobStorage, PartStatus


def test_job_storage_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_jobs.db"
        storage = JobStorage(db_path)

        # Create
        job = storage.create_or_update_job(
            job_id="game_1",
            title="Test Game",
            page_url="https://fitgirl-repacks.site/test-game",
            download_dir=Path(tmpdir) / "downloads",
            total_files=5,
            total_bytes=1000,
            status=JobStatus.DOWNLOADING,
        )
        assert isinstance(job, JobRecord)
        assert job.id == "game_1"
        assert job.status == JobStatus.DOWNLOADING
        assert job.total_files == 5

        # Query by ID
        fetched = storage.get_job("game_1")
        assert fetched is not None
        assert fetched.title == "Test Game"

        # Query by URL
        fetched_url = storage.get_job_by_url("https://fitgirl-repacks.site/test-game")
        assert fetched_url is not None
        assert fetched_url.id == "game_1"

        # Update status
        storage.update_job_status("game_1", JobStatus.COMPLETED)
        updated = storage.get_job("game_1")
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED

        # List
        all_jobs = storage.list_jobs()
        assert len(all_jobs) == 1
        completed = storage.list_jobs(status=JobStatus.COMPLETED)
        assert len(completed) == 1


def test_job_storage_parts_and_progress():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_jobs.db"
        storage = JobStorage(db_path)

        storage.create_or_update_job(
            job_id="job_parts",
            title="Parts Test",
            page_url="https://fitgirl-repacks.site/parts",
            download_dir=Path(tmpdir),
            total_files=2,
            total_bytes=200,
        )

        parts = [
            {"filename": "part1.rar", "share_url": "https://ff.co/1", "total_bytes": 100},
            {"filename": "part2.rar", "share_url": "https://ff.co/2", "total_bytes": 100},
        ]
        storage.save_parts("job_parts", parts)

        saved_parts = storage.get_parts("job_parts")
        assert len(saved_parts) == 2
        assert saved_parts[0].filename == "part1.rar"
        assert saved_parts[0].status == PartStatus.PENDING

        # Update progress on part 1
        storage.update_part_progress(
            "job_parts", "part1.rar", downloaded_bytes=50, total_bytes=100, status=PartStatus.DOWNLOADING
        )

        p1 = storage.get_parts("job_parts")[0]
        assert p1.downloaded_bytes == 50
        assert p1.status == PartStatus.DOWNLOADING

        # Check that job aggregate downloaded_bytes was updated automatically
        job = storage.get_job("job_parts")
        assert job is not None
        assert job.downloaded_bytes == 50

        # Mark part 1 complete
        storage.update_part_progress(
            "job_parts", "part1.rar", downloaded_bytes=100, total_bytes=100, status=PartStatus.COMPLETED
        )
        p1_done = storage.get_parts("job_parts")[0]
        assert p1_done.status == PartStatus.COMPLETED


def test_job_storage_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "persistent.db"

        # Instance 1
        s1 = JobStorage(db_path)
        s1.create_or_update_job(
            job_id="rec_job",
            title="Recoverable",
            page_url="https://example.com/rec",
            download_dir=Path(tmpdir),
            total_files=1,
            status=JobStatus.PAUSED,
        )

        # Instance 2 (simulating application restart)
        s2 = JobStorage(db_path)
        recovered = s2.get_job("rec_job")
        assert recovered is not None
        assert recovered.title == "Recoverable"
        assert recovered.status == JobStatus.PAUSED
