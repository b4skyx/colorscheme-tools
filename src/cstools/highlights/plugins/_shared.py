"""Resolve source-defined plugin links as independent, concrete styles."""
from __future__ import annotations

from dataclasses import replace

from ...scheme.model import ResolvedStyle as S, Scheme
from ..groups import CORE_SECTIONS
from . import editor


def linked(scheme: Scheme, links: dict[str, str | S]) -> dict[str, S]:
    """Copy core/plugin link styles, resolving aliases without emitting highlight links."""
    core = {name: style for section in CORE_SECTIONS for name, style in section(scheme).items()}
    core.update(editor.groups(scheme))
    aliases = {
        "Bold": S(bold=True), "Italic": S(italic=True), "Directory": scheme.style("syntax.function"),
        "Underlined": replace(scheme.style("syntax.function"), underline=True),
        "Character": scheme.style("syntax.string"), "SpecialChar": scheme.style("syntax.escape"),
        "SpecialComment": scheme.style("syntax.comment"), "SpecialKey": S(scheme.resolve("nontext")),
        "Method": scheme.style("syntax.function"), "Struct": scheme.style("syntax.type"),
        "Label": scheme.style("syntax.label"), "Question": scheme.style("syntax.string"),
        "ModeMsg": S(scheme.resolve("ui.fg")), "MsgArea": S(scheme.resolve("ui.fg")),
        "Conceal": S(scheme.resolve("ui.comment")), "CursorColumn": S(bg=scheme.resolve("bg_cursorline")),
        "WarningMsg": S(scheme.resolve("diagnostic.warning")), "ErrorMsg": S(scheme.resolve("diagnostic.error")),
        "SpellBad": S(sp=scheme.resolve("diagnostic.error"), undercurl=True),
        "SpellRare": S(sp=scheme.resolve("diagnostic.info"), undercurl=True),
        "SpellLocal": S(sp=scheme.resolve("diagnostic.hint"), undercurl=True),
        "diffAdded": S(scheme.resolve("git.add")), "diffRemoved": S(scheme.resolve("git.delete")),
        "diffChanged": S(scheme.resolve("git.change")), "@macro": scheme.style("syntax.macro"),
        "@markup.link": replace(scheme.style("syntax.function"), underline=True),
        "@markup.quote": scheme.style("syntax.comment"), "KeyWord": scheme.style("syntax.keyword"),
        "DiagnosticOK": S(scheme.resolve("diagnostic.ok")),
    }
    core.update(aliases)

    def resolve(name: str, stack: tuple[str, ...] = ()) -> S:
        if name in stack:
            raise ValueError("plugin highlight link cycle: " + " -> ".join((*stack, name)))
        if name in links:
            value = links[name]
            return replace(value) if isinstance(value, S) else resolve(value, (*stack, name))
        if name in core:
            return replace(core[name])
        if name.startswith(("syntax.", "ui.", "diagnostic.", "git.")):
            return scheme.style(name)
        if name.startswith("@") and "." in name:
            return resolve(name.rsplit(".", 1)[0], stack)
        raise ValueError(f"unknown plugin highlight link {name!r}")

    return {name: resolve(name) for name in links}
