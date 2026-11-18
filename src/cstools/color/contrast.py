"""Luminance and WCAG contrast."""
from __future__ import annotations

from .spaces import hex_to_linear, linear_to_xyz


def relative_luminance(h: str) -> float:
    """Relative luminance Y of ``#rrggbb`` (0 = black, 1 = white)."""
    return linear_to_xyz(hex_to_linear(h))[1]


def wcag_contrast(h1: str, h2: str) -> float:
    """WCAG 2 contrast ratio between two colours (1..21)."""
    y1, y2 = relative_luminance(h1), relative_luminance(h2)
    hi, lo = max(y1, y2), min(y1, y2)
    return (hi + 0.05) / (lo + 0.05)
