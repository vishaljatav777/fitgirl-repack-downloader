from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from exceptions import ConfigurationError
from settings import AppSettings, detect_executable, get_settings


def test_settings_defaults():
    s = AppSettings()
    assert s.max_concurrent_downloads == 3
    assert s.chunk_size == 1024 * 1024
    assert s.timeout == 30
    assert s.max_retries == 5
    assert "Mozilla" in s.user_agent


def test_settings_validation_invalid_concurrency():
    with pytest.raises(ConfigurationError, match="max_concurrent_downloads"):
        AppSettings(max_concurrent_downloads=0)

    with pytest.raises(ConfigurationError, match="max_concurrent_downloads"):
        AppSettings(max_concurrent_downloads=11)


def test_settings_validation_invalid_chunk_size():
    with pytest.raises(ConfigurationError, match="chunk_size"):
        AppSettings(chunk_size=1024)  # Less than 64 KB


def test_settings_validation_invalid_timeout():
    with pytest.raises(ConfigurationError, match="timeout"):
        AppSettings(timeout=2)


def test_settings_validation_invalid_retries():
    with pytest.raises(ConfigurationError, match="max_retries"):
        AppSettings(max_retries=-1)


def test_ensure_directories():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        d_dir = base / "custom_downloads"
        e_dir = base / "custom_extract"

        s = AppSettings(download_dir=d_dir, extract_dir=e_dir)
        assert not d_dir.exists()
        assert not e_dir.exists()

        s.ensure_directories()
        assert d_dir.exists()
        assert e_dir.exists()


def test_detect_executable_found():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tf:
        tf_path = tf.name

    try:
        found = detect_executable([tf_path])
        assert found == tf_path
    finally:
        Path(tf_path).unlink(missing_ok=True)


def test_detect_executable_not_found():
    found = detect_executable([r"C:\NonExistent\FakeExecutable_12345.exe"])
    assert found is None


def test_get_settings_singleton():
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_frozen_mode_portable_paths(monkeypatch):
    from settings import get_default_base_dir, get_default_download_dir, get_default_extract_dir

    portable_exe = r"D:\PortableApps\FitGirlDownloader\FitGirlDownloader.exe"
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", portable_exe)

    base = get_default_base_dir()
    download = get_default_download_dir()
    extract = get_default_extract_dir()

    assert base == Path(r"D:\PortableApps\FitGirlDownloader")
    assert download == Path(r"D:\PortableApps\FitGirlDownloader\downloads")
    assert extract == Path(r"D:\PortableApps\FitGirlDownloader\extracted")


def test_frozen_mode_program_files_fallback(monkeypatch):
    from settings import get_default_base_dir, get_default_download_dir, get_default_extract_dir

    installed_exe = r"C:\Program Files\FitGirl Downloader\FitGirlDownloader.exe"
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", installed_exe)
    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\TestUser\AppData\Local")

    base = get_default_base_dir()
    download = get_default_download_dir()
    extract = get_default_extract_dir()

    assert base == Path(r"C:\Users\TestUser\AppData\Local\FitGirlDownloader")
    assert download == Path.home() / "Downloads" / "FitGirlDownloader"
    assert extract == Path.home() / "Downloads" / "FitGirlDownloader" / "extracted"

