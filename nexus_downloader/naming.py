"""Helpers for parsing Nexus mod file names.

Nexus download file names end with a series of dash-separated numbers, e.g.::

    Unofficial Skyrim Special Edition Patch-266-4-2-9b-1656260165.7z

The mod id is the *fourth number from the end* (counting only purely-numeric
segments). In the example above the trailing numbers, read from the end, are
``1656260165`` (1st), ``2`` (2nd), ``4`` (3rd), ``266`` (4th) -> mod id ``266``.
The ``9b`` version segment is not purely numeric, so it is not counted.
"""

from __future__ import annotations

import os

MOD_ID_POSITION_FROM_END = 4


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


def numeric_segments(file_name: str) -> list[int]:
    """Return the purely-numeric dash-separated segments of *file_name*."""
    base = strip_extension(file_name)
    return [int(part) for part in base.split("-") if part.isdigit()]


def extract_mod_id(file_name: str, *, position_from_end: int = MOD_ID_POSITION_FROM_END) -> int:
    """Extract the Nexus mod id from a download *file_name*.

    The mod id is the ``position_from_end``-th purely-numeric, dash-separated
    segment counted from the end of the name (default: 4th).

    Raises:
        ModIdParseError: if there are not enough numeric segments.
    """
    numbers = numeric_segments(file_name)
    if len(numbers) < position_from_end:
        raise ModIdParseError(
            f"Cannot extract mod id from {file_name!r}: found {len(numbers)} numeric "
            f"segment(s), need at least {position_from_end}."
        )
    return numbers[-position_from_end]
