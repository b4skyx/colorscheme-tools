"""TextMate theme shared by bat and yazi."""
from __future__ import annotations

import plistlib

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

# TextMate scopes ordered from general to more specific matches.
SCOPES: tuple[tuple[str, str], ...] = (
    ("comment", "syntax.comment"), ("string", "syntax.string"),
    ("constant.numeric", "syntax.number"), ("constant.language", "syntax.boolean"),
    ("constant.character.escape", "syntax.escape"), ("constant.other", "syntax.constant"),
    ("keyword", "syntax.keyword"), ("keyword.operator", "syntax.operator"),
    ("storage", "syntax.keyword"), ("storage.type", "syntax.type"),
    ("entity.name.function", "syntax.function"), ("support.function", "syntax.builtin"),
    ("meta.function-call", "syntax.function"), ("entity.name.type", "syntax.type"),
    ("entity.name.class", "syntax.type"), ("support.type", "syntax.type"),
    ("support.class", "syntax.type"), ("variable", "syntax.variable"),
    ("variable.parameter", "syntax.parameter"), ("variable.language", "syntax.builtin"),
    ("variable.other.member", "syntax.property"), ("entity.name.tag", "syntax.tag"),
    ("entity.other.attribute-name", "syntax.attribute"), ("entity.name.namespace", "syntax.module"),
    ("punctuation", "syntax.punctuation"), ("markup.heading", "syntax.function"),
    ("markup.bold", "ui.fg"), ("markup.italic", "ui.fg"),
    ("markup.inserted", "git.add"), ("markup.deleted", "git.delete"),
    ("markup.changed", "git.change"), ("meta.diff.header", "syntax.function"),
    ("invalid", "diagnostic.error"),
)


def render_tmtheme(scheme: Scheme) -> str:
    """Return a deterministic XML plist with role colours and TextMate font styles."""
    r = scheme.resolve
    settings: list[dict[str, object]] = [{"settings": {
        "background": r("ui.bg"), "foreground": r("ui.fg"), "caret": scheme.terminal_color("cursor"),
        "lineHighlight": r("bg_cursorline"), "selection": r("bg_visual"),
        "gutterForeground": r("line_nr"), "invisibles": r("nontext"),
        "findHighlight": r("bg_search"),
    }}]
    for scope, role in SCOPES:
        style = scheme.style(role)
        flags = [flag for flag in ("bold", "italic", "underline") if getattr(style, flag)]
        if scope in ("markup.bold", "markup.heading") and "bold" not in flags:
            flags.append("bold")
        if scope == "markup.italic" and "italic" not in flags:
            flags.append("italic")
        values = {"foreground": style.fg, "fontStyle": " ".join(flags)}
        if style.bg is not None:
            values["background"] = style.bg
        settings.append({"name": scope, "scope": scope, "settings": values})
    return plistlib.dumps({"name": scheme.name, "settings": settings}, sort_keys=False).decode("utf-8")


@register
class Bat(Target):
    """Emit a bat theme, installed into BAT_CONFIG_DIR/themes before rebuilding its cache."""

    name = "bat"
    scope = "scheme"
    description = "bat syntax theme (TextMate plist)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        return {f"{scheme.id}/bat.tmTheme": render_tmtheme(scheme)}
