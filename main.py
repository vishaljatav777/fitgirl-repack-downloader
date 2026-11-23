"""
FitGirl Repack Downloader - Primary Entrypoint.
Dispatches to the Typer CLI application while maintaining backward-compatible helper exports.
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

from cli import app, execute_download_pipeline, run_interactive
from terminal_ui import (
    build_terminal_dashboard,
    format_bytes,
    format_seconds,
    make_progress_bar,
    print_banner,
)

# Backward-compatibility alias functions
run_pipeline = execute_download_pipeline
interactive_menu = run_interactive

__all__ = [
    "app",
    "build_terminal_dashboard",
    "execute_download_pipeline",
    "format_bytes",
    "format_seconds",
    "interactive_menu",
    "main",
    "make_progress_bar",
    "print_banner",
    "run_pipeline",
]


def main() -> None:
    # If user ran `python main.py <url>` directly (backward compatibility),
    # transform `python main.py <url> ...` to `python main.py download <url> ...`
    if len(sys.argv) > 1:
        first = sys.argv[1].strip()
        subcommands = {"download", "search", "history", "verify", "extract", "diagnostics", "jobs", "config", "--help", "-h"}
        if first not in subcommands and not first.startswith("-"):
            # It's a direct URL or path! Insert 'download' subcommand
            sys.argv.insert(1, "download")
    app()


if __name__ == "__main__":
    main()
