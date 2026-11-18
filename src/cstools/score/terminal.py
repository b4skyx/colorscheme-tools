"""Terminal score: separation of the ANSI accents for a vision model.

Metrics (CIEDE2000 on simulated colours unless noted):
``minN`` worst pair among the six normal accents, ``key`` worst of red/green, red/yellow, green/yellow,
``minB`` same as ``minN`` for brights, ``fgSep`` worst accent-vs-foreground, ``read`` lowest WCAG
contrast of a normal accent on the background, ``fgbg`` foreground/background WCAG contrast.
"""
from __future__ import annotations

import itertools
from typing import Any, Mapping

from ..color.contrast import wcag_contrast
from ..color.spaces import hex_to_lab
from ..scheme.model import Scheme
from ..vision.cvd import IDENTITY, Matrix, de_seen
from ..vision.model import DEFAULT, VisionModel

ACCENTS = (1, 2, 3, 4, 5, 6)
ACCENT_NAMES = {1: "red", 2: "green", 3: "yellow", 4: "blue", 5: "magenta", 6: "cyan"}


def score_palette(pal: Mapping[int, str], background: str, foreground: str, m: Matrix) -> dict[str, Any]:
    """Score a 16-colour palette ``{index: hex}`` with its background and foreground under ``m``."""
    def pairs(idx: list[int] | tuple[int, ...]) -> list[tuple[int, int, float]]:
        return [(a, b, de_seen(pal[a], pal[b], m)) for a, b in itertools.combinations(idx, 2)]

    n, b = pairs(ACCENTS), pairs([i + 8 for i in ACCENTS])
    worst = min(n, key=lambda x: x[2])
    keyp = [x for x in n if {x[0], x[1]} in ({1, 2}, {1, 3}, {2, 3})]
    return {
        "minN": round(worst[2], 1), "worst": f"{ACCENT_NAMES[worst[0]]}/{ACCENT_NAMES[worst[1]]}",
        "key": round(min(x[2] for x in keyp), 1),
        "minB": round(min(x[2] for x in b), 1),
        "fgSep": round(min(de_seen(pal[i], foreground, m) for i in ACCENTS), 1),
        "read": round(min(wcag_contrast(pal[i], background) for i in ACCENTS), 2),
        "fgbg": round(wcag_contrast(foreground, background), 1),
        "bgL": round(hex_to_lab(background)[0], 1),
        "minN_normal_vision": round(min(de_seen(pal[a], pal[c], IDENTITY)
                                        for a, c in itertools.combinations(ACCENTS, 2)), 1),
        "below10": sum(1 for x in n if x[2] < 10),
    }


def rank_value(s: Mapping[str, Any]) -> float:
    """Single ranking number: the worst normal pair dominates, the rest break ties."""
    return 0.5 * s["minN"] + 0.25 * s["key"] + 0.15 * s["minB"] + 0.10 * min(s["fgSep"], 25)


def score_terminal(scheme: Scheme, model: VisionModel = DEFAULT) -> dict[str, Any]:
    """Terminal score of a scheme's 16 ANSI colours under ``model``."""
    pal = {i: scheme.ansi(i) for i in range(16)}
    return score_palette(pal, scheme.terminal_color("background"), scheme.terminal_color("foreground"),
                         model.matrix)
