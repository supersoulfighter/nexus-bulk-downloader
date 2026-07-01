from nexus_downloader.api import ModFile
from nexus_downloader.nxm import (
    NxmAction,
    NxmStatus,
    build_nxm_uri,
    queue_in_mod_manager,
)
from nexus_downloader.planner import PlannedDownload


def _item(mod_id, file_id, file_name="Some Mod-12345-1-0"):
    mf = ModFile(
        file_id=file_id,
        name=file_name,
        file_name=file_name,
        category_name="MAIN",
        version="1.0",
        size_bytes=1024,
    )
    return PlannedDownload(file_name, mod_id, mf)


def test_build_nxm_uri():
    uri = build_nxm_uri("skyrimspecialedition", _item(12604, 98765))
    assert uri == "nxm://skyrimspecialedition/mods/12604/files/98765"


def test_queue_file_action_writes_links(tmp_path):
    items = [_item(12604, 1), _item(173, 2)]
    out = tmp_path / "links.txt"
    results = queue_in_mod_manager(
        "skyrimspecialedition", items, action=NxmAction.FILE, out_path=out
    )
    assert all(r.status is NxmStatus.QUEUED for r in results)
    assert out.read_text(encoding="utf-8").splitlines() == [
        "nxm://skyrimspecialedition/mods/12604/files/1",
        "nxm://skyrimspecialedition/mods/173/files/2",
    ]


def test_queue_print_action_returns_uris():
    items = [_item(12604, 1)]
    results = queue_in_mod_manager(
        "skyrimspecialedition", items, action=NxmAction.PRINT, delay=0
    )
    assert [r.uri for r in results] == ["nxm://skyrimspecialedition/mods/12604/files/1"]
    assert results[0].status is NxmStatus.QUEUED
