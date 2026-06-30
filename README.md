# Nexus Bulk Downloader

A small command-line tool that bulk-downloads a list of mod files from
[nexusmods.com](https://www.nexusmods.com) using their public API.

Given a text file of mod **file names**, the tool:

1. Extracts the **mod id** from each file name (the 4th dash-separated number
   from the end).
2. Queries the Nexus API for the list of files belonging to each mod.
3. Matches the requested names against the available files, **ignoring the file
   extension**.
4. Shows you the resolved download plan and asks for **confirmation**.
5. Downloads the matching files **concurrently**, with progress feedback,
   skipping files that are already present and continuing past individual
   errors.

## Requirements

- Python 3.9+
- A Nexus Mods API key — generate one at
  <https://www.nexusmods.com/users/myaccount?tab=api%20access>
- **Nexus Premium** account: generating download links through the API is a
  Premium-only feature. Free accounts receive `403 Forbidden` from the
  `download_link` endpoint unless they pass an `nxm://` `key`/`expires` pair,
  which is not available for unattended bulk downloads.

## Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

This installs the `nexus-bulk-download` command. You can also run it as a
module: `python -m nexus_downloader`.

## Configuration

Create a `config.json` (see `config.example.json`):

```json
{
  "apikey": "YOUR_NEXUS_API_KEY",
  "game_domain": "skyrimspecialedition",
  "download_dir": "downloads",
  "max_concurrent": 4,
  "timeout": 30
}
```

| Key              | Required | Description                                                        |
| ---------------- | -------- | ------------------------------------------------------------------ |
| `apikey`         | yes      | Your personal Nexus Mods API key.                                  |
| `game_domain`    | yes      | The game's domain name, e.g. `skyrimspecialedition`, `fallout4`.   |
| `download_dir`   | no       | Where to save files (relative to the config file). Default `downloads`. |
| `max_concurrent` | no       | Max simultaneous downloads. Default `4`.                           |
| `timeout`        | no       | Per-request timeout in seconds. Default `30`.                      |

> The `game_domain` is the slug in a mod's URL:
> `nexusmods.com/<game_domain>/mods/<id>`.

## The file list

Provide a plain-text `files.txt`, one mod file name per line (see
`files.example.txt`). Blank lines and lines starting with `#` are ignored.

```
Unofficial Skyrim Special Edition Patch-12604-4-2-9b-1656260165.7z
SkyUI-12604-5-2-SE-1518453379.7z
```

### How the mod id is parsed

Nexus download file names end with a series of dash-separated numbers. The mod
id is the **number furthest from the end that is purely numeric and at least 4
digits long**. Scanning segments from the end, shorter version numbers and
non-numeric tokens are skipped, and the trailing timestamp (also numeric) is
passed over in favour of the earlier qualifying number.

For example, in `SkyUI-12604-5-2-SE-1518453379.7z` the purely-numeric segments
of at least 4 digits are `12604` and `1518453379` (the timestamp); the one
furthest from the end is **12604** → mod id `12604`. The minimum digit count is
configurable in code via `extract_mod_id(..., min_digits=...)`.

## Usage

```bash
nexus-bulk-download --config config.json --files files.txt
```

Useful flags:

| Flag                | Description                                              |
| ------------------- | -------------------------------------------------------- |
| `-o, --output DIR`  | Override the download directory.                         |
| `-j, --concurrency` | Override max simultaneous downloads.                     |
| `--dry-run`         | Resolve and print the plan, then exit (no downloads).    |
| `-y, --yes`         | Skip the confirmation prompt.                            |

While the file list is resolved against the API, a progress bar shows
`N of M files processed`. Before any download starts you must **type `Y`** (or
`yes`) to confirm — pressing Enter or anything else aborts. Use `-y/--yes` to
skip the prompt in scripts.

The tool prints a summary of downloaded / skipped / failed files at the end and
exits non-zero if any file failed.

## Behavior notes

- **Duplicate prevention**: each resolved file is downloaded only once, and a
  file already present on disk with the expected size is skipped.
- **Error tolerance**: a failure on one file (network error, missing match,
  API error) does not stop the rest of the batch.
- **Mirrors**: if the API returns multiple CDN mirrors, they are tried in order.

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy nexus_downloader
```
