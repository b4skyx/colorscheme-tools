"""Deterministic base-colour names from OKLCH hue buckets.

Colours with chroma below ``GREY_CHROMA`` are ``grey``. When several colours share a bucket they
are sorted by OKLCH lightness and get suffixes from a lightness ladder (``LADDERS``), e.g. four
blues become ``blue_deep``, ``blue_dark``, ``blue_light``, ``blue_pale``. Buckets with more members
than the longest ladder fall back to ``<b>_1`` … ``<b>_n``.
"""
from __future__ import annotations

from typing import Iterable

from ..color.spaces import hex_to_oklch

GREY_CHROMA = 0.035
#: (bucket name, hue start inclusive, hue end exclusive); "rose" wraps around 0°.
HUE_BUCKETS: tuple[tuple[str, float, float], ...] = (
    ("rose", 350, 10), ("red", 10, 35), ("orange", 35, 60), ("amber", 60, 80), ("yellow", 80, 105),
    ("lime", 105, 125), ("green", 125, 155), ("teal", 155, 185), ("cyan", 185, 210), ("sky", 210, 235),
    ("blue", 235, 260), ("indigo", 260, 280), ("violet", 280, 300), ("purple", 300, 320),
    ("magenta", 320, 340), ("pink", 340, 350),
)


#: Suffixes by bucket size, darkest first ("" = the plain bucket name).
LADDERS: dict[int, tuple[str, ...]] = {
    1: ("",),
    2: ("_dark", "_light"),
    3: ("_dark", "", "_light"),
    4: ("_deep", "_dark", "_light", "_pale"),
    5: ("_deep", "_dark", "", "_light", "_pale"),
    6: ("_deep", "_dark", "_dim", "_soft", "_light", "_pale"),
    7: ("_deep", "_dark", "_dim", "", "_soft", "_light", "_pale"),
}


def hue_bucket(hexv: str) -> str:
    """Bucket name of one colour."""
    _, C, h = hex_to_oklch(hexv)
    if C < GREY_CHROMA:
        return "grey"
    for name, lo, hi in HUE_BUCKETS:
        if (lo <= h < hi) if lo < hi else (h >= lo or h < hi):
            return name
    raise AssertionError(f"hue {h} not covered")  # buckets cover 0..360


def name_colors(hexes: Iterable[str]) -> dict[str, str]:
    """Map each distinct (lowercased) hex to a unique bucket-based name, independent of input order."""
    buckets: dict[str, list[str]] = {}
    for h in sorted({h.lower() for h in hexes}):
        buckets.setdefault(hue_bucket(h), []).append(h)
    names: dict[str, str] = {}
    for bucket, members in buckets.items():
        members.sort(key=lambda h: (hex_to_oklch(h)[0], h))
        suffixes = LADDERS.get(len(members)) or tuple(f"_{i}" for i in range(1, len(members) + 1))
        names.update({h: bucket + s for h, s in zip(members, suffixes)})
    return names
