"""Helpers for parsing Nexus mod file names.

Nexus download file names end with a series of dash-separated numbers, e.g.::

    SkyUI-12604-5-2-SE-1518453379.7z

The mod id is the qualifying number *furthest from the end*: scanning the
dash-separated segments from the end, it is the last segment that is purely
numeric and at least :data:`MOD_ID_MIN_DIGITS` digits long. Equivalently, it is
the first (left-most) such segment. In the example above the segments that are
purely numeric and >= 4 digits are ``12604`` and ``1518453379`` (the trailing
timestamp); the one furthest from the end is ``12604`` -> mod id ``12604``.
Shorter numbers (e.g. version parts ``5``/``2``) and non-numeric tokens (``SE``)
are ignored.
"""

from __future__ import annotations

import os

# Mod ids are at least this many digits; shorter numbers (version parts) are
# ignored when locating the mod id.
MOD_ID_MIN_DIGITS = 4


class ModIdParseError(ValueError):
    """Raised when a mod id cannot be extracted from a file name."""


def strip_extension(file_name: str) -> str:
    """Return *file_name* without its final extension.

    Handles common double extensions such as ``.tar.gz`` is intentionally not
    special-cased; only the last suffix is removed, which matches how Nexus
    archive names (``.zip``/``.7z``/``.rar``) behave.
    """
    return os.path.splitext(file_name)[0]


def match_key(file_name: str) -> str:
    """Return a normalized key used to match requested names to API results.

    Matching ignores the file extension and is case-insensitive, with
    surrounding whitespace removed.
    """
    return strip_extension(file_name).strip().casefold()


def numeric_segments(file_name: str) -> list[str]:
    """Return the purely-numeric dash-separated segments of *file_name*."""
    base = strip_extension(file_name)
    return [part for part in base.split("-") if part.isdigit()]


def extract_mod_id(file_name: str, *, min_digits: int = MOD_ID_MIN_DIGITS) -> int:
    """Extract the Nexus mod id from a download *file_name*.

    Scanning the dash-separated segments from the end, the mod id is the last
    (i.e. left-most) segment that is purely numeric and at least ``min_digits``
    digits long. Trailing timestamps are also purely numeric and long, so the
    *furthest-from-the-end* qualifying segment is chosen rather than the nearest.

    Raises:
        ModIdParseError: if no qualifying numeric segment is found.
    """
    qualifying = [part for part in numeric_segments(file_name) if len(part) >= min_digits]
    if not qualifying:
        raise ModIdParseError(
            f"Cannot extract mod id from {file_name!r}: no purely-numeric, "
            f">= {min_digits}-digit dash-separated segment found."
        )
    return int(qualifying[0])
