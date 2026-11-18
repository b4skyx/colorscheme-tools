"""Alacritty colour file (``<id>/alacritty.toml``)."""
from __future__ import annotations

from ..scheme.model import ANSI_NAMES, Scheme
from .base import RenderContext, Target, register

USAGE = 'add general.import = ["/path/to/alacritty.toml"] (or [import] on older versions) to alacritty.toml'


def _section(name: str, values: dict[str, str]) -> str:
    return f"[colors.{name}]\n" + "".join(f'{k} = "{v}"\n' for k, v in values.items()) + "\n"


@register
class Alacritty(Target):
    name = "alacritty"
    scope = "scheme"
    description = "Alacritty colors (TOML import)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r, t = scheme.resolve, scheme.terminal_color
        bg = t("background")
        normal = {k: scheme.ansi(i) for i, k in enumerate(ANSI_NAMES)}
        bright = {k: scheme.ansi(i + 8) for i, k in enumerate(ANSI_NAMES)}
        warning, function = r("diagnostic.warning"), r("syntax.function")
        text = (
            ctx.header("#", scheme, USAGE) + "\n"
            + _section("primary", {"background": bg, "foreground": t("foreground"), "dim_foreground": r("ui.fg_dim"),
                                   "bright_foreground": bright["white"]})
            + _section("cursor", {"text": t("cursor_text"), "cursor": t("cursor")})
            + _section("vi_mode_cursor", {"text": t("cursor_text"), "cursor": warning})
            + _section("selection", {"text": "CellForeground", "background": t("selection_background")})
            + _section("search.matches", {"foreground": bg, "background": warning})
            + _section("search.focused_match", {"foreground": bg, "background": function})
            + _section("hints.start", {"foreground": bg, "background": warning})
            + _section("hints.end", {"foreground": bg, "background": function})
            + _section("footer_bar", {"foreground": t("foreground"), "background": r("ui.bg_alt")})
            + _section("line_indicator", {"foreground": "None", "background": "None"})
            + _section("normal", normal) + _section("bright", bright).rstrip() + "\n"
        )
        return {f"{scheme.id}/alacritty.toml": text}
