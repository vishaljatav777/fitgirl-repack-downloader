import sys
import os
import time
import shutil
import argparse
from pathlib import Path
from collections import deque

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console, Group
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.live import Live

from config import (
    BASE_DIR,
    DOWNLOAD_DIR,
    EXTRACT_DIR,
    MAX_CONCURRENT_DOWNLOADS,
    get_browser_path,
    get_unrar_path
)
from scraper import FitGirlScraper, GameRepack, DownloadItem
from resolver import FuckingFastResolver
from downloader import ResumableDownloader, DownloadTelemetry, ActiveFileProgress
from extractor import ArchiveVerifierExtractor

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
    sec = int(max(0, sec))
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
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

def print_banner():
    banner = """
    ╔═══════════════════════════════════════════════════════════════════════════════╗
    ║                 ⚡ FITGIRL REPACK TERMINAL DOWNLOADER ⚡                       ║
    ║   Automated Multi-Part Downloader • Live Speed & Net Bandwidth Telemetry      ║
    ║              No IDM Required • Resumable • Auto-Extraction                    ║
    ╚═══════════════════════════════════════════════════════════════════════════════╝
    """
    console.print(Panel(banner.strip(), style="bold cyan", border_style="cyan"))

def build_terminal_dashboard(
    repack_title: str,
    dest_path: Path,
    workers_count: int,
    telemetry: DownloadTelemetry,
    recent_logs: deque
) -> Group:
    """Constructs the comprehensive terminal UI dashboard."""

    # 1. Telemetry Metrics Grid
    speed_mb = telemetry.current_speed_bytes / (1024 ** 2)
    peak_mb = telemetry.peak_speed_bytes / (1024 ** 2)
    avg_mb = telemetry.average_speed_bytes / (1024 ** 2)
    net_mbps = telemetry.net_bandwidth_mbps

    cur_gb = format_bytes(telemetry.downloaded_bytes)
    tot_gb = format_bytes(telemetry.total_bytes)
    pct_total = (telemetry.downloaded_bytes / telemetry.total_bytes * 100) if telemetry.total_bytes > 0 else 0.0

    free_disk_gb = telemetry.disk_free_bytes / (1024 ** 3)
    drive_letter = str(dest_path.resolve())[:2]

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

def run_pipeline(
    url: str,
    dest_dir: Path = DOWNLOAD_DIR,
    extract_dir: Path = EXTRACT_DIR,
    auto_extract: bool = True,
    workers: int = MAX_CONCURRENT_DOWNLOADS,
    include_all_optionals: bool = False
):
    url = url.strip()
    if not url:
        console.print("[bold red]Error: No URL provided.[/]")
        return

    # Check browser availability
    browser = get_browser_path()
    if not browser:
        console.print("[bold red]✘ Error: Compatible browser (Brave / Chrome / Edge) not found on system![/]")
        return

    # Check disk space
    try:
        usage = shutil.disk_usage(dest_dir if dest_dir.exists() else BASE_DIR)
        free_gb = usage.free / (1024 ** 3)
        if free_gb < 10:
            console.print(f"[bold yellow]⚠️ Warning: Low disk space! Only {free_gb:.1f} GB available on destination drive.[/]")
    except Exception:
        pass

    scraper = FitGirlScraper()

    # Step 1: Scrape Game Page
    with console.status("[bold green]Scraping FitGirl repack page...[/]"):
        try:
            repack: GameRepack = scraper.scrape_url(url)
        except Exception as e:
            console.print(f"[bold red]Failed to scrape URL:[/] {e}")
            return

    console.print(f"\n[bold yellow]Game:[/] [bold white]{repack.title}[/]")
    console.print(f"[bold yellow]Mandatory Parts:[/] [cyan]{len(repack.parts)}[/]")
    console.print(f"[bold yellow]Optional Language Packs:[/] [cyan]{len(repack.optionals)}[/]\n")

    if not repack.parts and not repack.optionals:
        console.print("[bold red]No FuckingFast download links found on this page.[/]")
        return

    # Select items
    items_to_download = list(repack.parts)
    if include_all_optionals and repack.optionals:
        items_to_download.extend(repack.optionals)
        console.print(f"[cyan]Including all {len(repack.optionals)} optional files in download.[/]")
    elif repack.optionals:
        console.print(f"[dim]Automatically skipping {len(repack.optionals)} optional language pack(s).[/]")

    console.print(f"[bold green]Total files queued for download:[/] [cyan]{len(items_to_download)}[/]\n")

    # Step 2: Resolve Direct Download Links
    console.print("[bold cyan]Resolving direct download links via background browser...[/]")
    resolver = FuckingFastResolver(headless=True)

    with console.status("[bold cyan]Resolving links with Cloudflare bypass...[/]") as status:
        def update_progress(current, total, item):
            status.update(f"[bold cyan]Resolving {current}/{total}:[/] {item.filename[:35]}...")

        resolved_items = resolver.resolve_batch(items_to_download, progress_callback=update_progress)

    valid_resolved = [i for i in resolved_items if i.direct_url]
    console.print(f"[bold green]✔ Successfully resolved {len(valid_resolved)}/{len(items_to_download)} direct download links![/]\n")

    if not valid_resolved:
        console.print("[bold red]Could not resolve any direct links. Aborting.[/]")
        return

    # Step 3: Launch Live Terminal Telemetry Dashboard
    clean_game_title = "".join(c for c in repack.title if c.isalnum() or c in (" ", "-", "_")).strip()
    game_download_dir = dest_dir / clean_game_title
    game_download_dir.mkdir(parents=True, exist_ok=True)

    recent_logs = deque(maxlen=4)

    def log_handler(msg: str):
        t_str = time.strftime("[%H:%M:%S] ")
        recent_logs.append(t_str + msg)

    latest_telemetry = DownloadTelemetry(
        total_files=len(valid_resolved),
        active_files={}
    )

    downloader = ResumableDownloader(
        dest_dir=game_download_dir,
        max_workers=workers,
        log_callback=log_handler,
        telemetry_callback=None
    )

    console.print(f"[bold green]Starting High-Speed Download to:[/] [cyan]{game_download_dir}[/]\n")

    initial_render = build_terminal_dashboard(
        repack_title=repack.title,
        dest_path=game_download_dir,
        workers_count=workers,
        telemetry=latest_telemetry,
        recent_logs=recent_logs
    )

    try:
        with Live(initial_render, refresh_per_second=4, console=console) as live:
            def telemetry_handler(telemetry: DownloadTelemetry):
                nonlocal latest_telemetry
                latest_telemetry = telemetry
                live.update(
                    build_terminal_dashboard(
                        repack_title=repack.title,
                        dest_path=game_download_dir,
                        workers_count=workers,
                        telemetry=telemetry,
                        recent_logs=recent_logs
                    )
                )

            downloader.telemetry_callback = telemetry_handler
            completed = downloader.download_all(valid_resolved)

    except KeyboardInterrupt:
        downloader.stop()
        console.print("\n[bold yellow]⏹ Download paused by user. All progress saved! Safe to resume anytime by running main.py again.[/]\n")
        return

    console.print(f"\n[bold green]✔ Download phase finished:[/] {len(completed)}/{len(valid_resolved)} files ready in [cyan]{game_download_dir}[/]")

    # Step 4: Verification & Auto-Extraction
    if auto_extract:
        game_extract_dir = extract_dir / clean_game_title
        verifier = ArchiveVerifierExtractor(
            download_dir=game_download_dir,
            extract_dir=game_extract_dir
        )
        is_complete, parts, missing = verifier.verify_parts()

        if is_complete and parts:
            console.print("\n[bold green]✔ All multi-part RAR files verified complete! Starting auto-extraction...[/]")
            ok = verifier.extract()
            if ok:
                console.print(f"\n[bold green]🎉 Game setup is fully extracted and ready to play![/]")
                console.print(f"[bold cyan]Location:[/] [bold white]{game_extract_dir}[/]\n")
        else:
            if missing:
                console.print(f"\n[bold red]Cannot auto-extract: missing parts {missing}[/]")
            else:
                console.print("\n[yellow]No RAR parts found to extract.[/]")

def interactive_menu():
    print_banner()

    # Show quick diagnostics banner
    browser = get_browser_path()
    unrar = get_unrar_path()
    try:
        free_disk_gb = shutil.disk_usage(DOWNLOAD_DIR).free / (1024 ** 3)
    except Exception:
        free_disk_gb = 0

    diag_text = (
        f"Browser: [green]{Path(browser).name if browser else 'NOT FOUND'}[/]  •  "
        f"Unpacker: [green]{Path(unrar).name if unrar else 'NOT FOUND'}[/]  •  "
        f"Disk Space: [green]{free_disk_gb:.1f} GB Free[/]"
    )
    console.print(Panel(diag_text, style="dim", border_style="dim"))

    while True:
        console.print("\n[bold cyan]Actions:[/]")
        console.print("1. [bold white]Paste FitGirl Game URL & Download[/]")
        console.print("2. [bold white]Search Game on FitGirl Repacks[/]")
        console.print("3. [bold white]Verify & Extract previously downloaded parts[/]")
        console.print("4. [bold white]Full System Diagnostics[/]")
        console.print("5. [bold red]Exit[/]")

        choice = Prompt.ask("\nSelect option (or paste URL directly)", default="1")

        # If user pastes a URL directly instead of a number
        if choice.startswith("http://") or choice.startswith("https://") or "fitgirl-repacks.site" in choice or "fuckingfast.co" in choice:
            run_pipeline(choice.strip())
            break

        if choice == "1":
            url = Prompt.ask("\nEnter FitGirl Repack URL (e.g. https://fitgirl-repacks.site/...)")
            if url.strip():
                run_pipeline(url.strip())
                break

        elif choice == "2":
            query = Prompt.ask("\nEnter game title to search")
            if query.strip():
                scraper = FitGirlScraper()
                with console.status("[cyan]Searching FitGirl Repacks...[/]"):
                    try:
                        results = scraper.search_game(query.strip())
                    except Exception as e:
                        console.print(f"[red]Search failed:[/] {e}")
                        results = []

                if not results:
                    console.print("[yellow]No results found for that query.[/]")
                else:
                    table = Table(title="Search Results", expand=True)
                    table.add_column("#", width=4, style="dim")
                    table.add_column("Game Title", style="cyan")

                    for i, r in enumerate(results[:10], 1):
                        table.add_row(str(i), r["title"])
                    console.print(table)

                    pick = Prompt.ask("Enter number to download (or 'c' to cancel)", default="1")
                    if pick.isdigit() and 1 <= int(pick) <= len(results):
                        run_pipeline(results[int(pick) - 1]["url"])
                        break

        elif choice == "3":
            folder = Prompt.ask("Enter path to directory containing downloaded RAR parts", default=str(DOWNLOAD_DIR))
            p = Path(folder)
            if p.exists():
                verifier = ArchiveVerifierExtractor(download_dir=p, extract_dir=EXTRACT_DIR / p.name)
                verifier.extract()
            else:
                console.print("[red]Directory does not exist.[/]")

        elif choice == "4":
            diag_table = Table(title="System Diagnostics", expand=True)
            diag_table.add_column("Component", style="cyan")
            diag_table.add_column("Status", style="bold")
            diag_table.add_column("Detected Path", style="dim")

            diag_table.add_row(
                "Browser (Brave / Chrome / Edge)",
                "[green]READY[/]" if browser else "[red]NOT FOUND[/]",
                browser or "None detected"
            )
            diag_table.add_row(
                "Archiver (WinRAR / 7-Zip)",
                "[green]READY[/]" if unrar else "[yellow]MANUAL EXTRACT REQUIRED[/]",
                unrar or "None detected"
            )
            diag_table.add_row(
                "Download Directory",
                "[green]READY[/]",
                str(DOWNLOAD_DIR)
            )
            diag_table.add_row(
                "Available Storage",
                "[green]OK[/]" if free_disk_gb > 20 else "[yellow]LOW SPACE[/]",
                f"{free_disk_gb:.1f} GB Free"
            )
            console.print(diag_table)

        elif choice == "5":
            console.print("[bold green]Goodbye![/]")
            break

def main():
    parser = argparse.ArgumentParser(
        description="⚡ Automated Pure Python Terminal Game Downloader for FitGirl Repacks"
    )
    parser.add_argument("url", nargs="?", help="FitGirl repack page URL")
    parser.add_argument("--workers", type=int, default=MAX_CONCURRENT_DOWNLOADS, help="Concurrent download workers (1-5, default: 3)")
    parser.add_argument("--dir", type=str, default=str(DOWNLOAD_DIR), help="Custom download directory")
    parser.add_argument("--no-extract", action="store_true", help="Do not auto-extract archives after download")
    parser.add_argument("--all-optionals", action="store_true", help="Download all optional language/selective packs")

    args = parser.parse_args()

    if args.url:
        print_banner()
        run_pipeline(
            url=args.url,
            dest_dir=Path(args.dir),
            auto_extract=not args.no_extract,
            workers=max(1, min(args.workers, 5)),
            include_all_optionals=args.all_optionals
        )
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
