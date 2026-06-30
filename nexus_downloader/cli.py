"""Command-line entry point for the Nexus bulk downloader."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn
from rich.prompt import Prompt
from rich.table import Table

from . import __version__
from .api import NexusClient
from .config import Config, ConfigError
from .downloader import DownloadStatus, download_all
from .planner import DownloadPlan, build_plan, read_file_list

console = Console()


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _render_plan(plan: DownloadPlan) -> None:
    if plan.planned:
        table = Table(title="Files to download", show_lines=False, header_style="bold")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Mod ID", justify="right")
        table.add_column("File name")
        table.add_column("Version")
        table.add_column("Size", justify="right")
        for idx, item in enumerate(plan.planned, start=1):
            table.add_row(
                str(idx),
                str(item.mod_id),
                item.mod_file.file_name,
                item.mod_file.version or "-",
                _human_size(item.mod_file.size_bytes) if item.mod_file.size_bytes else "?",
            )
        console.print(table)
        total = sum(i.mod_file.size_bytes for i in plan.planned)
        console.print(f"[bold]{len(plan.planned)}[/bold] file(s), total ~{_human_size(total)}.")
    else:
        console.print("[yellow]No files matched the supplied list.[/yellow]")

    if plan.unresolved:
        count = len(plan.unresolved)
        console.print(f"\n[yellow]{count} entry/entries could not be resolved:[/yellow]")
        for entry in plan.unresolved:
            console.print(f"  [red]![/red] {entry.requested_name} — {entry.reason}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nexus-bulk-download",
        description="Bulk download a list of mod files from nexusmods.com using their API.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        help="Path to JSON config (apikey, game_domain). Default: config.json",
    )
    parser.add_argument(
        "-f",
        "--files",
        default="files.txt",
        help="Path to text file listing mod file names. Default: files.txt",
    )
    parser.add_argument(
        "-o", "--output", default=None, help="Override the download directory from the config."
    )
    parser.add_argument(
        "-j", "--concurrency", type=int, default=None, help="Override max simultaneous downloads."
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt and download immediately.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve and show the plan, then exit without downloading.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _confirm_download() -> bool:
    """Ask the user to explicitly type 'Y' to proceed (anything else aborts)."""
    answer = Prompt.ask("Type 'Y' to confirm and start the download", default="")
    return answer.strip().casefold() in {"y", "yes"}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = Config.load(args.config)
    except ConfigError as exc:
        console.print(f"[red]Config error:[/red] {exc}")
        return 2

    if args.output:
        config.download_dir = Path(args.output).resolve()
    if args.concurrency:
        config.max_concurrent = max(1, args.concurrency)

    files_path = Path(args.files)
    if not files_path.is_file():
        console.print(f"[red]File list not found:[/red] {files_path}")
        return 2

    requested = read_file_list(files_path)
    if not requested:
        console.print("[yellow]The file list is empty — nothing to do.[/yellow]")
        return 0

    console.print(
        f"Resolving [bold]{len(requested)}[/bold] requested file(s) for game "
        f"[bold]{config.game_domain}[/bold]…"
    )

    client = NexusClient(config.api_key, timeout=config.timeout)
    with Progress(
        TextColumn("Processing files"),
        BarColumn(complete_style="green", finished_style="green"),
        MofNCompleteColumn(),
        TextColumn("files processed"),
        console=console,
        transient=True,
    ) as progress:
        task_id = progress.add_task("resolve", total=len(requested))

        def on_progress(done: int, total: int) -> None:
            progress.update(task_id, completed=done, total=total)

        plan = build_plan(
            client, config.game_domain, requested, progress_callback=on_progress
        )
    console.print(f"Processed {len(requested)} of {len(requested)} files.")

    # Filter out files that are already present so the confirmation report only
    # lists what will actually be downloaded.
    dest_dir = config.download_dir
    already_present = [
        p for p in plan.planned if (dest_dir / p.mod_file.file_name).exists()
    ]
    plan.planned = [
        p for p in plan.planned if not (dest_dir / p.mod_file.file_name).exists()
    ]

    _render_plan(plan)
    if already_present:
        console.print(
            f"[yellow]{len(already_present)} file(s) already present in "
            f"{dest_dir} — will be skipped.[/yellow]"
        )

    if not plan.planned:
        console.print("[green]Nothing to download.[/green]")
        return 1 if plan.unresolved else 0

    if args.dry_run:
        console.print("[dim]--dry-run set; exiting without downloading.[/dim]")
        return 0

    console.print(f"\nDownloads will be saved to: [bold]{dest_dir}[/bold]")
    if not args.yes and not _confirm_download():
        console.print("Aborted — confirmation not given.")
        return 0

    results = download_all(
        client,
        config.game_domain,
        plan.planned,
        dest_dir,
        max_concurrent=config.max_concurrent,
        timeout=max(config.timeout, 300.0),
    )

    downloaded = [r for r in results if r.status is DownloadStatus.DOWNLOADED]
    skipped = [r for r in results if r.status is DownloadStatus.SKIPPED]
    failed = [r for r in results if r.status is DownloadStatus.FAILED]

    skipped_present = len(skipped) + len(already_present)

    console.print("\n[bold]Summary[/bold]")
    console.print(f"  [green]Downloaded:[/green] {len(downloaded)}")
    console.print(f"  [yellow]Skipped (already present):[/yellow] {skipped_present}")
    console.print(f"  [red]Failed:[/red] {len(failed)}")
    for result in failed:
        console.print(f"    [red]![/red] {result.item.mod_file.file_name} — {result.detail}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
