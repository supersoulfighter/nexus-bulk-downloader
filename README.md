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
Unofficial Skyrim Special Edition Patch-266-4-2-9b-1656260165.7z
SkyUI-12604-5-2-SE-1518453379.7z
```

### How the mod id is parsed

Nexus download file names end with a series of dash-separated numbers. The mod
id is the **4th number from the end**, counting only purely-numeric segments.
For example, in `...-266-4-2-9b-1656260165.7z` the numbers from the end are
`1656260165` (1st), `2` (2nd), `4` (3rd), `266` (4th) → mod id **266**
(`9b` is skipped because it is not purely numeric).

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
