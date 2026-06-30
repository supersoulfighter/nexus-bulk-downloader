from rich.progress import Progress

from nexus_downloader.api import ModFile
from nexus_downloader.downloader import DownloadStatus, _download_one
from nexus_downloader.planner import PlannedDownload


class ExplodingClient:
    """A client whose network methods must never be called."""

    def get_download_links(self, *args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("get_download_links should not be called for an existing file")


def _item():
    mf = ModFile(
        file_id=1,
        name="SkyUI",
        file_name="SkyUI-12604-6-9-1776525988.7z",
        category_name="MAIN",
        version="6.9",
        size_bytes=5 * 1024,
    )
    return PlannedDownload("SkyUI-12604-6-9-1776525988", 12604, mf)


def test_existing_file_is_skipped_without_redownloading(tmp_path):
    item = _item()
    dest = tmp_path / item.mod_file.file_name
    dest.write_bytes(b"original contents")  # size deliberately != reported size

    with Progress() as progress:
        result = _download_one(ExplodingClient(), "skyrim", item, tmp_path, progress, 1.0)

    assert result.status is DownloadStatus.SKIPPED
    # The file on disk is left untouched (not overwritten).
    assert dest.read_bytes() == b"original contents"
