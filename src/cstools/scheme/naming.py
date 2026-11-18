"""Deterministic base-colour names from OKLCH hue buckets.

Colours with chroma below ``GREY_CHROMA`` are ``grey``. When several colours share a bucket they
are sorted by OKLCH lightness: two become ``<b>_dark``/``<b>_light``, three ``<b>_dark``/``<b>``/
``<b>_light``, more ``<b>_1`` … ``<b>_n``.
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
        if len(members) == 1:
            suffixes = [""]
        elif len(members) == 2:
            suffixes = ["_dark", "_light"]
        elif len(members) == 3:
            suffixes = ["_dark", "", "_light"]
        else:
            suffixes = [f"_{i}" for i in range(1, len(members) + 1)]
        names.update({h: bucket + s for h, s in zip(members, suffixes)})
    return names
