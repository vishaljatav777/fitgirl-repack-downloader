"""
Typer CLI implementation for the FitGirl Repack Downloader.
Provides command-line commands, interactive wizard, job management,
diagnostics, settings, archive verification, and download history.
"""

from __future__ import annotations

import sys
import time
from collections import deque
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, Prompt

from downloader import DownloadTelemetry
from services import DownloadManagerService
from storage import JobStatus
from terminal_ui import (
    build_terminal_dashboard,
    print_banner,
    render_diagnostics_table,
    render_jobs_table,
    render_parts_table,
    render_search_results_table,
    render_settings_table,
)

console = Console()
app = typer.Typer(
    name="fitgirl",
    help="⚡ Professional Automated FitGirl Repack Downloader CLI",
    no_args_is_help=False,
    add_completion=False,
)
jobs_app = typer.Typer(help="Manage background and persistent download jobs")
config_app = typer.Typer(help="Inspect and configure application settings")

app.add_typer(jobs_app, name="jobs")
app.add_typer(config_app, name="config")


def get_service() -> DownloadManagerService:
    """Helper to instantiate application service."""
    return DownloadManagerService()


def execute_download_pipeline(
    url: str,
    dest_dir: Path | None = None,
    workers: int | None = None,
    auto_extract: bool = True,
    all_optionals: bool = False,
    non_interactive: bool = False,
) -> None:
    """Executes the full scrape -> resolve -> download -> verify -> extract pipeline."""
    service = get_service()

    # Step 1: Scrape
    with console.status("[bold green]Scraping FitGirl repack page...[/]"):
        try:
            repack = service.scrape_repack(url)
        except Exception as e:
            console.print(f"[bold red]✘ Failed to scrape URL:[/] {e}")
            raise typer.Exit(code=1) from e

    console.print(f"\n[bold yellow]Game:[/] [bold white]{repack.title}[/]")
    console.print(f"[bold yellow]Mandatory Parts:[/] [cyan]{len(repack.parts)}[/]")
    console.print(f"[bold yellow]Optional Language Packs:[/] [cyan]{len(repack.optionals)}[/]\n")

    items = list(repack.parts)
    if all_optionals and repack.optionals:
        items.extend(repack.optionals)
        console.print(f"[cyan]Including {len(repack.optionals)} optional files in download queue.[/]")
    elif repack.optionals:
        console.print(f"[dim]Automatically skipping {len(repack.optionals)} optional language pack(s).[/]")

    if not items:
        console.print("[bold red]No download links found to download.[/]")
        raise typer.Exit(code=1)

    # Step 2: Resolve Direct Links
    console.print("[bold cyan]Resolving direct download links via background browser...[/]")
    with console.status("[bold cyan]Resolving links with Cloudflare bypass...[/]") as status:
        def update_progress(current: int, total: int, item: Any) -> None:
            status.update(f"[bold cyan]Resolving {current}/{total}:[/] {item.filename[:35]}...")

        try:
            resolved_items = service.resolve_links(items, progress_callback=update_progress)
        except Exception as e:
            console.print(f"[bold red]✘ Resolver error:[/] {e}")
            raise typer.Exit(code=1) from e

    valid_resolved = [i for i in resolved_items if i.direct_url]
    console.print(f"[bold green]✔ Successfully resolved {len(valid_resolved)}/{len(items)} direct links![/]\n")

    if not valid_resolved:
        console.print("[bold red]Could not resolve any direct links. Aborting.[/]")
        raise typer.Exit(code=1)

    # Step 3: Download with Live Dashboard
    target_dir = dest_dir or (service.settings.download_dir / repack.title.replace(":", " -"))
    target_dir.mkdir(parents=True, exist_ok=True)

    recent_logs: deque[str] = deque(maxlen=4)

    def log_handler(msg: str) -> None:
        recent_logs.append(time.strftime("[%H:%M:%S] ") + msg)

    latest_telemetry = DownloadTelemetry(
        total_files=len(valid_resolved),
        active_files={}
    )

    console.print(f"[bold green]Starting High-Speed Download to:[/] [cyan]{target_dir}[/]\n")

    completed_items: list[Any] = []
    if non_interactive or not sys.stdout.isatty():
        # Clean streaming log mode for non-TTY / CI
        completed_items = service.start_download(
            repack=repack,
            items=valid_resolved,
            dest_dir=target_dir,
            workers=workers,
            log_callback=lambda m: console.print(f"[dim]{time.strftime('[%H:%M:%S]')}[/] {m}"),
        )
    else:
        # Full Rich live updating dashboard
        initial_render = build_terminal_dashboard(
            repack_title=repack.title,
            dest_path=target_dir,
            workers_count=workers or service.settings.max_concurrent_downloads,
            telemetry=latest_telemetry,
            recent_logs=recent_logs,
        )
        try:
            with Live(initial_render, refresh_per_second=4, console=console) as live:
                def telemetry_handler(telemetry: DownloadTelemetry) -> None:
                    live.update(
                        build_terminal_dashboard(
                            repack_title=repack.title,
                            dest_path=target_dir,
                            workers_count=workers or service.settings.max_concurrent_downloads,
                            telemetry=telemetry,
                            recent_logs=recent_logs,
                        )
                    )

                completed_items = service.start_download(
                    repack=repack,
                    items=valid_resolved,
                    dest_dir=target_dir,
                    workers=workers,
                    telemetry_callback=telemetry_handler,
                    log_callback=log_handler,
                )
        except KeyboardInterrupt:
            service.pause_active_download()
            console.print("\n[bold yellow]⏹ Download paused by user. Progress saved! Resume anytime.[/]\n")
            return

    console.print(f"\n[bold green]✔ Download phase finished:[/] {len(completed_items)}/{len(valid_resolved)} files ready in [cyan]{target_dir}[/]")

    # Step 4: Verification & Auto-Extraction
    if auto_extract:
        is_complete, archive_files, missing = service.verify_archive(target_dir)
        if is_complete and archive_files:
            console.print("\n[bold green]✔ All multi-part RAR files verified complete! Starting extraction...[/]")
            ok = service.extract_archive(target_dir)
            if ok:
                console.print("\n[bold green]🎉 Extraction complete![/]")
        elif missing:
            console.print(f"\n[bold red]Cannot auto-extract: missing parts {missing}[/]")


@app.command("download")
def download_cmd(
    url: str = typer.Argument(..., help="FitGirl repack page URL or direct FuckingFast share link"),
    workers: int = typer.Option(3, "--workers", "-w", min=1, max=10, help="Concurrent download workers"),
    dir: Path | None = typer.Option(None, "--dir", "-d", help="Custom destination folder"),
    no_extract: bool = typer.Option(False, "--no-extract", help="Skip automatic archive extraction"),
    all_optionals: bool = typer.Option(False, "--all-optionals", help="Include optional language/voice packs"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Disable Rich Live dashboard (plain log output)"),
) -> None:
    """Download a FitGirl game repack by URL."""
    print_banner()
    execute_download_pipeline(
        url=url,
        dest_dir=dir,
        workers=workers,
        auto_extract=not no_extract,
        all_optionals=all_optionals,
        non_interactive=non_interactive,
    )


@app.command("search")
def search_cmd(query: str = typer.Argument(..., help="Game title to search")) -> None:
    """Search FitGirl catalog for game titles."""
    print_banner()
    service = get_service()
    with console.status(f"[cyan]Searching FitGirl catalog for '{query}'...[/]"):
        results = service.search_repacks(query)

    if not results:
        console.print(f"[yellow]No results found for query '{query}'.[/]")
        return

    console.print(render_search_results_table(results))


@app.command("history")
def history_cmd() -> None:
    """List completed download history."""
    print_banner()
    service = get_service()
    completed_jobs = service.list_jobs(status=JobStatus.COMPLETED)
    console.print(render_jobs_table(completed_jobs, title="🏆 Completed Download History"))


@app.command("verify")
def verify_cmd(folder: Path = typer.Argument(..., help="Folder containing downloaded RAR/7z parts")) -> None:
    """Verify sequence and integrity of multi-part archives in a folder."""
    print_banner()
    service = get_service()
    if not folder.exists():
        console.print(f"[bold red]Folder '{folder}' does not exist.[/]")
        raise typer.Exit(code=1)

    is_complete, archive_files, missing = service.verify_archive(folder)
    if is_complete and archive_files:
        console.print(f"[bold green]✔ Archive sequence complete! Found {len(archive_files)} parts in:[/] {folder}")
    else:
        if missing:
            console.print(f"[bold red]✘ Incomplete archive sequence! Missing part numbers: {missing}[/]")
        else:
            console.print(f"[bold yellow]No multi-part RAR files found in:[/] {folder}")


@app.command("extract")
def extract_cmd(
    download_dir: Path = typer.Argument(..., help="Folder containing downloaded parts"),
    extract_dir: Path | None = typer.Option(None, "--out", "-o", help="Custom extraction destination"),
) -> None:
    """Extract a verified multi-part archive using 7-Zip or WinRAR."""
    print_banner()
    service = get_service()
    if not download_dir.exists():
        console.print(f"[bold red]Folder '{download_dir}' does not exist.[/]")
        raise typer.Exit(code=1)

    ok = service.extract_archive(download_dir=download_dir, extract_dir=extract_dir)
    if not ok:
        raise typer.Exit(code=1)


@app.command("diagnostics")
def diagnostics_cmd() -> None:
    """Run full system diagnostics and check readiness."""
    print_banner()
    service = get_service()
    diag = service.get_diagnostics()
    console.print(render_diagnostics_table(diag))


@app.command("gui")
def gui_cmd() -> None:
    """Launch the Windows native PySide6 desktop GUI."""
    from gui.app import run_gui
    run_gui()


@jobs_app.command("list")
def jobs_list_cmd(status: str | None = typer.Option(None, help="Filter by status (COMPLETED, DOWNLOADING, PAUSED, FAILED)")) -> None:
    """List all persistent download jobs."""
    service = get_service()
    st_filter = JobStatus(status.upper()) if status else None
    jobs = service.list_jobs(status=st_filter)
    console.print(render_jobs_table(jobs))


@jobs_app.command("show")
def jobs_show_cmd(job_id: str = typer.Argument(..., help="Job ID to inspect")) -> None:
    """Inspect individual parts for a download job."""
    service = get_service()
    job = service.get_job(job_id)
    if not job:
        console.print(f"[bold red]Job '{job_id}' not found.[/]")
        raise typer.Exit(code=1)

    parts = service.get_job_parts(job_id)
    console.print(render_parts_table(parts, job_id))


@jobs_app.command("resume")
def jobs_resume_cmd(job_id: str = typer.Argument(..., help="Job ID to resume")) -> None:
    """Resume an interrupted or paused download job."""
    service = get_service()
    job = service.get_job(job_id)
    if not job:
        console.print(f"[bold red]Job '{job_id}' not found.[/]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Resuming job:[/] {job.title} ({job.id})")
    service.resume_job(job_id)


@jobs_app.command("cancel")
def jobs_cancel_cmd(job_id: str = typer.Argument(..., help="Job ID to cancel")) -> None:
    """Cancel an active or paused download job."""
    service = get_service()
    ok = service.cancel_job(job_id)
    if ok:
        console.print(f"[bold green]✔ Job '{job_id}' successfully canceled.[/]")
    else:
        console.print(f"[bold red]✘ Job '{job_id}' not found.[/]")


@config_app.command("show")
def config_show_cmd() -> None:
    """Show current application settings."""
    service = get_service()
    console.print(render_settings_table(service.settings))


@config_app.command("set")
def config_set_cmd(
    key: str = typer.Argument(..., help="Setting key to modify"),
    val: str = typer.Argument(..., help="New value for setting"),
) -> None:
    """Update an application setting."""
    service = get_service()
    try:
        # Cast numerical values if applicable
        if val.isdigit():
            service.update_setting(key, int(val))
        elif val.lower() in ("true", "false"):
            service.update_setting(key, val.lower() == "true")
        else:
            service.update_setting(key, val)
        console.print(f"[bold green]✔ Setting '{key}' updated to:[/] {val}")
    except Exception as e:
        console.print(f"[bold red]Failed to update setting:[/] {e}")
        raise typer.Exit(code=1) from e


def run_interactive() -> None:
    """Interactive wizard menu."""
    print_banner()
    service = get_service()
    diag = service.get_diagnostics()

    diag_text = (
        f"Browser: [green]{'READY' if diag['browser_ready'] else 'NOT FOUND'}[/]  •  "
        f"Unpacker: [green]{'READY' if diag['unrar_ready'] else 'NOT FOUND'}[/]  •  "
        f"Disk Space: [green]{diag['storage_free_gb']:.1f} GB Free[/]"
    )
    console.print(f"[dim]{diag_text}[/]\n")

    while True:
        console.print("\n[bold cyan]Actions:[/]")
        console.print("1. [bold white]Paste FitGirl Game URL & Download[/]")
        console.print("2. [bold white]Search Game on FitGirl Repacks[/]")
        console.print("3. [bold white]List Active & Past Download Jobs[/]")
        console.print("4. [bold white]Verify & Extract Downloaded Parts[/]")
        console.print("5. [bold white]System Diagnostics & Settings[/]")
        console.print("6. [bold red]Exit[/]")

        choice = Prompt.ask("\nSelect option (or paste URL directly)", default="1")

        # If user pastes a URL directly
        if choice.startswith("http://") or choice.startswith("https://") or "fitgirl-repacks.site" in choice or "fuckingfast.co" in choice:
            execute_download_pipeline(choice.strip())
            break

        if choice == "1":
            url = Prompt.ask("\nEnter FitGirl Repack URL (e.g. https://fitgirl-repacks.site/...)")
            if url.strip():
                execute_download_pipeline(url.strip())
                break

        elif choice == "2":
            query = Prompt.ask("\nEnter game title to search")
            if query.strip():
                with console.status("[cyan]Searching FitGirl Repacks...[/]"):
                    results = service.search_repacks(query.strip())
                if not results:
                    console.print("[yellow]No results found for that query.[/]")
                else:
                    console.print(render_search_results_table(results))
                    pick = Prompt.ask("Enter number to download (or 'c' to cancel)", default="1")
                    if pick.isdigit() and 1 <= int(pick) <= len(results):
                        execute_download_pipeline(results[int(pick) - 1]["url"])
                        break

        elif choice == "3":
            jobs = service.list_jobs()
            console.print(render_jobs_table(jobs))
            if jobs:
                act = Prompt.ask("Enter Job ID to resume/inspect (or press Enter to return)", default="")
                if act.strip():
                    job_parts = service.get_job_parts(act.strip())
                    console.print(render_parts_table(job_parts, act.strip()))
                    if Confirm.ask("Do you want to resume downloading this job?", default=True):
                        service.resume_job(act.strip())
                        break

        elif choice == "4":
            folder = Prompt.ask("Enter path to directory containing downloaded RAR parts", default=str(service.settings.download_dir))
            p = Path(folder)
            if p.exists():
                is_complete, archive_files, missing = service.verify_archive(p)
                if is_complete and archive_files:
                    console.print(f"[bold green]✔ Archive sequence verified with {len(archive_files)} parts.[/]")
                    if Confirm.ask("Extract this archive now?", default=True):
                        service.extract_archive(p)
                else:
                    console.print(f"[yellow]Archive verification incomplete: missing {missing}[/]")
            else:
                console.print("[red]Directory does not exist.[/]")

        elif choice == "5":
            console.print(render_diagnostics_table(service.get_diagnostics()))
            console.print(render_settings_table(service.settings))

        elif choice == "6":
            console.print("[bold green]Goodbye![/]")
            break


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Default entry point when no subcommand is specified."""
    if ctx.invoked_subcommand is None:
        run_interactive()
