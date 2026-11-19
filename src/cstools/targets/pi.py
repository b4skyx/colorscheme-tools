"""Pi agent theme (``<id>/pi/<Name>.json``), placed in the agent's themes directory."""
from __future__ import annotations

import json
from typing import Any

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = "copy to ~/.pi/agent/themes/<Name>.json (or .pi/themes/ for one project) and select <Name> in /settings"

#: vars block: theme-level aliases shared by several colors entries.
#: Role paths resolve via ``scheme.resolve``; integer entries go through ``scheme.ansi``.
VARS: tuple[tuple[str, str | int], ...] = (
    ("text", "ui.fg"), ("muted", "ui.fg_dim"), ("accent", "syntax.function"),
    ("success", "git.add"), ("warning", "diagnostic.warning"), ("error", "diagnostic.error"),
    ("blue", 4), ("green", 2), ("yellow", 3), ("red", 1),
)

#: colors entry → role reference; ``accent``/``success``/``error``/``warning`` come from vars
COLOR_ROLES: tuple[tuple[str, str], ...] = (
    # general interface; var aliases resolve against the vars block
    ("accent", "accent"),
    ("border", "border"), ("borderAccent", "syntax.function"), ("borderMuted", "line_nr"),
    ("success", "success"), ("error", "error"), ("warning", "warning"),
    ("muted", "muted"), ("dim", "ui.comment"), ("text", "text"),
    ("thinkingText", "ui.fg_dim"),
    # selection and fullscreen
    ("selectedBg", "bg_visual"), ("searchMatchBg", "bg_search"), ("searchMatchText", "text"),
    ("scrollbarTrack", "line_nr"), ("scrollbarThumb", "ui.comment"),
    # messages
    ("userMessageBg", "ui.bg_alt"), ("userMessageText", "text"),
    ("customMessageBg", "bg_visual"), ("customMessageText", "muted"), ("customMessageLabel", "accent"),
    # tool execution
    ("toolPendingBg", "ui.bg_alt"), ("toolSuccessBg", "diff_add_bg"), ("toolErrorBg", "diff_delete_bg"),
    ("toolTitle", "text"), ("toolOutput", "muted"),
    # markdown
    ("mdHeading", "syntax.type"), ("mdLink", "accent"), ("mdLinkUrl", "muted"),
    ("mdCode", "syntax.string"), ("mdCodeBlock", "syntax.variable"), ("mdCodeBlockBorder", "border"),
    ("mdQuote", "muted"), ("mdQuoteBorder", "border"),
    ("mdHr", "border"), ("mdListBullet", "accent"),
    # tool diffs
    ("toolDiffAdded", "git.add"), ("toolDiffRemoved", "git.delete"), ("toolDiffContext", "ui.comment"),
    # syntax highlighting
    ("syntaxComment", "syntax.comment"), ("syntaxKeyword", "syntax.keyword"),
    ("syntaxFunction", "syntax.function"), ("syntaxVariable", "syntax.variable"),
    ("syntaxString", "syntax.string"), ("syntaxNumber", "syntax.number"),
    ("syntaxType", "syntax.type"), ("syntaxOperator", "syntax.operator"),
    ("syntaxPunctuation", "syntax.punctuation"),
    # editor modes
    ("bashMode", "git.add"),
)

#: thinking-level borders: quiet neutrals, then an ANSI gradient for separation
THINKING_ROLES: tuple[tuple[str, str], ...] = (
    ("thinkingOff", "ui.comment"), ("thinkingMinimal", "ui.fg_dim"),
    ("thinkingLow", "git.add"), ("thinkingMedium", "accent"),
    ("thinkingHigh", "diagnostic.info"), ("thinkingXhigh", "error"),
    ("thinkingMax", "warning"),
)


@register
class Pi(Target):
    name = "pi"
    scope = "scheme"
    description = "Pi agent theme (JSON)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        vars_ = {name: scheme.ansi(role) if isinstance(role, int) else scheme.resolve(role)
                 for name, role in VARS}
        colors: dict[str, str] = {}
        for name, role in COLOR_ROLES:
            colors[name] = vars_[role] if role in vars_ else scheme.resolve(role)
        for name, role in THINKING_ROLES:
            colors[name] = vars_.get(role) or scheme.resolve(role)
        theme: dict[str, Any] = {
            "$schema": "https://pi.dev/schemas/theme.schema.json",
            "name": scheme.name,
            "appearance": "light" if scheme.is_light else "dark",
            "vars": vars_,
            "colors": colors,
            "export": {
                "pageBg": scheme.resolve("ui.bg"),
                "cardBg": scheme.resolve("ui.bg_alt"),
                "infoBg": scheme.resolve("bg_search"),
            },
        }
        text = json.dumps(theme, indent=2) + "\n"
        name = scheme.id if "/" in scheme.name else scheme.name
        return {f"{scheme.id}/pi/{name}.json": text}
