"""Build a download plan from a requested file list."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .api import ModFile, NexusApiError, NexusClient
from .naming import ModIdParseError, extract_mod_id, match_key


@dataclass
class PlannedDownload:
    """A file resolved to a concrete Nexus mod file ready to download."""

    requested_name: str
    mod_id: int
    mod_file: ModFile


@dataclass
class UnresolvedRequest:
    """A requested file that could not be matched to a downloadable file."""

    requested_name: str
    reason: str


@dataclass
class DownloadPlan:
    """The result of resolving a requested file list against the Nexus API."""

    planned: list[PlannedDownload] = field(default_factory=list)
    unresolved: list[UnresolvedRequest] = field(default_factory=list)


def read_file_list(path: str | Path) -> list[str]:
    """Read requested file names from *path*, skipping blanks and ``#`` comments."""
    text = Path(path).read_text(encoding="utf-8")
    names: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        names.append(line)
    return names


def build_plan(client: NexusClient, game_domain: str, requested_names: list[str]) -> DownloadPlan:
    """Resolve *requested_names* into a :class:`DownloadPlan`.

    Files belonging to the same mod are fetched once. Duplicate resolved files
    (same mod id + file id) are collapsed so each file is downloaded only once.
    """
    plan = DownloadPlan()

    # Group requested names by mod id so we hit the API once per mod.
    by_mod: dict[int, list[str]] = {}
    for name in requested_names:
        try:
            mod_id = extract_mod_id(name)
        except ModIdParseError as exc:
            plan.unresolved.append(UnresolvedRequest(name, str(exc)))
            continue
        by_mod.setdefault(mod_id, []).append(name)

    seen_file_ids: set[tuple[int, int]] = set()

    for mod_id, names in by_mod.items():
        try:
            mod_files = client.list_mod_files(game_domain, mod_id)
        except NexusApiError as exc:
            for name in names:
                plan.unresolved.append(
                    UnresolvedRequest(name, f"Failed to list files for mod {mod_id}: {exc}")
                )
            continue

        lookup: dict[str, ModFile] = {}
        for mod_file in mod_files:
            lookup.setdefault(match_key(mod_file.file_name), mod_file)

        for name in names:
            matched = lookup.get(match_key(name))
            if matched is None:
                plan.unresolved.append(
                    UnresolvedRequest(name, f"No matching file found in mod {mod_id}.")
                )
                continue
            dedupe_key = (mod_id, matched.file_id)
            if dedupe_key in seen_file_ids:
                continue
            seen_file_ids.add(dedupe_key)
            plan.planned.append(PlannedDownload(name, mod_id, matched))

    return plan
