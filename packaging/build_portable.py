"""
Build script for FitGirl Repack Downloader Portable Distribution.
Generates a clean standalone ZIP archive and cryptographic SHA-256 checksums.
"""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = PROJECT_ROOT / "dist"
APP_DIR = DIST_DIR / "FitGirlDownloader"
PORTABLE_ZIP = DIST_DIR / f"FitGirlDownloader-{VERSION}-windows-x64-portable.zip"
CHECKSUMS_FILE = DIST_DIR / "checksums.sha256"


def calculate_sha256(filepath: Path) -> str:
    """Computes the SHA-256 hexadecimal hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def create_portable_archive() -> None:
    """Packages dist/FitGirlDownloader into a standalone zip file."""
    if not APP_DIR.exists():
        raise FileNotFoundError(f"Build directory does not exist: {APP_DIR}")

    print(f"Creating portable zip: {PORTABLE_ZIP.name}...")

    # Copy launcher batch scripts into app directory for portable convenience
    launchers_dir = PROJECT_ROOT / "packaging" / "launchers"
    if (launchers_dir / "START_CLI.bat").exists():
        shutil.copy2(launchers_dir / "START_CLI.bat", APP_DIR / "START_CLI.bat")
    if (launchers_dir / "START_GUI.bat").exists():
        shutil.copy2(launchers_dir / "START_GUI.bat", APP_DIR / "START_GUI.bat")

    # Copy legal and documentation files
    for doc in ("README.md", "LICENSE", "THIRD_PARTY_LICENSES.md"):
        doc_path = PROJECT_ROOT / doc
        if doc_path.exists():
            shutil.copy2(doc_path, APP_DIR / doc)

    with zipfile.ZipFile(PORTABLE_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in APP_DIR.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(APP_DIR)
                zf.write(file, f"FitGirlDownloader/{arcname}")

    print(f"✔ Portable archive created successfully: {PORTABLE_ZIP} ({PORTABLE_ZIP.stat().st_size / (1024 * 1024):.1f} MB)")


def generate_checksums() -> None:
    """Generates checksums.sha256 for all distribution artifacts in dist/."""
    checksums: list[str] = []
    for ext in ("*.zip", "*.exe"):
        for artifact in DIST_DIR.glob(ext):
            h = calculate_sha256(artifact)
            entry = f"{h}  {artifact.name}"
            checksums.append(entry)
            print(f"SHA256: {entry}")

    CHECKSUMS_FILE.write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print(f"✔ Checksums written to: {CHECKSUMS_FILE}")


if __name__ == "__main__":
    create_portable_archive()
    generate_checksums()
