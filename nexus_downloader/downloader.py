"""Concurrent file downloading with progress feedback."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import requests
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .api import NexusApiError, NexusClient
from .planner import PlannedDownload

CHUNK_SIZE = 1 << 16  # 64 KiB


class DownloadStatus(str, Enum):
    DOWNLOADED = "downloaded"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class DownloadResult:
    item: PlannedDownload
    status: DownloadStatus
    detail: str = ""
    path: Path | None = None


def _is_complete(dest: Path, expected_size: int) -> bool:
    """Return True if *dest* already exists and matches the expected size."""
    if not dest.exists():
        return False
    if expected_size <= 0:
        # Size unknown; treat any existing file as complete to avoid re-downloading.
        return True
    return dest.stat().st_size == expected_size


def _download_one(
    client: NexusClient,
    game_domain: str,
    item: PlannedDownload,
    dest_dir: Path,
    progress: Progress,
    timeout: float,
) -> DownloadResult:
    dest = dest_dir / item.mod_file.file_name

    if _is_complete(dest, item.mod_file.size_bytes):
        return DownloadResult(item, DownloadStatus.SKIPPED, "already downloaded", dest)

    try:
        links = client.get_download_links(game_domain, item.mod_id, item.mod_file.file_id)
    except NexusApiError as exc:
        return DownloadResult(item, DownloadStatus.FAILED, str(exc))

    tmp = dest.with_suffix(dest.suffix + ".part")
    last_error = "no download mirrors succeeded"
    for link in links:
        task_id = progress.add_task(
            "download",
            filename=item.mod_file.file_name,
            total=item.mod_file.size_bytes or None,
        )
        try:
            with client._session.get(link.uri, stream=True, timeout=timeout) as response:
                response.raise_for_status()
                total = int(response.headers.get("Content-Length", 0)) or item.mod_file.size_bytes
                progress.update(task_id, total=total or None)
                with open(tmp, "wb") as handle:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if chunk:
                            handle.write(chunk)
                            progress.update(task_id, advance=len(chunk))
            os.replace(tmp, dest)
            progress.remove_task(task_id)
            return DownloadResult(
                item, DownloadStatus.DOWNLOADED, link.short_name or link.name, dest
            )
        except (requests.RequestException, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            progress.remove_task(task_id)
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass
            continue

    return DownloadResult(item, DownloadStatus.FAILED, last_error)


def download_all(
    client: NexusClient,
    game_domain: str,
    items: list[PlannedDownload],
    dest_dir: Path,
    *,
    max_concurrent: int = 4,
    timeout: float = 300.0,
) -> list[DownloadResult]:
    """Download *items* concurrently, tolerating individual failures."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    results: list[DownloadResult] = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[filename]}", justify="left"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        transient=True,
    )

    with progress:
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {
                executor.submit(
                    _download_one, client, game_domain, item, dest_dir, progress, timeout
                ): item
                for item in items
            }
            for future in as_completed(futures):
                item = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001 - keep bulk run alive on any error
                    results.append(
                        DownloadResult(item, DownloadStatus.FAILED, f"unexpected error: {exc}")
                    )

    return results
