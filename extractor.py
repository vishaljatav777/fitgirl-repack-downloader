import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple
from rich.console import Console
from config import get_unrar_path

console = Console()

class ArchiveVerifierExtractor:
    def __init__(self, download_dir: Path, extract_dir: Path):
        self.download_dir = Path(download_dir)
        self.extract_dir = Path(extract_dir)
        self.unrar_path = get_unrar_path()

    def verify_parts(self) -> Tuple[bool, List[Path], List[int]]:
        """
        Scans download_dir for multipart RAR files.
        Returns (is_complete, sorted_part_files, missing_part_numbers).
        """
        rar_files = list(self.download_dir.glob("*.rar"))
        if not rar_files:
            return False, [], []

        # Group by part numbers
        part_map = {}
        for f in rar_files:
            # Match .partXX.rar or .partX.rar
            m = re.search(r"\.part(\d+)\.rar$", f.name, re.IGNORECASE)
            if m:
                part_num = int(m.group(1))
                part_map[part_num] = f

        if not part_map:
            # Single RAR file or other naming
            return True, rar_files, []

        max_part = max(part_map.keys())
        missing_parts = []
        sorted_files = []

        for i in range(1, max_part + 1):
            if i in part_map:
                f = part_map[i]
                # Check for 0-byte files
                if f.stat().st_size == 0:
                    missing_parts.append(i)
                else:
                    sorted_files.append(f)
            else:
                missing_parts.append(i)

        is_complete = len(missing_parts) == 0
        return is_complete, sorted_files, missing_parts

    def extract(self) -> bool:
        """Extracts the verified archive to extract_dir."""
        is_complete, part_files, missing = self.verify_parts()

        if not part_files:
            console.print("[bold red]No RAR files found to extract in:[/] " + str(self.download_dir))
            return False

        if not is_complete:
            console.print(f"[bold red]Cannot extract! Missing or incomplete parts: {missing}[/]")
            return False

        if not self.unrar_path:
            console.print("[bold yellow]Neither WinRAR (UnRAR.exe) nor 7-Zip (7z.exe) was found on your system.[/]")
            console.print(f"Please extract [cyan]{part_files[0].name}[/] manually using your preferred archiver.")
            return False

        first_part = part_files[0]
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        console.print(f"\n[bold green]Extracting archive:[/] [cyan]{first_part.name}[/]")
        console.print(f"[bold green]Destination folder:[/] [cyan]{self.extract_dir}[/]")
        console.print(f"[bold green]Unpacker tool:[/] [dim]{self.unrar_path}[/]\n")

        # Build unpack command
        if "7z" in self.unrar_path.lower():
            cmd = [
                self.unrar_path,
                "x",
                "-y",
                f"-o{str(self.extract_dir)}",
                str(first_part)
            ]
        else:
            # WinRAR / UnRAR.exe
            cmd = [
                self.unrar_path,
                "x",
                "-o+",
                "-y",
                str(first_part),
                f"{str(self.extract_dir)}\\"
            ]

        try:
            with console.status("[bold cyan]Extracting multi-part game archive... Please wait.[/]"):
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

            if result.returncode == 0:
                console.print("\n[bold green]✔ Extraction completed successfully![/]")
                # Search for setup.exe or main executable
                setups = list(self.extract_dir.glob("setup*.exe")) + list(self.extract_dir.glob("*.exe"))
                if setups:
                    console.print(f"[bold cyan]Installer found:[/] [bold yellow]{setups[0]}[/]")
                return True
            else:
                console.print(f"[bold red]Extraction failed (code {result.returncode}):[/]\n{result.stderr}")
                return False
        except Exception as e:
            console.print(f"[bold red]Failed to execute unpacker:[/] {e}")
            return False
