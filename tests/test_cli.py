from __future__ import annotations

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from cli import app
from storage import JobStatus, JobStorage

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Professional Automated FitGirl Repack Downloader CLI" in result.stdout
    assert "download" in result.stdout
    assert "diagnostics" in result.stdout
    assert "jobs" in result.stdout
    assert "verify" in result.stdout


def test_cli_diagnostics():
    result = runner.invoke(app, ["diagnostics"])
    assert result.exit_code == 0
    assert "System Diagnostics & Readiness" in result.stdout
    assert "Browser Automation" in result.stdout
    assert "Archive Unpacker" in result.stdout


def test_cli_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "Application Configuration" in result.stdout
    assert "max_concurrent_downloads" in result.stdout


def test_cli_config_set():
    result = runner.invoke(app, ["config", "set", "max_concurrent_downloads", "4"])
    assert result.exit_code == 0
    assert "updated to: 4" in result.stdout


def test_cli_config_set_invalid_key():
    result = runner.invoke(app, ["config", "set", "non_existent_key", "123"])
    assert result.exit_code == 1
    assert "Unknown configuration key" in result.stdout


def test_cli_jobs_list_empty():
    result = runner.invoke(app, ["jobs", "list"])
    assert result.exit_code == 0
    assert "Download Jobs" in result.stdout


def test_cli_jobs_show_not_found():
    result = runner.invoke(app, ["jobs", "show", "non_existent_id"])
    assert result.exit_code == 1
    assert "not found" in result.stdout


def test_cli_jobs_list_with_records():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_jobs.db"
        storage = JobStorage(db_path)
        storage.create_or_update_job(
            job_id="test_game_101",
            title="Cyber Adventure",
            page_url="https://example.com/cyber",
            download_dir=Path(tmpdir),
            total_files=3,
            status=JobStatus.COMPLETED,
        )

        # Query using cli with custom storage
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "Completed Download History" in result.stdout


def test_cli_verify_missing_folder():
    result = runner.invoke(app, ["verify", "C:/Definitely/Not/Existing/Path/12345"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_cli_verify_valid_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)
        (folder / "game.part01.rar").write_bytes(b"data" * 10)
        (folder / "game.part02.rar").write_bytes(b"data" * 10)

        result = runner.invoke(app, ["verify", str(folder)])
        assert result.exit_code == 0
        assert "Archive sequence complete" in result.stdout


def test_cli_extract_missing_folder():
    result = runner.invoke(app, ["extract", "C:/Definitely/Not/Existing/Folder"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_cli_download_help():
    result = runner.invoke(app, ["download", "--help"])
    assert result.exit_code == 0
    assert "--workers" in result.stdout
    assert "--no-extract" in result.stdout
    assert "--all-optionals" in result.stdout
    assert "--non-interactive" in result.stdout
