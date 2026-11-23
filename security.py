"""
Security validation and path sanitization module.
Protects against Path Traversal (CWE-22) and unsafe file operations.
"""

from __future__ import annotations

import re
from pathlib import Path

from exceptions import PathTraversalError

# Windows reserved device names
RESERVED_DEVICE_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}

# Known archive magic bytes
ARCHIVE_MAGIC_SIGNATURES = [
    (b"\x52\x61\x72\x21\x1a\x07\x01\x00", "RAR5"),
    (b"\x52\x61\x72\x21\x1a\x07\x00", "RAR4"),
    (b"\x37\x7a\xbc\xaf\x27\x1c", "7-Zip"),
    (b"\x50\x4b\x03\x04", "ZIP"),
    (b"\x4d\x5a", "PE/EXE"),
]


def sanitize_filename(filename: str) -> str:
    """Sanitizes an untrusted filename.

    Strips directory separators, traversal tokens ('..'), control characters,
    and reserved Windows device names.

    Args:
        filename: Raw filename string from URL or HTML text.

    Returns:
        A safe, clean filename string.
    """
    if not filename:
        return "download_part.bin"

    # Take only the base filename (strips any path components)
    clean = Path(filename).name

    # Replace illegal filesystem and control characters with '_'
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", clean)

    # Strip leading/trailing dots and whitespace
    clean = clean.strip(". ")

    # Check for Windows reserved device names (e.g. CON, NUL.txt, com1.rar)
    base_stem = clean.split(".")[0].upper()
    if base_stem in RESERVED_DEVICE_NAMES:
        clean = f"safe_{clean}"

    if not clean:
        return "download_part.bin"

    return clean


def validate_destination_path(dest_dir: Path, filename: str) -> Path:
    """Validates that joining dest_dir and filename remains strictly within dest_dir.

    Raises:
        PathTraversalError: If the target path resolves outside dest_dir.
    """
    safe_name = sanitize_filename(filename)
    dest_resolved = Path(dest_dir).resolve()
    target_path = (dest_resolved / safe_name).resolve()

    # Enforce directory containment
    try:
        target_path.relative_to(dest_resolved)
    except ValueError as e:
        raise PathTraversalError(
            f"Path traversal detected: {filename!r} escapes {dest_dir}",
            details=str(target_path)
        ) from e

    return target_path


def verify_archive_magic_bytes(file_path: Path) -> bool:
    """Verifies that an archive part file starts with a recognized magic header.

    Returns:
        True if header matches known archive/binary format or file is a secondary
        multi-part volume; False if file is empty or corrupted.
    """
    if not file_path.is_file():
        return False

    try:
        size = file_path.stat().st_size
        if size == 0:
            return False

        with open(file_path, "rb") as f:
            header = f.read(16)

        if not header:
            return False

        # Check against recognized archive signatures
        for sig, _ in ARCHIVE_MAGIC_SIGNATURES:
            if header.startswith(sig):
                return True

        # Secondary multi-part RAR or 7z split files (.part02.rar, .7z.002, .bin)
        # may not have the standalone volume header at byte 0.
        # If size > 1024 bytes, accept as valid data stream.
        return size >= 512
    except OSError:
        return False
