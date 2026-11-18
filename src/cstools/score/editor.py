"""Editor score: how many intended syntax distinctions survive for a vision model.

A pair of roles is *intended* to differ when its normal-vision CIEDE2000 is at least ``INTENT``;
it *survives* when the simulated distance is at least ``OK``.
"""
from __future__ import annotations

import itertools
import math
from typing import Any, Mapping

from ..color.contrast import wcag_contrast
from ..color.spaces import hex_to_lab
from ..highlights.groups import build_groups
from ..scheme.model import ResolvedStyle, Scheme
from ..vision.cvd import IDENTITY, Matrix, de_seen
from ..vision.model import DEFAULT, VisionModel

INTENT, OK = 8.0, 8.0
#: role → highlight groups tried in order (mirrors Neovim's capture fallback)
ROLE_CHAIN: dict[str, list[str]] = {
    "text": ["@variable", "Normal"], "comment": ["@comment", "Comment"], "keyword": ["@keyword", "Keyword", "Statement"],
    "function": ["@function", "Function"], "call": ["@function.call", "@function", "Function"],
    "method": ["@function.method.call", "@function.method", "@function.call", "@function", "Function"],
    "string": ["@string", "String"], "type": ["@type", "Type"], "builtin_type": ["@type.builtin", "@type", "Type"],
    "constant": ["@constant", "Constant"], "number": ["@number", "Number", "Constant"],
    "boolean": ["@boolean", "Boolean", "Constant"],
    "property": ["@variable.member", "@property", "Identifier"],
    "parameter": ["@variable.parameter", "@variable", "Identifier", "Normal"],
    "builtin": ["@variable.builtin", "@constant.builtin", "Special"], "operator": ["@operator", "Operator"],
    "module": ["@module", "Identifier", "Normal"], "constructor": ["@constructor", "@type", "Type"],
    "err": ["DiagnosticError"], "warn": ["DiagnosticWarn"], "info": ["DiagnosticInfo"], "hint": ["DiagnosticHint"],
    "add": ["GitSignsAdd", "Added", "@diff.plus", "DiffAdd"],
    "change": ["GitSignsChange", "Changed", "@diff.delta", "DiffChange"],
    "delete": ["GitSignsDelete", "Removed", "@diff.minus", "DiffDelete"],
}
SYNTAX = ["text", "comment", "keyword", "function", "string", "type", "constant", "number", "property", "parameter",
          "builtin", "operator"]
CORE = ["text", "comment", "keyword", "function", "string", "type", "constant"]

GroupMap = Mapping[str, Mapping[str, Any] | ResolvedStyle]
Pair = tuple[str, str, float, float]


def _get(group: Mapping[str, Any] | ResolvedStyle | None, key: str) -> str | None:
    if group is None:
        return None
    return getattr(group, key) if isinstance(group, ResolvedStyle) else group.get(key)


def roles_of(groups: GroupMap) -> dict[str, str | None]:
    """Resolve the scored roles (plus ``bg``) from highlight groups."""
    r: dict[str, str | None] = {}
    for role, chain in ROLE_CHAIN.items():
        r[role] = next((_get(groups.get(g), "fg") for g in chain if _get(groups.get(g), "fg")), None)
    r["bg"] = _get(groups.get("Normal"), "bg") or "#000000"
    r["text"] = r["text"] or _get(groups.get("Normal"), "fg")
    return r


def _pairs(r: Mapping[str, str | None], keys: list[str], m: Matrix) -> list[Pair]:
    out = []
    for a, b in itertools.combinations(keys, 2):
        if not r.get(a) or not r.get(b):
            continue
        dn, ds = de_seen(r[a], r[b], IDENTITY), de_seen(r[a], r[b], m)
        if dn >= INTENT:
            out.append((a, b, dn, ds))
    return out


def _softmin(ps: list[Pair], T: float = 3.0) -> float:
    return -T * math.log(sum(math.exp(-p[3] / T) for p in ps)) if ps else 0


def score_groups(groups: GroupMap, m: Matrix) -> tuple[dict[str, Any], dict[str, str | None]]:
    """Score highlight groups (``{name: {"fg": hex, ...}}`` or ``ResolvedStyle``) under matrix ``m``."""
    r = roles_of(groups)
    syn, core = _pairs(r, SYNTAX, m), _pairs(r, CORE, m)
    diag, git = _pairs(r, ["err", "warn", "info", "hint"], m), _pairs(r, ["add", "change", "delete"], m)
    lost = [p for p in syn if p[3] < OK]
    s: dict[str, Any] = {
        "syntax_kept": round(1 - len(lost) / max(1, len(syn)), 3), "syntax_pairs": len(syn), "syntax_lost": len(lost),
        "core_min": round(min((p[3] for p in core), default=0), 1),
        "core_worst": min(core, key=lambda p: p[3])[:2] if core else None,
        "core_soft": round(_softmin(core), 1),
        "errwarn": round(de_seen(r["err"], r["warn"], m), 1) if r["err"] and r["warn"] else None,
        "diag_min": round(min((p[3] for p in diag), default=0), 1),
        "git_min": round(min((p[3] for p in git), default=0), 1) if git else None,
        "add_del": round(de_seen(r["add"], r["delete"], m), 1) if r["add"] and r["delete"] else None,
        "fgbg": round(wcag_contrast(r["text"], r["bg"]), 1),
        "comment_contrast": round(wcag_contrast(r["comment"], r["bg"]), 1) if r["comment"] else None,
        "bgL": round(hex_to_lab(r["bg"])[0], 1),
        "lost_pairs": [f"{a}≈{b} ({ds:.1f})" for a, b, dn, ds in sorted(lost, key=lambda p: p[3])][:8],
    }
    s["rank"] = round(0.35 * s["core_soft"] + 15 * s["syntax_kept"] + 0.2 * min(s["errwarn"] or 0, 30)
                      + 0.2 * min(s["add_del"] or 0, 30), 2)
    return s, r


def score_editor(scheme: Scheme, model: VisionModel = DEFAULT) -> dict[str, Any]:
    """Editor score of a scheme's highlight template under ``model``."""
    return score_groups(build_groups(scheme), model.matrix)[0]
