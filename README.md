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
SkyUI-12604-6-9-1776525988
Immersive Citizens - AI Overhaul-173-0-4
```

### How the mod id is parsed

Nexus download file names follow `<name>-<modid>-<version>-<timestamp>`. The mod
id is the **largest purely-numeric, dash-separated segment that is not the
trailing upload timestamp** (timestamps are 10-digit unix epochs, i.e. values
`>= 1_000_000_000`, and are ignored).

This handles the tricky cases seen in real lists:

- short version parts (`6`, `9`) and non-numeric tokens (`SE`, `9b`) are ignored;
- 3-digit mod ids work (e.g. `Immersive Citizens - AI Overhaul-173-0-4` → `173`),
  because the timestamp is excluded rather than "first/last N digits" being used;
- names that themselves contain dash-separated version numbers resolve correctly,
  e.g. `RaceMenu Anniversary Edition v0-4-20-0-19080-0-4-20-0-1776620918` →
  largest non-timestamp number `19080`;
- embedded version dots like `Footprints 1.6.1-3808-...` are preserved (the
  extension stripper only removes a genuine short suffix such as `.7z`).

Names with no number at all (e.g. `PandoraOutput`) cannot be resolved and are
reported as unresolved. The timestamp threshold is configurable in code via
`extract_mod_id(..., timestamp_min=...)`.

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
| `--nxm`             | Queue files in a mod manager (Vortex) instead of downloading. |
| `--nxm-action`      | `open` (default), `print`, or `file` — what to do with the links. |
| `--nxm-out PATH`    | Output file for `--nxm-action file` (default `<output>/nxm_links.txt`). |
| `--nxm-delay SECS`  | Delay between opening links in `open` mode (default `1.0`). |

While the file list is resolved against the API, a progress bar shows
`N of M files processed`. Before any download starts you must **type `Y`** (or
`yes`) to confirm — pressing Enter or anything else aborts. Use `-y/--yes` to
skip the prompt in scripts.

The tool prints a summary of downloaded / skipped / failed files at the end and
exits non-zero if any file failed.

### Queue in Vortex instead of downloading (`--nxm`)

With `--nxm`, the tool resolves each requested file to a mod id + file id and
emits an `nxm://<game_domain>/mods/<mod_id>/files/<file_id>` link instead of
downloading it. Vortex registers the `nxm://` protocol handler, so opening these
links queues the downloads into Vortex's own download folder (and it handles the
actual CDN URL itself).

```bash
nexus-bulk-download --nxm                       # open each link -> Vortex queues it
nexus-bulk-download --nxm --nxm-action print    # just print the nxm:// links
nexus-bulk-download --nxm --nxm-action file     # write links to nxm_links.txt
```

Notes:

- Run this on the machine where **Vortex is installed and running**, with the
  `nxm://` handler registered (Settings → Download → "Handle nxm links").
- `open` mode fires the links through your OS handler (`os.startfile` on Windows,
  `open` on macOS, `xdg-open` on Linux); `--nxm-delay` paces them so Vortex keeps
  up.
- Because Vortex uses its own download folder, the "already present on disk"
  filter is not applied in `--nxm` mode (duplicate resolution within a run still
  applies).

## Behavior notes

- **Duplicate prevention**: each resolved file is downloaded only once, and a
  file already present on disk (matched by name) is skipped and not overwritten.
  Already-present files are excluded from the pre-download confirmation report.
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
