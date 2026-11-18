"""Colour operations used by derived-colour expressions. Every result is a rounded hex string."""
from __future__ import annotations

from .spaces import hex_to_linear, hex_to_oklch, linear_to_hex, linear_to_oklab, oklab_to_linear, oklch_to_hex


def mix(h1: str, h2: str, t: float) -> str:
    """Perceptual mix in OKLab; ``t = 0`` gives ``h1``, ``t = 1`` gives ``h2``."""
    a, b = linear_to_oklab(hex_to_linear(h1)), linear_to_oklab(hex_to_linear(h2))
    return linear_to_hex(oklab_to_linear(*[x + (y - x) * t for x, y in zip(a, b)]))


def shift_lightness(h: str, dL: float, dC: float = 0.0) -> str:
    """Shift OKLCH lightness by ``dL`` (and chroma by ``dC``), clamped and gamut-mapped."""
    L, C, hue = hex_to_oklch(h)
    return oklch_to_hex(max(0, min(1, L + dL)), max(0, C + dC), hue)


def lighten(h: str, dL: float) -> str:
    """Raise OKLCH lightness by ``dL``."""
    return shift_lightness(h, dL)


def darken(h: str, dL: float) -> str:
    """Lower OKLCH lightness by ``dL``."""
    return shift_lightness(h, -dL)


def raise_(h: str, dL: float, light: bool) -> str:
    """Move away from the background: lighten on dark variants, darken on light variants."""
    return shift_lightness(h, -dL if light else dL)


def with_chroma(h: str, C: float) -> str:
    """Set OKLCH chroma to ``C`` keeping lightness and hue (gamut-mapped)."""
    L, _, hue = hex_to_oklch(h)
    return oklch_to_hex(L, max(0.0, C), hue)
