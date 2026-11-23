from __future__ import annotations

import tempfile
from pathlib import Path

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
