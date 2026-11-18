"""Role-coloured lualine modes, with deterministic default-vision separation."""
from __future__ import annotations

from functools import cache
from itertools import combinations
from typing import Sequence

from ..scheme.model import DIAGNOSTIC_ROLES, GIT_ROLES, SYNTAX_ROLES, Scheme
from ..vision.cvd import de_seen
from ..vision.model import DEFAULT
from .base import RenderContext, Target, register
from .neovim import lua_value

MODE_ROLES = {
    "normal": "syntax.function", "insert": "syntax.string", "visual": "syntax.constant",
    "replace": "diagnostic.error", "command": "diagnostic.warning", "terminal": "syntax.type",
}
FALLBACK_ROLES = tuple(f"{group}.{role}" for group, roles in (
    ("syntax", SYNTAX_ROLES), ("diagnostic", DIAGNOSTIC_ROLES), ("git", GIT_ROLES)) for role in roles)


def mode_roles(scheme: Scheme) -> tuple[dict[str, str], float]:
    """Prefer requested roles, then nearest roles; maximise separation if 10 is impossible.

    A derived ``lualine_<mode>`` pins a mode's colour. Search uses fixed mode order,
    nearest-role preference with canonical role order for ties, and cached compatibility
    masks, avoiding factorial permutations of equivalent colour assignments.
    """
    matrix = DEFAULT.matrix
    colors = {role: scheme.resolve(role) for role in FALLBACK_ROLES}
    preferences = []
    for mode, preferred in MODE_ROLES.items():
        override = "lualine_" + mode
        if override in scheme.derived:
            colors[override] = scheme.resolve(override)
            preferences.append([override])
        else:
            preferences.append(sorted(FALLBACK_ROLES, key=lambda role: (
                role != preferred, de_seen(colors[preferred], colors[role], matrix), FALLBACK_ROLES.index(role))))
    unique = list(dict.fromkeys(colors.values()))
    indices = {color: i for i, color in enumerate(unique)}
    distances = [[de_seen(a, b, matrix) for b in unique] for a in unique]
    choices = []
    for roles in preferences:
        # Multiple roles sharing one colour cannot improve separation.
        seen = set()
        choice = []
        for role in roles:
            index = indices[colors[role]]
            if index not in seen:
                choice.append((index, role))
                seen.add(index)
        choices.append(choice)

    def assignment(threshold: float) -> tuple[str, ...] | None:
        neighbors = [sum(1 << j for j, distance in enumerate(row) if distance >= threshold) for row in distances]

        @cache
        def search(mode: int, allowed: int) -> tuple[str, ...] | None:
            if mode == len(choices):
                return ()
            if threshold > 0 and allowed.bit_count() < len(choices) - mode:
                return None
            for index, role in choices[mode]:
                if allowed & (1 << index):
                    rest = search(mode + 1, allowed & neighbors[index])
                    if rest is not None:
                        return (role, *rest)
            return None

        return search(0, (1 << len(unique)) - 1)

    chosen = assignment(10.0)
    if chosen is None:
        thresholds = sorted({0.0, *(d for row in distances for d in row if d < 10.0)})
        low, high = 0, len(thresholds) - 1
        while low < high:
            mid = (low + high + 1) // 2
            if assignment(thresholds[mid]) is not None:
                low = mid
            else:
                high = mid - 1
        chosen = assignment(thresholds[low])
    assert chosen is not None  # threshold zero always permits an assignment, including repeated colours
    minimum = min(distances[indices[colors[a]]][indices[colors[b]]] for a, b in combinations(chosen, 2))
    return dict(zip(MODE_ROLES, chosen)), minimum


@register
class Lualine(Target):
    """Render seven lualine modes, with a/b/c sections and documented role choices."""

    name = "lualine"
    scope = "project"
    description = "Lualine mode themes"

    def render_project(self, schemes: Sequence[Scheme], ctx: RenderContext) -> dict[str, str]:
        out = {}
        for scheme in schemes:
            roles, minimum = mode_roles(scheme)
            if minimum < 10:
                ctx.warn(f"{scheme.id}: lualine mode separation is {minimum:.2f} ΔE00 (target ≥10)")
            r = scheme.resolve
            theme = {
                mode: {"a": {"fg": r("ui.bg"), "bg": r(role), "gui": "bold"},
                       "b": {"fg": r(role), "bg": r("ui.bg_alt")},
                       "c": {"fg": r("ui.fg"), "bg": r("ui.bg")}}
                for mode, role in roles.items()
            }
            theme["inactive"] = {section: {"fg": r("ui.comment"), "bg": r("ui.bg_alt")} for section in "abc"}
            comments = "-- Mode roles: " + ", ".join(f"{mode}={role}" for mode, role in roles.items())
            comments += f"\n-- Minimum mode separation: {minimum:.2f} ΔE00 (default VisionModel).\n"
            out[f"lua/lualine/themes/{scheme.id}.lua"] = ctx.header("--", scheme) + comments + "return " + lua_value(theme) + "\n"
        return out
