"""Editor-role optimiser (port of the original prototype's ``evaluate`` + ``optimise``).

The accent roles move in OKLCH so that syntax, diagnostic and git roles stay apart for the vision model
(CIEDE2000 on simulated colours), with capped rewards, a contrast floor against the background, and a
prior that keeps every accent near its anchor (hue tolerance, lightness window, chroma floor, look).
Dark and light recipes use the same objective; only the recipe's limits differ.
"""
from __future__ import annotations

import itertools
import math
from typing import Mapping

from ..color.contrast import wcag_contrast
from ..color.difference import ciede2000
from ..color.spaces import hex_to_lab, hex_to_oklch, oklch_to_hex
from ..vision.cvd import Matrix, seen_lab
from ..vision.model import DEFAULT, VisionModel
from .recipe import Recipe
from .search import Bounds, Points, search

CORE = ("text", "comment", "keyword", "function", "string", "type", "constant")
DIAGNOSTICS = ("error", "warning", "info", "hint")
GIT = ("git_add", "git_change", "git_delete")


def softmin(ds: list[float], T: float = 2.5) -> float:
    """Smooth minimum of distances (temperature ``T``)."""
    return -T * math.log(sum(math.exp(-d / T) for d in ds))


def _pairs(lab: Mapping[str, tuple[float, float, float]], keys: tuple[str, ...]) -> list[float]:
    return [ciede2000(lab[a], lab[b]) for a, b in itertools.combinations(keys, 2)]


def evaluate_editor(recipe: Recipe, accents: Mapping[str, str], m: Matrix) -> tuple[float, dict[str, float]]:
    """Objective value and separation metrics for accent hexes keyed by ``ACCENT_KEYS``."""
    fg, comment = recipe.base["fg"], recipe.base["comment"]
    sv = {k: seen_lab(v, m) for k, v in accents.items()}
    sv["text"], sv["comment"] = seen_lab(fg, m), seen_lab(comment, m)
    d_core, d_diag, d_git = _pairs(sv, CORE), _pairs(sv, DIAGNOSTICS), _pairs(sv, GIT)
    ew = ciede2000(sv["error"], sv["warning"])
    prop = ciede2000(sv["property"], sv["text"])
    nv = {k: hex_to_lab(v) for k, v in accents.items()}
    nv["text"], nv["comment"] = hex_to_lab(fg), hex_to_lab(comment)
    d_norm = _pairs(nv, CORE)
    # capped rewards: once a pair is clearly distinct, more distance buys nothing
    score = (1.0 * min(softmin(d_core), 16) + 0.3 * min(softmin(d_diag), 20) + 0.5 * min(ew, 25)
             + 0.4 * min(softmin(d_git), 25) + 0.2 * min(prop, 8) + 0.15 * min(softmin(d_norm), 15))
    cmin = recipe.editor.contrast_min
    for v in accents.values():
        c = wcag_contrast(v, recipe.base["bg"])
        if c < cmin:
            score -= 6 * (cmin - c)
    return score, dict(core_min=min(d_core), core_soft=softmin(d_core), errwarn=ew, git_min=min(d_git),
                       diag_min=min(d_diag), prop=prop, normal_core_min=min(d_norm))


def _hexes(points: Points) -> dict[str, str]:
    return {k: oklch_to_hex(*p) for k, p in points.items()}


def optimize_editor(recipe: Recipe, model: VisionModel = DEFAULT) -> dict[str, str]:
    """Optimised accent hexes keyed by ``ACCENT_KEYS``, using the recipe's seed, iterations and restarts."""
    ed, opt, m = recipe.editor, recipe.optimizer, model.matrix
    anchors = {k: hex_to_oklch(v) for k, v in ed.anchors.items()}
    anchor_lab = {k: hex_to_lab(v) for k, v in ed.anchors.items()}

    def prior(points: Points, origin: Points) -> float:
        pen = 0.0
        for k, (L, C, h) in points.items():
            dh = abs((h - origin[k][2] + 180) % 360 - 180)
            pen += 0.3 * max(0, dh - ed.hue_tolerance)
            pen += 30 * max(0, L - ed.lightness_max) + 30 * max(0, ed.lightness_min - L)
            pen += 40 * max(0, max(0.03, 0.6 * origin[k][1]) - C)
            # stay close to the recipe's look (normal-vision distance from the anchor colour)
            pen += 0.05 * ciede2000(hex_to_lab(oklch_to_hex(L, C, h)), anchor_lab[k])
        return pen

    def objective(points: Points, origin: Points) -> float:
        return evaluate_editor(recipe, _hexes(points), m)[0] - prior(points, origin)

    bounds = Bounds(ed.lightness_min - 0.08, ed.lightness_max + 0.05, 0.01, ed.chroma_max)
    result = search(anchors, objective, lambda _k: bounds, opt.iterations, opt.restarts, opt.seed)
    return _hexes(result.points)
