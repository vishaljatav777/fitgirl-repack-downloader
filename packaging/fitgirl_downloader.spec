# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Multi-Target Canonical Build Specification for FitGirl Repack Downloader.
Generates a consolidated distribution containing both:
  1. FitGirlDownloader.exe (PySide6 Native Desktop GUI - Windowed)
  2. FitGirlDownloaderCLI.exe (Typer/Rich Terminal CLI - Console)
Both executables share the underlying _internal/ runtime to optimize disk footprint.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(__file__).resolve().parent.parent if "__file__" in globals() else Path.cwd().resolve()
packaging_dir = project_root / "packaging"

# 1. Collect Playwright driver binaries (node.exe, driver package, etc.)
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")

# 2. Collect GUI submodules and views
gui_submodules = collect_submodules("gui")

# 3. Assemble datas, binaries, and hidden imports
all_datas = pw_datas + [
    (str(project_root / "LICENSE"), "."),
    (str(project_root / "README.md"), "."),
    (str(project_root / "THIRD_PARTY_LICENSES.md"), "."),
]

all_binaries = pw_binaries

all_hiddenimports = list(set(
    pw_hiddenimports
    + gui_submodules
    + [
        "sqlite3",
        "requests",
        "urllib3",
        "certifi",
        "bs4",
        "pydantic",
        "typer",
        "rich",
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "services",
        "storage",
        "downloader",
        "scraper",
        "resolver",
        "extractor",
        "settings",
        "security",
        "logger",
        "exceptions",
        "terminal_ui",
        "config",
        "cli",
    ]
))

excluded_packages = [
    "pytest",
    "pytest_qt",
    "pytest_cov",
    "ruff",
    "mypy",
    "tkinter",
    "unittest",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
]

version_info_gui = str(packaging_dir / "version_info.txt")
version_info_cli = str(packaging_dir / "version_info_cli.txt")

# 4. GUI Analysis & Executable (Windowed)
a_gui = Analysis(
    [str(project_root / "gui_launcher.py")],
    pathex=[str(project_root)],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_packages,
    noarchive=False,
    optimize=0,
)
pyz_gui = PYZ(a_gui.pure)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="FitGirlDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # Windowed GUI application (no command prompt window)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_info_gui if Path(version_info_gui).exists() else None,
)

# 5. CLI Analysis & Executable (Console)
a_cli = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=all_binaries,
    datas=all_datas,
    hiddenimports=all_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_packages,
    noarchive=False,
    optimize=0,
)
pyz_cli = PYZ(a_cli.pure)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="FitGirlDownloaderCLI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Console CLI for terminal interaction
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_info_cli if Path(version_info_cli).exists() else None,
)

# 6. Combined Directory Distribution Collection
coll = COLLECT(
    exe_gui,
    a_gui.binaries,
    a_gui.datas,
    exe_cli,
    a_cli.binaries,
    a_cli.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="FitGirlDownloader",
)
