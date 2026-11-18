"""Default derived colours shared by every scheme (formulas of the original highlight template).

``raise`` lightens on dark variants and darkens on light ones, so one table serves both.
A scheme's own ``derived`` block may override or extend these names.
"""
from __future__ import annotations

from .expr import ColorValue

DIAGNOSTIC_ROLES = ("error", "warning", "info", "hint", "ok")

DEFAULT_DERIVED: dict[str, ColorValue] = {
    "bg_cursorline": {"raise": ["ui.bg", 0.035]},
    "bg_visual": {"mix": [{"raise": ["ui.bg", 0.10]}, "syntax.type", 0.12]},
    "line_nr": {"mix": ["ui.comment", "ui.bg", 0.35]},
    "nontext": {"mix": ["ui.comment", "ui.bg", 0.4]},
    "border": {"raise": ["ui.bg_alt", 0.08]},
    "bg_search": {"mix": ["ui.bg", "diagnostic.warning", 0.35]},
    "diff_add_bg": {"mix": ["ui.bg", "git.add", 0.22]},
    "diff_delete_bg": {"mix": ["ui.bg", "git.delete", 0.22]},
    "diff_change_bg": {"mix": ["ui.bg", "git.change", 0.12]},
    "diff_text_bg": {"mix": ["ui.bg", "git.change", 0.32]},
    **{f"virtual_{d}_bg": {"mix": ["ui.bg", f"diagnostic.{d}", 0.10]} for d in DIAGNOSTIC_ROLES},
}
