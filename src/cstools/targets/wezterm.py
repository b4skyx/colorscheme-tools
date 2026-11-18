"""WezTerm colour-scheme file (``<id>/wezterm.toml``)."""
from __future__ import annotations

from ..scheme.model import ANSI_NAMES, Scheme
from .base import RenderContext, Target, register

USAGE = 'add color_scheme_dirs = ["/path/to/dir"] to wezterm.lua and set color_scheme = "<Name>"'

_TAB_SECTIONS = ("active_tab", "inactive_tab", "inactive_tab_hover", "new_tab", "new_tab_hover")


def _toml_str(value: str) -> str:
    """Quote a string for TOML."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _toml_table(name: str, values: dict[str, str | list[str]]) -> str:
    """One ``[name]`` section with string and string-array values."""
    lines = [f"[{name}]"]
    for key, value in values.items():
        if isinstance(value, list):
            rendered = "[" + ", ".join(_toml_str(v) for v in value) + "]"
        else:
            rendered = _toml_str(value)
        lines.append(f"{key} = {rendered}")
    return "\n".join(lines) + "\n\n"


@register
class WezTerm(Target):
    name = "wezterm"
    scope = "scheme"
    description = "WezTerm color scheme (TOML for color_scheme_dirs)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r, t = scheme.resolve, scheme.terminal_color
        bg, fg = t("background"), t("foreground")
        warning, function = r("diagnostic.warning"), r("syntax.function")
        colors: dict[str, str | list[str]] = {
            "foreground": fg, "background": bg,
            "cursor_bg": t("cursor"), "cursor_fg": t("cursor_text"), "cursor_border": t("cursor"),
            "selection_fg": t("selection_foreground"), "selection_bg": t("selection_background"),
            "scrollbar_thumb": r("ui.bg_alt"), "split": r("bg_visual"),
            "compose_cursor": warning, "ansi": [scheme.ansi(i) for i in range(8)],
            "brights": [scheme.ansi(i + 8) for i in range(8)],
        }
        lines = [f"[metadata]\nname = {_toml_str(scheme.name)}\n\n",
                 _toml_table("colors", colors),
                 "[colors.tab_bar]\nbackground = " + _toml_str(r("ui.bg")) + "\n\n"]
        tabs = {"active_tab": {"bg_color": function, "fg_color": bg},
                "inactive_tab": {"bg_color": r("ui.bg_alt"), "fg_color": r("ui.comment")},
                "inactive_tab_hover": {"bg_color": r("ui.bg_alt"), "fg_color": r("ui.fg")},
                "new_tab": {"bg_color": r("ui.bg_alt"), "fg_color": r("ui.comment")},
                "new_tab_hover": {"bg_color": function, "fg_color": bg}}
        for section in _TAB_SECTIONS:
            lines.append(_toml_table(f"colors.tab_bar.{section}", tabs[section]))
        return {f"{scheme.id}/wezterm.toml": ctx.header("#", scheme, USAGE) + "\n" + "".join(lines).rstrip() + "\n"}
