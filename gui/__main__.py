"""
FitGirl Repack Downloader - GUI Module Main Execution.
Supports running via `python -m gui`.
"""

from __future__ import annotations

import sys

from gui.app import run_gui


def main() -> None:
    sys.exit(run_gui())


if __name__ == "__main__":
    main()
