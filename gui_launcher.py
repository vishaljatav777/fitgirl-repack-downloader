"""
FitGirl Repack Downloader - Standalone Desktop GUI Entrypoint.
Launchable via 'python gui_launcher.py' or Windows desktop shortcut.
"""

from __future__ import annotations

import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        getattr(sys.stdout, "reconfigure", lambda **kw: None)(encoding="utf-8", errors="replace")
        getattr(sys.stderr, "reconfigure", lambda **kw: None)(encoding="utf-8", errors="replace")
    except Exception:
        pass

from gui.app import run_gui


def main() -> None:
    sys.exit(run_gui())


if __name__ == "__main__":
    main()
