"""Configuration loading for the Nexus bulk downloader."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MAX_CONCURRENT = 4
DEFAULT_DOWNLOAD_DIR = "downloads"


class ConfigError(Exception):
    """Raised when the supplied configuration is missing or invalid."""


@dataclass
class Config:
    """Runtime configuration for a bulk download run."""

    api_key: str
    game_domain: str
    download_dir: Path
    max_concurrent: int
    timeout: float

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, base_dir: Path | None = None) -> Config:
        base_dir = base_dir or Path.cwd()

        api_key = _coalesce(data, "apikey", "api_key")
        if not api_key or not str(api_key).strip():
            raise ConfigError("Config is missing a non-empty 'apikey'.")

        game_domain = _coalesce(data, "game_domain", "game", "game_domain_name")
        if not game_domain or not str(game_domain).strip():
            raise ConfigError("Config is missing a non-empty 'game_domain'.")

        download_dir_raw = _coalesce(data, "download_dir", "output_dir") or DEFAULT_DOWNLOAD_DIR
        download_dir = Path(download_dir_raw)
        if not download_dir.is_absolute():
            download_dir = (base_dir / download_dir).resolve()

        max_concurrent = int(
            _coalesce(data, "max_concurrent", "concurrency") or DEFAULT_MAX_CONCURRENT
        )
        if max_concurrent < 1:
            raise ConfigError("'max_concurrent' must be >= 1.")

        timeout = float(data.get("timeout", 30.0))

        return cls(
            api_key=str(api_key).strip(),
            game_domain=str(game_domain).strip(),
            download_dir=download_dir,
            max_concurrent=max_concurrent,
            timeout=timeout,
        )

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> Config:
        config_path = Path(path)
        if not config_path.is_file():
            raise ConfigError(f"Config file not found: {config_path}")
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Config file is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError("Config file must contain a JSON object.")
        return cls.from_dict(data, base_dir=config_path.resolve().parent)


def _coalesce(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None
