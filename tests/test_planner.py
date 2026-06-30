from nexus_downloader.api import ModFile, NexusApiError
from nexus_downloader.planner import build_plan, read_file_list


class FakeClient:
    def __init__(self, files_by_mod, errors=None):
        self._files_by_mod = files_by_mod
        self._errors = errors or {}
        self.calls = []

    def list_mod_files(self, game_domain, mod_id):
        self.calls.append(mod_id)
        if mod_id in self._errors:
            raise NexusApiError(self._errors[mod_id])
        return self._files_by_mod.get(mod_id, [])


def _mf(file_id, file_name, size_kb=10):
    return ModFile(
        file_id=file_id,
        name=file_name,
        file_name=file_name,
        category_name="MAIN",
        version="1.0",
        size_bytes=size_kb * 1024,
    )


def test_read_file_list_skips_blanks_and_comments(tmp_path):
    p = tmp_path / "files.txt"
    p.write_text("# comment\n\nMod A-100-1-2-3.zip\n  Mod B-200-1-2-3.7z  \n")
    assert read_file_list(p) == ["Mod A-100-1-2-3.zip", "Mod B-200-1-2-3.7z"]


def test_build_plan_matches_ignoring_extension():
    client = FakeClient({100: [_mf(1, "Mod A-100-1-2-3.7z")]})
    plan = build_plan(client, "skyrim", ["Mod A-100-1-2-3.zip"])
    assert len(plan.planned) == 1
    assert plan.planned[0].mod_file.file_id == 1
    assert not plan.unresolved


def test_build_plan_groups_api_calls_per_mod():
    client = FakeClient({100: [_mf(1, "A-100-1-2-3.7z"), _mf(2, "B-100-1-2-3.7z")]})
    plan = build_plan(client, "skyrim", ["A-100-1-2-3.7z", "B-100-1-2-3.7z"])
    assert client.calls == [100]
    assert len(plan.planned) == 2


def test_build_plan_dedupes_same_file():
    client = FakeClient({100: [_mf(1, "A-100-1-2-3.7z")]})
    plan = build_plan(client, "skyrim", ["A-100-1-2-3.zip", "A-100-1-2-3.7z"])
    assert len(plan.planned) == 1


def test_build_plan_reports_unmatched():
    client = FakeClient({100: [_mf(1, "A-100-1-2-3.7z")]})
    plan = build_plan(client, "skyrim", ["Missing-100-1-2-3.zip"])
    assert not plan.planned
    assert len(plan.unresolved) == 1


def test_build_plan_handles_unparseable_name():
    client = FakeClient({})
    plan = build_plan(client, "skyrim", ["badname.zip"])
    assert not plan.planned
    assert len(plan.unresolved) == 1
    assert client.calls == []


def test_build_plan_continues_on_api_error():
    client = FakeClient({}, errors={100: "boom"})
    plan = build_plan(client, "skyrim", ["A-100-1-2-3.zip"])
    assert not plan.planned
    assert len(plan.unresolved) == 1
    assert "boom" in plan.unresolved[0].reason
