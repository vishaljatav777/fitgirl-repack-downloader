"""
Terminal UI rendering components for the FitGirl Repack Downloader CLI.
Decouples all Rich dashboard and console formatting from core business logic.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from downloader import DownloadTelemetry
from settings import AppSettings
from storage import JobRecord, PartRecord

console = Console()


def format_bytes(b: float) -> str:
    """Formats bytes into human readable string (KB, MB, GB)."""
    if b >= 1024 ** 3:
        return f"{b / (1024 ** 3):.2f} GB"
    elif b >= 1024 ** 2:
        return f"{b / (1024 ** 2):.1f} MB"
    elif b >= 1024:
        return f"{b / 1024:.0f} KB"
    else:
        return f"{b:.0f} B"


def format_seconds(sec: float) -> str:
    """Formats seconds into hh:mm:ss or mm:ss."""
    sec_int = int(max(0, sec))
    h = sec_int // 3600
    m = (sec_int % 3600) // 60
    s = sec_int % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    elif m > 0:
        return f"{m}m {s:02d}s"
    else:
        return f"{s}s"


def make_progress_bar(pct: float, width: int = 24) -> str:
    """Creates a colorful visual block progress bar."""
    pct = min(1.0, max(0.0, pct))
    filled = int(width * pct)
    empty = width - filled
    return f"[bold green]{'█' * filled}[/][dim white]{'░' * empty}[/]"


def print_banner() -> None:
    """Prints the application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                 ⚡ FITGIRL REPACK TERMINAL DOWNLOADER ⚡                       ║
    ║   Automated Multi-Part Downloader • Live Speed & Net Bandwidth Telemetry      ║
    ║              No IDM Required • Resumable • SQLite Managed                     ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner.strip(), style="bold cyan", border_style="cyan"))


def build_terminal_dashboard(
    repack_title: str,
    dest_path: Path,
    workers_count: int,
    telemetry: DownloadTelemetry,
    recent_logs: deque[str],
) -> Group:
    """Constructs the comprehensive terminal UI dashboard."""
    speed_mb = telemetry.current_speed_bytes / (1024 ** 2)
    peak_mb = telemetry.peak_speed_bytes / (1024 ** 2)
    avg_mb = telemetry.average_speed_bytes / (1024 ** 2)
    net_mbps = telemetry.net_bandwidth_mbps

    cur_gb = format_bytes(telemetry.downloaded_bytes)
    tot_gb = format_bytes(telemetry.total_bytes)
    pct_total = (telemetry.downloaded_bytes / telemetry.total_bytes * 100) if telemetry.total_bytes > 0 else 0.0

    free_disk_gb = telemetry.disk_free_bytes / (1024 ** 3)
    drive_letter = str(dest_path.resolve())[:2]

    # 1. Telemetry Metrics Grid
    grid = Table.grid(expand=True)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    grid.add_row(
        f"[bold cyan]🚀 Download Speed:[/] [bold white]{speed_mb:.1f} MB/s[/]  [dim]•[/]  [bold blue]🌐 Net Line:[/] [bold white]{net_mbps:.1f} Mbps[/]",
        f"[bold yellow]⏱️  Estimated Time (ETA):[/] [bold white]{format_seconds(telemetry.eta_seconds)}[/]"
    )
    grid.add_row(
        f"[bold magenta]⚡ Peak Speed:[/] [white]{peak_mb:.1f} MB/s[/]  [dim]•[/]  [bold blue]📈 Average:[/] [white]{avg_mb:.1f} MB/s[/]",
        f"[bold white]⏳ Elapsed Time:[/] [white]{format_seconds(telemetry.elapsed_seconds)}[/]"
    )
    grid.add_row(
        f"[bold green]💾 Data Transferred:[/] [bold white]{cur_gb}[/] / [white]{tot_gb}[/] ([bold green]{pct_total:.1f}%[/])",
        f"[bold purple]💽 Target Drive Free:[/] [bold white]{free_disk_gb:.1f} GB[/] [dim]({drive_letter})[/]"
    )
    grid.add_row(
        f"[bold white]📦 Parts Completed:[/] [bold cyan]{telemetry.completed_files}[/] of [cyan]{telemetry.total_files}[/] parts ([cyan]{(telemetry.completed_files / max(1, telemetry.total_files))*100:.1f}%[/])",
        f"[bold dim]📁 Destination:[/] [dim]{str(dest_path)[-40:]}[/]"
    )

    telemetry_panel = Panel(grid, title="[bold cyan]📊 Live Telemetry & Network Bandwidth[/]", border_style="cyan")

    # 2. Overall Progress Bar Panel
    overall_pct_ratio = (telemetry.downloaded_bytes / telemetry.total_bytes) if telemetry.total_bytes > 0 else 0.0
    overall_bar_str = f"{make_progress_bar(overall_pct_ratio, width=42)}  [bold white]{pct_total:.1f}%[/] [dim]({cur_gb} / {tot_gb})[/]"
    overall_panel = Panel(overall_bar_str, title="[bold blue]🚀 Overall Game Download Progress[/]", border_style="blue")

    # 3. Active Concurrent Download Streams
    streams_table = Table(expand=True, box=None)
    streams_table.add_column("Worker", style="bold cyan", width=8)
    streams_table.add_column("File Name", style="white", ratio=2)
    streams_table.add_column("Downloaded / Size", style="dim", width=22)
    streams_table.add_column("Speed", style="green", width=12)
    streams_table.add_column("Stream Progress", width=34)

    active_items = list(telemetry.active_files.values())
    if active_items:
        for idx, af in enumerate(active_items, 1):
            f_speed = af.speed_bytes_sec / (1024 ** 2)
            f_cur = format_bytes(af.downloaded_bytes)
            f_tot = format_bytes(af.total_bytes)
            f_pct = af.percentage * 100
            streams_table.add_row(
                f"#{idx}",
                af.filename[:30] + ("..." if len(af.filename) > 30 else ""),
                f"{f_cur} / {f_tot}",
                f"{f_speed:.1f} MB/s",
                f"{make_progress_bar(af.percentage, width=20)} {f_pct:>3.0f}%"
            )
    else:
        streams_table.add_row(
            "[dim]#1[/]",
            "[dim]Waiting for next chunk in queue...[/]",
            "-- / --",
            "0.0 MB/s",
            f"{make_progress_bar(0.0, width=20)}   0%"
        )

    streams_panel = Panel(
        streams_table,
        title=f"[bold green]🔄 Active Download Streams (Batch Workers: {workers_count})[/]",
        border_style="green"
    )

    # 4. Activity Logs Panel
    log_text = "\n".join(recent_logs) if recent_logs else "[dim]Initializing download pipeline...[/]"
    logs_panel = Panel(log_text, title="[bold dim]📜 Recent Activity Feed[/]", border_style="dim")

    return Group(telemetry_panel, overall_panel, streams_panel, logs_panel)


def render_jobs_table(jobs: list[JobRecord], title: str = "Download Jobs") -> Table:
    """Renders a formatted table of download jobs."""
    table = Table(title=title, expand=True)
    table.add_column("Job ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white", ratio=2)
    table.add_column("Parts", style="dim", width=10)
    table.add_column("Downloaded", style="green", width=18)
    table.add_column("Status", style="bold", width=14)

    status_styles = {
        "COMPLETED": "[green]COMPLETED[/]",
        "DOWNLOADING": "[cyan]DOWNLOADING[/]",
        "PAUSED": "[yellow]PAUSED[/]",
        "FAILED": "[red]FAILED[/]",
        "PENDING": "[dim]PENDING[/]",
        "VERIFYING": "[magenta]VERIFYING[/]",
    }

    if not jobs:
        table.add_row("No jobs found", "--", "--", "--", "--")
    else:
        for j in jobs:
            st_text = status_styles.get(j.status.value, j.status.value)
            cur = format_bytes(j.downloaded_bytes)
            tot = format_bytes(j.total_bytes) if j.total_bytes > 0 else "--"
            table.add_row(
                j.id[:20] + ("..." if len(j.id) > 20 else ""),
                j.title[:40] + ("..." if len(j.title) > 40 else ""),
                str(j.total_files),
                f"{cur} / {tot}",
                st_text
            )
    return table


def render_parts_table(parts: list[PartRecord], job_id: str) -> Table:
    """Renders a formatted table of individual job parts."""
    table = Table(title=f"Parts for Job: {job_id}", expand=True)
    table.add_column("#", width=4, style="dim")
    table.add_column("Filename", style="cyan", ratio=2)
    table.add_column("Size", style="dim", width=14)
    table.add_column("Downloaded", style="dim", width=14)
    table.add_column("Status", style="bold", width=14)

    for p in parts:
        sz = format_bytes(p.total_bytes) if p.total_bytes > 0 else "--"
        dl = format_bytes(p.downloaded_bytes)
        st = "[green]DONE[/]" if p.status.value == "COMPLETED" else f"[dim]{p.status.value}[/]"
        table.add_row(str(p.part_number), p.filename, sz, dl, st)

    return table


def render_diagnostics_table(diag: dict[str, Any]) -> Table:
    """Renders a system diagnostics table."""
    table = Table(title="⚡ System Diagnostics & Readiness", expand=True)
    table.add_column("Component", style="cyan", width=24)
    table.add_column("Status", style="bold", width=14)
    table.add_column("Detected Path / Value", style="dim")

    table.add_row(
        "Browser Automation",
        "[green]READY[/]" if diag["browser_ready"] else "[red]NOT FOUND[/]",
        diag["browser_path"]
    )
    table.add_row(
        "Archive Unpacker",
        "[green]READY[/]" if diag["unrar_ready"] else "[yellow]MANUAL EXTRACT[/]",
        diag["unrar_path"]
    )
    table.add_row(
        "Download Directory",
        "[green]READY[/]",
        diag["download_dir"]
    )
    table.add_row(
        "Extract Directory",
        "[green]READY[/]",
        diag["extract_dir"]
    )
    table.add_row(
        "Available Storage",
        "[green]OK[/]" if diag["storage_free_gb"] > 20 else "[yellow]LOW SPACE[/]",
        f"{diag['storage_free_gb']:.1f} GB Free (of {diag['storage_total_gb']:.1f} GB)"
    )
    table.add_row(
        "Default Concurrency",
        "[green]OK[/]",
        f"{diag['max_workers']} concurrent workers"
    )
    return table


def render_settings_table(settings: AppSettings) -> Table:
    """Renders an application configuration table."""
    table = Table(title="⚙️ Application Configuration", expand=True)
    table.add_column("Setting Key", style="cyan", width=28)
    table.add_column("Current Value", style="white")

    for k in (
        "download_dir", "extract_dir", "max_concurrent_downloads",
        "chunk_size", "timeout", "max_retries", "auto_extract", "include_optionals"
    ):
        table.add_row(k, str(getattr(settings, k, "")))
    return table


def render_search_results_table(results: list[dict[str, str]]) -> Table:
    """Renders search results table."""
    table = Table(title="FitGirl Catalog Search Results", expand=True)
    table.add_column("#", width=4, style="dim")
    table.add_column("Game Title", style="cyan")

    for i, r in enumerate(results[:15], 1):
        table.add_row(str(i), r["title"])
    return table
