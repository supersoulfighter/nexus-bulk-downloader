"""Hand resolved downloads off to a mod manager (e.g. Vortex) as ``nxm://`` URIs.

Instead of downloading files directly (which needs a Nexus Premium account for
the ``download_link`` endpoint), this builds ``nxm://`` links and dispatches them
to the OS protocol handler. Vortex registers that handler, so each link is queued
into Vortex's own download folder.

An ``nxm://`` link only needs the game domain, mod id, and file id::

    nxm://skyrimspecialedition/mods/12604/files/123456

so this mode does not call the Premium-only download endpoint. Vortex resolves
the actual CDN URL itself using the signed-in account.
"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .planner import PlannedDownload


class NxmAction(str, Enum):
    """What to do with the generated ``nxm://`` links."""

    OPEN = "open"  # hand each link to the OS handler (launches/queues Vortex)
    PRINT = "print"  # write the links to stdout
    FILE = "file"  # write the links to a text file


class NxmStatus(str, Enum):
    QUEUED = "queued"
    FAILED = "failed"


@dataclass
class NxmResult:
    item: PlannedDownload
    uri: str
    status: NxmStatus
    detail: str = ""


def build_nxm_uri(game_domain: str, item: PlannedDownload) -> str:
    """Return the ``nxm://`` URI for a resolved download."""
    return f"nxm://{game_domain}/mods/{item.mod_id}/files/{item.mod_file.file_id}"


def _open_uri(uri: str) -> None:
    """Launch *uri* via the platform's protocol handler (raises on failure)."""
    if sys.platform.startswith("win"):
        # os.startfile is the reliable way to trigger a protocol handler on Windows.
        import os

        os.startfile(uri)  # type: ignore[attr-defined]  # noqa: S606 - Windows only
    elif sys.platform == "darwin":
        subprocess.run(["open", uri], check=True)
    else:
        subprocess.run(["xdg-open", uri], check=True)


def queue_in_mod_manager(
    game_domain: str,
    items: list[PlannedDownload],
    *,
    action: NxmAction = NxmAction.OPEN,
    out_path: Path | None = None,
    delay: float = 1.0,
) -> list[NxmResult]:
    """Dispatch ``nxm://`` links for *items* according to *action*.

    * ``OPEN``  - hand each link to the OS handler so Vortex queues it, pausing
      *delay* seconds between links so the manager can keep up.
    * ``PRINT`` - return results only (the caller prints the URIs).
    * ``FILE``  - append every link to *out_path* (one per line).
    """
    results: list[NxmResult] = []

    file_handle = None
    if action is NxmAction.FILE:
        if out_path is None:
            raise ValueError("out_path is required for NxmAction.FILE")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        file_handle = out_path.open("w", encoding="utf-8")

    try:
        for index, item in enumerate(items):
            uri = build_nxm_uri(game_domain, item)
            try:
                if action is NxmAction.OPEN:
                    _open_uri(uri)
                    if delay > 0 and index < len(items) - 1:
                        time.sleep(delay)
                elif action is NxmAction.FILE:
                    assert file_handle is not None
                    file_handle.write(uri + "\n")
                results.append(NxmResult(item, uri, NxmStatus.QUEUED))
            except (OSError, subprocess.SubprocessError) as exc:
                results.append(
                    NxmResult(item, uri, NxmStatus.FAILED, f"{type(exc).__name__}: {exc}")
                )
    finally:
        if file_handle is not None:
            file_handle.close()

    return results
