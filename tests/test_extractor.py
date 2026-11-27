from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from extractor import ArchiveVerifierExtractor


def test_verify_parts_empty_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        is_complete, files, missing = verifier.verify_parts()
        assert is_complete is False
        assert len(files) == 0
        assert len(missing) == 0


def test_verify_parts_complete_sequence():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create part01.rar, part02.rar, part03.rar
        for i in range(1, 4):
            f = tmp_path / f"game.part{i:02d}.rar"
            f.write_bytes(b"dummy data" * 10)

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        is_complete, files, missing = verifier.verify_parts()
        assert is_complete is True
        assert len(files) == 3
        assert len(missing) == 0


def test_verify_parts_missing_part():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        # Create part01.rar and part03.rar (missing part02.rar)
        (tmp_path / "game.part01.rar").write_bytes(b"dummy")
        (tmp_path / "game.part03.rar").write_bytes(b"dummy")

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        is_complete, files, missing = verifier.verify_parts()
        assert is_complete is False
        assert missing == [2]


def test_verify_parts_single_rar():
    """Single .rar without part numbering should be recognized as complete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "standalone.rar").write_bytes(b"dummy")

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        is_complete, files, missing = verifier.verify_parts()
        assert is_complete is True
        assert len(files) == 1
        assert len(missing) == 0


def test_verify_parts_zero_byte_part():
    """A 0-byte file in sequence should be detected as missing/incomplete."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")
        (tmp_path / "game.part02.rar").write_bytes(b"")  # 0 bytes

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        is_complete, files, missing = verifier.verify_parts()
        assert is_complete is False
        assert 2 in missing


def test_extract_no_parts():
    """extract() returns False when directory has no RAR files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        assert verifier.extract() is False


def test_extract_incomplete_parts():
    """extract() returns False when parts are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")
        (tmp_path / "game.part03.rar").write_bytes(b"data")

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        assert verifier.extract() is False


def test_extract_missing_unpacker():
    """extract() returns False when unrar_path is empty."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        verifier.unrar_path = ""
        assert verifier.extract() is False


def test_extract_7z_success():
    """Test successful extraction invocation with 7-Zip."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")
        ext_dir = tmp_path / "extracted"

        verifier = ArchiveVerifierExtractor(tmp_path, ext_dir)
        verifier.unrar_path = "C:/Program Files/7-Zip/7z.exe"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
            ok = verifier.extract()
            assert ok is True
            assert mock_run.called
            cmd = mock_run.call_args[0][0]
            assert "7z.exe" in cmd[0]
            assert "x" in cmd
            assert f"-o{str(ext_dir)}" in cmd


def test_extract_winrar_success():
    """Test successful extraction invocation with WinRAR."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")
        ext_dir = tmp_path / "extracted"

        verifier = ArchiveVerifierExtractor(tmp_path, ext_dir)
        verifier.unrar_path = "C:/Program Files/WinRAR/UnRAR.exe"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
            ok = verifier.extract()
            assert ok is True
            cmd = mock_run.call_args[0][0]
            assert "UnRAR.exe" in cmd[0]
            assert "-o+" in cmd


def test_extract_subprocess_failure():
    """Test extract() handles non-zero exit code gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        verifier.unrar_path = "C:/Program Files/7-Zip/7z.exe"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="Corrupted archive")
            assert verifier.extract() is False


def test_extract_subprocess_exception():
    """Test extract() handles subprocess exception without crashing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        (tmp_path / "game.part01.rar").write_bytes(b"data")

        verifier = ArchiveVerifierExtractor(tmp_path, tmp_path / "extracted")
        verifier.unrar_path = "C:/Program Files/7-Zip/7z.exe"

        with patch("subprocess.run", side_effect=OSError("Binary not executable")):
            assert verifier.extract() is False
