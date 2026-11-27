# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for FitGirl Repack Downloader (Root Alias).
Points to the canonical build specification in packaging/fitgirl_downloader.spec.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Load and execute the canonical build specification from packaging/
canonical_spec = Path("packaging") / "fitgirl_downloader.spec"
if not canonical_spec.exists():
    raise FileNotFoundError(f"Canonical specification not found: {canonical_spec}")

with open(canonical_spec, "rb") as f:
    exec(compile(f.read(), str(canonical_spec), "exec"))
