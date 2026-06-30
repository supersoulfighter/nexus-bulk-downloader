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
        # name-modid-major-minor-<non-numeric version>-timestamp
        ("Unofficial Skyrim Special Edition Patch-266-4-2-9b-1656260165.7z", 266),
        # all-numeric trailing segments: timestamp, patch, minor, major(=4th)->modid? No:
        # numbers from end: 1612345678,3,2,1,12345 -> 4th from end = 1 ... documented behavior
        ("Some Mod-12345-1-2-3-1612345678.zip", 1),
        # realistic two-part version: name-modid-major-minor-timestamp
        ("Cool Mod-98765-1-0-1700000000.rar", 98765),
    ],
)
def test_extract_mod_id(file_name, expected):
    assert extract_mod_id(file_name) == expected


def test_extract_mod_id_custom_position():
    # The 1st number from end is always the timestamp-like trailing number.
    assert extract_mod_id("Cool Mod-98765-1-0-1700000000.rar", position_from_end=1) == 1700000000


def test_extract_mod_id_insufficient_numbers():
    with pytest.raises(ModIdParseError):
        extract_mod_id("OnlyName-1-2.zip")


def test_numeric_segments_ignores_non_numeric():
    assert numeric_segments("Patch-266-4-2-9b-1656260165.7z") == [266, 4, 2, 1656260165]


def test_strip_extension():
    assert strip_extension("My File-1-2-3-4.7z") == "My File-1-2-3-4"
    assert strip_extension("noext") == "noext"


def test_match_key_ignores_extension_and_case():
    assert match_key("MyMod-1-2-3-4.ZIP") == match_key("mymod-1-2-3-4.7z")
    assert match_key("  Spaced-1-2-3-4.zip  ") == "spaced-1-2-3-4"
