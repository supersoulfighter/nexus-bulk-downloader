"""Helpers for parsing Nexus mod file names.

Nexus download file names follow ``<name>-<modid>-<version>-<timestamp>`` where
``<version>`` is dotted-version-with-dashes and ``<timestamp>`` is the upload
unix epoch, e.g.::

    SkyUI-12604-6-9-1776525988

The mod id is recovered as the **largest purely-numeric, dash-separated segment
that is not the trailing upload timestamp**. This is robust against:

* short version parts (``6``, ``9``) and non-numeric tokens (``SE``, ``9b``),
* the trailing timestamp (always >= :data:`TIMESTAMP_MIN`, i.e. a 10-digit
  epoch, which is larger than any real mod id and is excluded), and
* names that themselves contain dash-separated version numbers, e.g.
  ``RaceMenu Anniversary Edition v0-4-20-0-19080-0-4-20-0-1776620918`` -> the
  numbers are ``4,20,0,19080,0,4,20,0`` (timestamp removed) and the largest,
  ``19080``, is the mod id.

Note: a handful of names carry no number at all (e.g. ``PandoraOutput``); those
raise :class:`ModIdParseError` and are reported as unresolved by the caller.
"""

from __future__ import annotations

import re

# Numbers >= this value are treated as upload timestamps (10-digit unix epochs)
# rather than mod ids, and are ignored when locating the mod id.
TIMESTAMP_MIN = 1_000_000_000

# A trailing ".<ext>" is only treated as a file extension when it is a short
# alphanumeric token with no dashes/spaces (e.g. ".7z", ".zip", ".1"). This
# avoids mangling names that contain dots such as "Footprints 1.6.1-3808-...".
_EXT_RE = re.compile(r"[A-Za-z0-9]{1,4}")


class ModIdParseError(ValueError):
    """Raised when a mod id cannot be extracted from a file name."""


def strip_extension(file_name: str) -> str:
    """Return *file_name* without a genuine trailing file extension.

    Unlike :func:`os.path.splitext`, this does not strip everything after the
    last dot; it only removes a short alphanumeric suffix, so embedded version
    dots (``v13.0``, ``1.6.1``) are preserved.
    """
    head, dot, ext = file_name.rpartition(".")
    if dot and head and _EXT_RE.fullmatch(ext):
        return head
    return file_name


def match_key(file_name: str) -> str:
    """Return a normalized key used to match requested names to API results.

    Matching ignores the file extension and is case-insensitive, with
    surrounding whitespace removed.
    """
    return strip_extension(file_name.strip()).casefold()


def numeric_segments(file_name: str) -> list[str]:
    """Return the purely-numeric dash-separated segments of *file_name*."""
    base = strip_extension(file_name)
    return [part for part in base.split("-") if part.isdigit()]


def extract_mod_id(file_name: str, *, timestamp_min: int = TIMESTAMP_MIN) -> int:
    """Extract the Nexus mod id from a download *file_name*.

    The mod id is the largest purely-numeric, dash-separated segment whose value
    is below ``timestamp_min`` (so the trailing upload timestamp is ignored).

    Raises:
        ModIdParseError: if the name has no qualifying numeric segment.
    """
    candidates = [int(part) for part in numeric_segments(file_name)]
    non_timestamp = [value for value in candidates if value < timestamp_min]
    if not non_timestamp:
        raise ModIdParseError(
            f"Cannot extract mod id from {file_name!r}: no non-timestamp, "
            "purely-numeric dash-separated segment found."
        )
    return max(non_timestamp)
