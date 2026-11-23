from __future__ import annotations

import tempfile
from pathlib import Path

from security import (
    sanitize_filename,
    validate_destination_path,
    verify_archive_magic_bytes,
)


def test_sanitize_filename_traversal():
    assert sanitize_filename("../../Windows/System32/evil.dll") == "evil.dll"
    assert sanitize_filename("..\\..\\Windows\\calc.exe") == "calc.exe"
    assert sanitize_filename("/etc/passwd") == "passwd"
    assert sanitize_filename(".../foo/bar.part01.rar") == "bar.part01.rar"


def test_sanitize_filename_reserved_windows_names():
    assert sanitize_filename("con.txt") == "safe_con.txt"
    assert sanitize_filename("NUL") == "safe_NUL"
    assert sanitize_filename("com1.rar") == "safe_com1.rar"
    assert sanitize_filename("aux.tar.gz") == "safe_aux.tar.gz"


def test_sanitize_filename_illegal_characters():
    assert sanitize_filename("game:part?*|<>.rar") == "game_part_____.rar"
    assert sanitize_filename("") == "download_part.bin"
    assert sanitize_filename("   ...   ") == "download_part.bin"


def test_validate_destination_path_safe():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest = Path(tmpdir)
        target = validate_destination_path(dest, "game.part01.rar")
        assert target.parent == dest.resolve()
        assert target.name == "game.part01.rar"


def test_verify_archive_magic_bytes_rar5():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"\x52\x61\x72\x21\x1a\x07\x01\x00" + b"\x00" * 32)
        tf_path = Path(tf.name)

    try:
        assert verify_archive_magic_bytes(tf_path) is True
    finally:
        tf_path.unlink(missing_ok=True)


def test_verify_archive_magic_bytes_7zip():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"\x37\x7a\xbc\xaf\x27\x1c" + b"\x00" * 32)
        tf_path = Path(tf.name)

    try:
        assert verify_archive_magic_bytes(tf_path) is True
    finally:
        tf_path.unlink(missing_ok=True)


def test_verify_archive_magic_bytes_empty_or_missing():
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        pass  # 0 bytes
        tf_path = Path(tf.name)

    try:
        assert verify_archive_magic_bytes(tf_path) is False
    finally:
        tf_path.unlink(missing_ok=True)

    assert verify_archive_magic_bytes(Path("non_existent_file.rar")) is False
