"""ANSI optimiser (port of ``legacy/export_schemes.py``), variant-aware.

The six accent slots (red … cyan) and their bright versions start from the scheme colours whose hue is
closest to each slot (red = error and yellow = warning stay semantic) and are searched so that, for the
vision model, the normal accents are clearly apart (cap 18), the bright accents apart (cap 16), red/green/
yellow get extra weight, accents stay apart from the foreground and readable on the background, each
bright colour stays in its normal colour's family, and everything stays near its anchor.
Bright colours are lighter than normal on dark variants and darker on light variants by ≥ 0.03 OKLCH L
(a penalty during the search, then ``repair_bright_step`` for any remaining shortfall).
Black and white come from the UI base colours (``EXTREMES``).
"""
from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass, field
from typing import Mapping

from ..color.contrast import wcag_contrast
from ..color.difference import ciede2000
from ..color.spaces import hex_to_lab, hex_to_oklch, oklch_to_hex
from ..scheme.expr import ColorValue, evaluate
from ..vision.cvd import Matrix, seen_lab
from ..vision.model import DEFAULT, VisionModel
from .editor import softmin
from .recipe import Recipe
from .search import Bounds, Points, search

SLOTS = ("red", "green", "yellow", "blue", "magenta", "cyan")
#: Conventional OKLCH hue of the slots that are matched by hue (red and yellow are semantic).
SLOT_HUES = {"green": 150.0, "blue": 255.0, "magenta": 325.0, "cyan": 200.0}
#: Hue-matching order: earlier slots pick their nearest accent first.
MATCH_ORDER = ("blue", "cyan", "magenta", "green")
#: Accents never used as hue-matched anchors (error/warning are fixed to red/yellow).
NON_ANCHOR_KEYS = ("error", "warning", "property")
HUE_SNAP = 35.0
MIN_ANCHOR_CHROMA = 0.05
BRIGHT_STEP = 0.03
#: Post-search repair of the bright step: OKLCH L increment and maximum total shift.
REPAIR_STEP = 0.001
REPAIR_LIMIT = 0.05
#: Hard lightness clamps of the search on dark variants (legacy constants).
DARK_L_CLAMP = (0.45, 0.93)
#: Light variants clamp to the recipe window widened by these margins (below, above).
LIGHT_L_MARGINS = (0.11, 0.13)

#: Black/white slots as expressions over the UI base colours, per variant (``"<normal|bright>.<name>"``).
EXTREMES: dict[str, dict[str, ColorValue]] = {
    "dark": {"normal.black": {"raise": ["bg_alt", 0.06]}, "normal.white": "fg",
             "bright.black": "comment", "bright.white": {"raise": ["fg", 0.07]}},
    "light": {"normal.black": {"lighten": ["fg", 0.10]}, "normal.white": {"darken": ["bg_alt", 0.06]},
              "bright.black": "comment", "bright.white": "bg_alt"},
}


@dataclass(frozen=True)
class TerminalResult:
    """Optimised accent slots (hex) plus separation metrics."""

    normal: dict[str, str]
    bright: dict[str, str]
    metrics: dict[str, float]
    #: slot → (bright hex before, after) for every slot changed by ``repair_bright_step``.
    repairs: dict[str, tuple[str, str]] = field(default_factory=dict)


def _hue_distance(h1: float, h2: float) -> float:
    return abs((h1 - h2 + 180) % 360 - 180)


def anchors_for(accents: Mapping[str, str]) -> dict[str, str]:
    """Anchor hex per slot: red = error, yellow = warning, others the hue-nearest unused accent
    (rotated onto the slot hue when none is within ``HUE_SNAP`` degrees, chroma at least 0.05)."""
    out = {"red": accents["error"], "yellow": accents["warning"]}
    cands = [k for k in accents if k not in NON_ANCHOR_KEYS]
    used: set[str] = set()
    for slot in MATCH_ORDER:
        k = min((k for k in cands if k not in used),
                key=lambda k: _hue_distance(hex_to_oklch(accents[k])[2], SLOT_HUES[slot]))
        used.add(k)
        L, C, h = hex_to_oklch(accents[k])
        if _hue_distance(h, SLOT_HUES[slot]) > HUE_SNAP:
            h = SLOT_HUES[slot]
        out[slot] = oklch_to_hex(L, max(C, MIN_ANCHOR_CHROMA), h)
    return out


def extremes(recipe: Recipe) -> dict[str, str]:
    """Hex of the black/white slots for the recipe's variant, keyed like ``EXTREMES``."""
    return {k: evaluate(v, recipe.base.__getitem__, recipe.is_light) for k, v in EXTREMES[recipe.variant].items()}


def evaluate_terminal(recipe: Recipe, normal: Mapping[str, str], bright: Mapping[str, str],
                      anchors: Mapping[str, str], m: Matrix) -> tuple[float, dict[str, float]]:
    """Terminal objective (without the per-point prior) and metrics for the six accent slots."""
    t, base, light = recipe.terminal, recipe.base, recipe.is_light
    sn, sb = {k: seen_lab(v, m) for k, v in normal.items()}, {k: seen_lab(v, m) for k, v in bright.items()}
    fg = seen_lab(base["fg"], m)
    dn = [ciede2000(sn[x], sn[y]) for x, y in itertools.combinations(SLOTS, 2)]
    db = [ciede2000(sb[x], sb[y]) for x, y in itertools.combinations(SLOTS, 2)]
    key = [ciede2000(sn[x], sn[y]) for x, y in (("red", "green"), ("red", "yellow"), ("green", "yellow"))]
    cross = [ciede2000(sn[x], sb[y]) for x in SLOTS for y in SLOTS if x != y]
    vsfg = [ciede2000(sn[x], fg) for x in SLOTS] + [ciede2000(sb[x], fg) for x in SLOTS]
    dn_norm = [ciede2000(hex_to_lab(normal[x]), hex_to_lab(normal[y])) for x, y in itertools.combinations(SLOTS, 2)]
    s = (1.0 * min(softmin(dn), 18) + 0.6 * min(softmin(db), 16) + 0.5 * min(min(key), 22)
         + 0.3 * min(softmin(cross), 10) + 0.3 * min(softmin(vsfg), 10) + 0.15 * min(softmin(dn_norm), 15))
    for x in SLOTS:
        Ln, Lb = hex_to_oklch(normal[x])[0], hex_to_oklch(bright[x])[0]
        # bright must be lighter than normal on dark variants, darker on light variants
        s -= 40 * max(0, (Lb + BRIGHT_STEP - Ln) if light else (Ln + BRIGHT_STEP - Lb))
        fam = ciede2000(hex_to_lab(normal[x]), hex_to_lab(bright[x]))
        s -= 0.4 * max(0, 3 - fam) + 0.4 * max(0, fam - 14)
        for col in (normal[x], bright[x]):
            c = wcag_contrast(col, base["bg"])
            if c < t.contrast_min:
                s -= 6 * (t.contrast_min - c)
        s -= 0.05 * ciede2000(hex_to_lab(normal[x]), hex_to_lab(anchors[x]))
    return s, dict(normal_min=min(dn), bright_min=min(db), key_min=min(key), cross_min=min(cross), fg_min=min(vsfg),
                   normal_vision_min=min(dn_norm))


def bright_step(normal: str, bright: str, light: bool) -> float:
    """OKLCH lightness step from the normal to the bright colour (towards the foreground)."""
    step = hex_to_oklch(bright)[0] - hex_to_oklch(normal)[0]
    return -step if light else step


def repair_bright_step(normal: Mapping[str, str], bright: Mapping[str, str], light: bool
                       ) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    """Move each bright colour that is less than ``BRIGHT_STEP`` away from its normal colour further away
    (darker on light variants, lighter on dark) in ``REPAIR_STEP`` increments, at most ``REPAIR_LIMIT``.

    Returns the repaired bright colours and ``{slot: (before, after)}`` for the slots that changed;
    warns when a slot still violates the step at the limit.
    """
    out, repairs = dict(bright), {}
    sign = -1 if light else 1
    for x, b in bright.items():
        if bright_step(normal[x], b, light) >= BRIGHT_STEP:
            continue
        L, C, h = hex_to_oklch(b)
        hx = b
        for i in range(1, round(REPAIR_LIMIT / REPAIR_STEP) + 1):
            hx = oklch_to_hex(L + sign * i * REPAIR_STEP, C, h)
            if bright_step(normal[x], hx, light) >= BRIGHT_STEP:
                break
        else:
            warnings.warn(f"bright {x}: lightness step below {BRIGHT_STEP} after the {REPAIR_LIMIT} repair limit",
                          stacklevel=2)
        out[x] = hx
        repairs[x] = (b, hx)
    return out, repairs


def _split(points: Points) -> tuple[dict[str, str], dict[str, str]]:
    return ({x: oklch_to_hex(*points[x]) for x in SLOTS}, {x: oklch_to_hex(*points["b_" + x]) for x in SLOTS})


def optimize_terminal(recipe: Recipe, accents: Mapping[str, str], model: VisionModel = DEFAULT) -> TerminalResult:
    """Optimise the six normal and six bright accent slots from the editor accents."""
    t, opt, m, light = recipe.terminal, recipe.optimizer, model.matrix, recipe.is_light
    anc = anchors_for(accents)
    anchor_hue = {x: hex_to_oklch(anc[x])[2] for x in SLOTS}
    start: Points = {}
    for x in SLOTS:
        L, C, h = hex_to_oklch(anc[x])
        start[x] = (L, C, h)
        start["b_" + x] = (max(t.lightness_min - 0.04, L - 0.06) if light else min(t.lightness_max + 0.04, L + 0.06),
                           C, h)

    def objective(points: Points, _origin: Points) -> float:
        n, b = _split(points)
        s = evaluate_terminal(recipe, n, b, anc, m)[0]
        for k, (L, C, h) in points.items():
            is_bright = k.startswith("b_")
            slot = k[2:] if is_bright else k
            s -= 0.3 * max(0, _hue_distance(h, anchor_hue[slot]) - (20 if slot == "red" else 35))
            # bright colours may leave the window by 0.05 on their side (above on dark, below on light)
            hi = t.lightness_max + (0.05 if is_bright and not light else 0)
            lo = t.lightness_min - (0.05 if is_bright and light else 0)
            s -= 30 * max(0, L - hi) + 30 * max(0, lo - L)
            cfloor = (0.5 if slot == "cyan" else 0.75) * t.chroma_max  # keep every accent recognisably coloured
            s -= 60 * max(0, cfloor - C)
        return s

    l_lo, l_hi = ((t.lightness_min - LIGHT_L_MARGINS[0], t.lightness_max + LIGHT_L_MARGINS[1]) if light
                  else DARK_L_CLAMP)
    bounds = Bounds(l_lo, l_hi, 0.02, t.chroma_max)
    result = search(start, objective, lambda _k: bounds, opt.terminal_iterations, restarts=1, seed=opt.terminal_seed)
    n, b = _split(result.points)
    b, repairs = repair_bright_step(n, b, light)
    return TerminalResult(n, b, evaluate_terminal(recipe, n, b, anc, m)[1], repairs)
