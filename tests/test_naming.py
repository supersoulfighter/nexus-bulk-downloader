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
        # name-modid-major-minor-<non-numeric version>-timestamp; modid is the
        # furthest-from-the-end purely-numeric, >=4-digit segment (not the timestamp).
        ("Unofficial Skyrim Special Edition Patch-12604-4-2-9b-1656260165.7z", 12604),
        # name-modid-major-minor-<SE>-timestamp
        ("SkyUI-12604-5-2-SE-1518453379.7z", 12604),
        # name-modid-major-minor-patch-timestamp (all numeric tail)
        ("Some Mod-345678-1-2-3-1612345678.zip", 345678),
        # two-part version: name-modid-major-minor-timestamp
        ("Cool Mod-98765-1-0-1700000000.rar", 98765),
        # short version numbers (<4 digits) are ignored
        ("Mod-1000-1-2-1700000000.7z", 1000),
    ],
)
def test_extract_mod_id(file_name, expected):
    assert extract_mod_id(file_name) == expected


def test_extract_mod_id_only_timestamp_when_id_too_short():
    # If the only >=4-digit number is the trailing timestamp, it is returned.
    assert extract_mod_id("Mod-266-4-2-1700000000.7z") == 1700000000


def test_extract_mod_id_custom_min_digits():
    # Lowering min_digits lets a 3-digit mod id be picked (furthest from the end).
    assert extract_mod_id("Mod-266-4-2-1700000000.7z", min_digits=3) == 266


def test_extract_mod_id_no_qualifying_number():
    with pytest.raises(ModIdParseError):
        extract_mod_id("OnlyName-1-2-3.zip")


def test_numeric_segments_ignores_non_numeric():
    assert numeric_segments("Patch-12604-4-2-9b-1656260165.7z") == [
        "12604",
        "4",
        "2",
        "1656260165",
    ]


def test_strip_extension():
    assert strip_extension("My File-1-2-3-4.7z") == "My File-1-2-3-4"
    assert strip_extension("noext") == "noext"


def test_match_key_ignores_extension_and_case():
    assert match_key("MyMod-1-2-3-4.ZIP") == match_key("mymod-1-2-3-4.7z")
    assert match_key("  Spaced-1-2-3-4.zip  ") == "spaced-1-2-3-4"
