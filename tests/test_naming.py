import pytest

from nexus_downloader.naming import (
    ModIdParseError,
    extract_mod_id,
    match_key,
    numeric_segments,
    strip_extension,
)


@pytest.mark.parametrize(
    "file_name, expected",
    [
        # name-modid-version-timestamp (timestamp is ignored)
        ("SkyUI-12604-6-9-1776525988", 12604),
        ("Fuz Ro D'oh-15109-2-5-1706039953", 15109),
        # 3-digit mod ids are valid and must beat the trailing timestamp
        ("Immersive Citizens - AI Overhaul-173-0-4", 173),
        ("Fair Skin Complexion for CBBE v13.0-798-13-0-1770011213", 798),
        # names containing dots must not be truncated like os.path.splitext would
        ("Footprints 1.6.1-3808-1-6-1-1613434284", 3808),
        # names containing dash-separated version numbers before the mod id:
        # the largest non-timestamp number wins
        ("RaceMenu Anniversary Edition v0-4-20-0-19080-0-4-20-0-1776620918", 19080),
        ("UIExtensions v1-2-0-17561-1-2-0", 17561),
        ("SMIM SE 2-08-659-2-08", 659),
        # a real archive extension is stripped
        ("Some Mod-12345-1-0-1700000000.7z", 12345),
        ("Skyrim Script Extender (SKSE64)-30379-2-2-6-1705522967.1", 30379),
        # no timestamp present
        ("GIST Soul Trap-15755-1-3", 15755),
    ],
)
def test_extract_mod_id(file_name, expected):
    assert extract_mod_id(file_name) == expected


def test_extract_mod_id_no_number():
    for name in ("High Poly Head v1.4 (SE)", "PandoraOutput"):
        with pytest.raises(ModIdParseError):
            extract_mod_id(name)


def test_extract_mod_id_only_timestamp():
    # If the only number is a timestamp, there is no mod id to extract.
    with pytest.raises(ModIdParseError):
        extract_mod_id("Mod-1700000000")


def test_strip_extension_real_extension():
    assert strip_extension("My File-12345-1-0-1700000000.7z") == "My File-12345-1-0-1700000000"
    assert strip_extension("noext-12345") == "noext-12345"


def test_strip_extension_preserves_version_dots():
    # The dot in "1.6.1" is not an extension.
    assert strip_extension("Footprints 1.6.1-3808-1-6-1") == "Footprints 1.6.1-3808-1-6-1"


def test_numeric_segments_ignores_non_numeric():
    assert numeric_segments("Patch-12604-4-2-9b-1656260165") == [
        "12604",
        "4",
        "2",
        "1656260165",
    ]


def test_match_key_ignores_extension_and_case():
    assert match_key("SkyUI-12604-6-9-1776525988.ZIP") == match_key(
        "skyui-12604-6-9-1776525988.7z"
    )
    assert match_key("  Spaced-12345-1-0.zip  ") == "spaced-12345-1-0"
