"""Colour-space conversions: hex, sRGB, linear RGB, XYZ, CIELAB, CIELUV, OKLab and OKLCH.

Numerics and hex rounding follow the original prototype exactly, so ported schemes
reproduce their legacy output byte-for-byte.
"""
from __future__ import annotations

import math
import re

Linear = list[float]
Triple = tuple[float, float, float]

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
D65_U, D65_V = 0.1978, 0.4683  # D65 white point in u'v'


def is_hex(value: object) -> bool:
    """True if ``value`` is a ``#rrggbb`` string."""
    return isinstance(value, str) and bool(HEX_RE.match(value))


def srgb_decode(c: float) -> float:
    """sRGB transfer function, encoded channel → linear."""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def srgb_encode(c: float) -> float:
    """sRGB transfer function, linear channel (clamped to 0..1) → encoded."""
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hex_to_linear(h: str) -> Linear:
    """``#rrggbb`` → linear RGB."""
    h = h.lstrip("#")
    return [srgb_decode(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4)]


def linear_to_hex(lin: Linear) -> str:
    """Linear RGB → lowercase ``#rrggbb`` (clamped, rounded half-to-even like the prototype)."""
    return "#" + "".join(f"{round(255 * srgb_encode(c)):02x}" for c in lin)


def linear_to_xyz(lin: Linear) -> Triple:
    """Linear RGB → CIE XYZ (D65)."""
    r, g, b = lin
    return (0.4124 * r + 0.3576 * g + 0.1805 * b, 0.2126 * r + 0.7152 * g + 0.0722 * b,
            0.0193 * r + 0.1192 * g + 0.9505 * b)


def xyz_to_linear(x: float, y: float, z: float) -> Linear:
    """CIE XYZ (D65) → linear RGB."""
    return [3.2406 * x - 1.5372 * y - 0.4986 * z, -0.9689 * x + 1.8758 * y + 0.0415 * z,
            0.0557 * x - 0.2040 * y + 1.0570 * z]


def _lab_f(t: float) -> float:
    return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116


def linear_to_lab(lin: Linear) -> Triple:
    """Linear RGB (clamped to 0..1) → CIELAB (D65)."""
    x, y, z = linear_to_xyz([min(1, max(0, c)) for c in lin])
    fx, fy, fz = _lab_f(x / 0.95047), _lab_f(y), _lab_f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def lab_to_linear(L: float, a: float, b: float) -> Linear:
    """CIELAB (D65) → linear RGB (unclamped)."""
    fy = (L + 16) / 116
    fx, fz = fy + a / 500, fy - b / 200

    def inv(t: float) -> float:
        return t ** 3 if t ** 3 > 0.008856 else (t - 16 / 116) / 7.787

    return xyz_to_linear(0.95047 * inv(fx), inv(fy), 1.08883 * inv(fz))


def hex_to_lab(h: str) -> Triple:
    """``#rrggbb`` → CIELAB."""
    return linear_to_lab(hex_to_linear(h))


def linear_to_luv(lin: Linear) -> Triple:
    """Linear RGB → CIELUV (D65)."""
    x, y, z = linear_to_xyz(lin)
    d = x + 15 * y + 3 * z
    u, v = (4 * x / d, 9 * y / d) if d > 0 else (D65_U, D65_V)
    L = 116 * _lab_f(y) - 16
    return (L, 13 * L * (u - D65_U), 13 * L * (v - D65_V))


def luv_to_linear(L: float, us: float, vs: float) -> Linear:
    """CIELUV (D65) → linear RGB."""
    u, v = us / (13 * L) + D65_U, vs / (13 * L) + D65_V
    Y = ((L + 16) / 116) ** 3 if L > 8 else L / 903.3
    return xyz_to_linear(Y * 9 * u / (4 * v), Y, Y * (12 - 3 * u - 20 * v) / (4 * v))


def in_gamut(lin: Linear, eps: float = 1e-6) -> bool:
    """True if every linear channel lies within ``[-eps, 1 + eps]``."""
    return all(-eps <= c <= 1 + eps for c in lin)


def linear_to_oklab(lin: Linear) -> Triple:
    """Linear RGB → OKLab."""
    r, g, b = lin
    lms = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
           0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
           0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    L, M, S = (math.copysign(abs(x) ** (1 / 3), x) for x in lms)
    return (0.2104542553 * L + 0.7936177850 * M - 0.0040720468 * S,
            1.9779984951 * L - 2.4285922050 * M + 0.4505937099 * S,
            0.0259040371 * L + 0.7827717662 * M - 0.8086757660 * S)


def oklab_to_linear(L: float, a: float, b: float) -> Linear:
    """OKLab → linear RGB (unclamped)."""
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s]


def oklch_to_hex(L: float, C: float, h: float, gamut_map: bool = True) -> str:
    """OKLCH → hex; with ``gamut_map`` the chroma shrinks by 7 % steps until the colour fits sRGB."""
    hr = math.radians(h)
    for _ in range(40):
        lin = oklab_to_linear(L, C * math.cos(hr), C * math.sin(hr))
        if in_gamut(lin, 1e-4) or not gamut_map:
            return linear_to_hex(lin)
        C *= 0.93
    return linear_to_hex(oklab_to_linear(L, 0, 0))


def hex_to_oklch(h: str) -> Triple:
    """``#rrggbb`` → OKLCH ``(L, C, hue_degrees)``."""
    L, a, b = linear_to_oklab(hex_to_linear(h))
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklch_string(h: str) -> str:
    """CSS-style ``oklch(L C h)`` string for display."""
    L, C, hh = hex_to_oklch(h)
    return f"oklch({L:.3f} {C:.3f} {hh:.1f})"
