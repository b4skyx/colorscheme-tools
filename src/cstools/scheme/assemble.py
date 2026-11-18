"""Assemble a v2 ``Scheme`` from resolved colours (used by migration and the optimiser).

Every distinct hex becomes one palette entry: the five UI base colours keep their role names,
all other colours are named by hue (``naming.py``). Roles reference palette names; secondary
syntax roles reference their primary role (``number`` → ``syntax.constant``). Terminal colours
that equal a palette colour, a default derived colour or a standard terminal formula are stored
as that reference or expression instead of a new hex.
"""
from __future__ import annotations

from typing import Any, Mapping

from .defaults import DEFAULT_DERIVED
from .expr import ColorValue
from .model import ANSI_NAMES, UI_ROLES, Scheme
from .naming import name_colors

ACCENT_KEYS = ("keyword", "function", "string", "type", "constant", "property", "error", "warning", "info", "hint",
               "git_add", "git_change", "git_delete")
STYLE_KEYS = ("comment_italic", "keyword_italic", "parameter_italic")
#: ``raise(<ui role>, dL)`` formulas the terminal generators use for black / bright white,
#: tried after palette names and derived colours.
TERMINAL_FORMULAS: tuple[tuple[str, float], ...] = (("bg_alt", 0.06), ("fg", 0.07), ("fg", 0.08))


def _syntax_roles(n: Mapping[str, str], styles: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    def st(fg: str, **flags: bool) -> dict[str, Any]:
        return {"fg": fg, **{k: True for k, v in flags.items() if v}}

    ci, ki, pi = (bool(styles.get(k, False)) for k in STYLE_KEYS)
    return {
        "variable": st("ui.fg"), "comment": st("ui.comment", italic=ci), "keyword": st(n["keyword"], italic=ki),
        "function": st(n["function"]), "string": st(n["string"]), "type": st(n["type"]),
        "constant": st(n["constant"]), "number": st("syntax.constant"), "boolean": st("syntax.constant"),
        "property": st(n["property"]), "parameter": st("ui.fg", italic=pi),
        "builtin": st("syntax.constant", italic=True), "operator": st("ui.fg_dim"), "punctuation": st("ui.fg_dim"),
        "module": st("syntax.type", italic=True), "attribute": st("syntax.keyword"), "tag": st("syntax.keyword"),
        "escape": st("syntax.constant"), "regex": st("syntax.constant"), "macro": st("syntax.keyword"),
        "constructor": st("syntax.type"), "label": st("syntax.keyword"),
        "todo": {"fg": "ui.bg", "bg": "diagnostic.warning", "bold": True},
        "note": {"fg": "ui.bg", "bg": "diagnostic.info", "bold": True},
    }


def assemble_scheme(meta: Mapping[str, Any], base: Mapping[str, str], accents: Mapping[str, str],
                    styles: Mapping[str, Any], term_normal: Mapping[str, str],
                    term_bright: Mapping[str, str]) -> Scheme:
    """Build a scheme from hex colours.

    ``meta``: id, name, variant and optionally family, description, tags, designed_for, derived.
    ``base``: hex for each of bg, bg_alt, fg, fg_dim, comment. ``accents``: hex for each ``ACCENT_KEYS``.
    ``styles``: comment_italic / keyword_italic / parameter_italic booleans.
    ``term_normal`` / ``term_bright``: hex for each ANSI name (black … white).
    """
    missing = [k for k in UI_ROLES if k not in base] + [k for k in ACCENT_KEYS if k not in accents]
    missing += [f"normal.{k}" for k in ANSI_NAMES if k not in term_normal]
    missing += [f"bright.{k}" for k in ANSI_NAMES if k not in term_bright]
    if missing:
        raise ValueError("assemble_scheme: missing colours: " + ", ".join(missing))

    by_hex: dict[str, str] = {}
    palette: dict[str, str] = {}
    for role in UI_ROLES:
        h = base[role].lower()
        if h not in by_hex:
            by_hex[h] = role
            palette[role] = h
    ui = {role: by_hex[base[role].lower()] for role in UI_ROLES}

    accent_hexes = [h for h in dict.fromkeys(accents[k].lower() for k in ACCENT_KEYS) if h not in by_hex]

    def build(names: Mapping[str, str]) -> Scheme:
        """Scheme with base colours plus accents named by ``names`` (terminal filled in later)."""
        pal = dict(palette) | {names[h]: h for h in accent_hexes}
        lookup = dict(by_hex) | {h: names[h] for h in accent_hexes}
        n = {k: lookup[accents[k].lower()] for k in ACCENT_KEYS}
        roles = {
            "ui": ui,
            "syntax": _syntax_roles(n, styles),
            "diagnostic": {"error": n["error"], "warning": n["warning"], "info": n["info"], "hint": n["hint"],
                           "ok": "git.add"},
            "git": {"add": n["git_add"], "change": n["git_change"], "delete": n["git_delete"]},
        }
        return Scheme(
            id=meta["id"], name=meta["name"], variant=meta["variant"], family=meta.get("family", meta["id"]),
            description=meta.get("description", ""), tags=list(meta.get("tags", [])),
            designed_for=dict(meta.get("designed_for", {})), palette=pal, derived=dict(meta.get("derived", {})),
            roles=roles, terminal={})

    # Resolve candidate expressions with placeholder accent names; only hexes matter here.
    draft = build({h: f"accent_{i}" for i, h in enumerate(accent_hexes)})
    candidates: list[ColorValue] = [name for name in DEFAULT_DERIVED if name not in draft.palette]
    candidates += [name for name in draft.derived if name not in candidates]
    candidates += [{"raise": [ui[role], dL]} for role, dL in TERMINAL_FORMULAS]
    expr_by_hex: dict[str, ColorValue] = {}
    for c in candidates:
        expr_by_hex.setdefault(draft.resolve(c), c)

    term_hexes = [term_normal[k].lower() for k in ANSI_NAMES] + [term_bright[k].lower() for k in ANSI_NAMES]
    known = set(by_hex) | set(accent_hexes) | set(expr_by_hex)
    term_only = [h for h in dict.fromkeys(term_hexes) if h not in known]
    names = name_colors(accent_hexes + term_only)
    scheme = build(names)
    for h in term_only:
        scheme.palette[names[h]] = h
    by_hex.update({h: names[h] for h in accent_hexes + term_only})

    def ref(h: str) -> ColorValue:
        h = h.lower()
        return by_hex[h] if h in by_hex else expr_by_hex[h]

    scheme.terminal = {
        "background": ui["bg"], "foreground": ui["fg"], "cursor": ui["fg"], "cursor_text": ui["bg"],
        "selection_background": "bg_visual", "selection_foreground": ui["fg"],
        "normal": {k: ref(term_normal[k]) for k in ANSI_NAMES},
        "bright": {k: ref(term_bright[k]) for k in ANSI_NAMES},
    }
    return scheme
