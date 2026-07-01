"""Thin client for the Nexus Mods public API (https://api.nexusmods.com)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from . import __version__

API_BASE = "https://api.nexusmods.com/v1"
USER_AGENT = f"nexus-bulk-downloader/{__version__}"


class NexusApiError(Exception):
    """Raised when the Nexus API returns an error or unexpected payload."""


@dataclass(frozen=True)
class ModFile:
    """A single downloadable file belonging to a mod."""

    file_id: int
    name: str
    file_name: str
    category_name: str | None
    version: str | None
    size_bytes: int

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> ModFile:
        # The API reports size in kilobytes via several historical keys.
        size_kb = data.get("size_kb")
        if size_kb is None:
            size_kb = data.get("size", 0)
        return cls(
            file_id=int(data["file_id"]),
            name=str(data.get("name", "")),
            file_name=str(data.get("file_name", "")),
            category_name=data.get("category_name"),
            version=data.get("version"),
            size_bytes=int(size_kb or 0) * 1024,
        )


@dataclass(frozen=True)
class DownloadLink:
    """A CDN mirror URL for a file."""

    name: str
    short_name: str
    uri: str


class NexusClient:
    """Minimal Nexus Mods API client with basic rate-limit handling."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30.0,
        session: requests.Session | None = None,
        max_retries: int = 3,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "apikey": api_key,
                "accept": "application/json",
                "User-Agent": USER_AGENT,
            }
        )

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        url = f"{API_BASE}{path}"
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                response = self._session.get(url, params=params, timeout=self._timeout)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(min(2 ** attempt, 10))
                continue

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 2 ** attempt))
                time.sleep(min(retry_after, 30))
                continue
            if response.status_code == 401:
                raise NexusApiError("Nexus API rejected the API key (401 Unauthorized).")
            if response.status_code == 403:
                raise NexusApiError(
                    "Nexus API returned 403 Forbidden. Generating download links via the API "
                    "requires a Nexus Premium account (or an nxm key/expires pair)."
                )
            if response.status_code == 404:
                raise NexusApiError(f"Nexus API resource not found (404): {url}")
            if response.status_code >= 500:
                last_exc = NexusApiError(f"Nexus API server error {response.status_code}.")
                time.sleep(min(2 ** attempt, 10))
                continue

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise NexusApiError(f"Nexus API error {response.status_code}: {exc}") from exc

            try:
                return response.json()
            except ValueError as exc:
                raise NexusApiError(f"Nexus API returned non-JSON response from {url}.") from exc

        raise NexusApiError(
            f"Nexus API request failed after {self._max_retries} attempts: {last_exc}"
        )

    def list_mod_files(self, game_domain: str, mod_id: int) -> list[ModFile]:
        """Return the files available for a mod."""
        payload = self._get(f"/games/{game_domain}/mods/{mod_id}/files.json")
        files = payload.get("files", []) if isinstance(payload, dict) else []
        return [ModFile.from_api(item) for item in files]

    def get_download_links(self, game_domain: str, mod_id: int, file_id: int) -> list[DownloadLink]:
        """Return CDN download links for a file (requires Premium for free generation)."""
        payload = self._get(
            f"/games/{game_domain}/mods/{mod_id}/files/{file_id}/download_link.json"
        )
        if not isinstance(payload, list):
            raise NexusApiError("Unexpected download_link payload (expected a list of mirrors).")
        links = [
            DownloadLink(
                name=str(item.get("name", "")),
                short_name=str(item.get("short_name", "")),
                uri=str(item["URI"]),
            )
            for item in payload
            if item.get("URI")
        ]
        if not links:
            raise NexusApiError("Nexus API returned no download URLs for this file.")
        return links
