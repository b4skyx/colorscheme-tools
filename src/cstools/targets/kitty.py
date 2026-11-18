"""kitty colour file (``<id>/kitty.conf``)."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = "include /path/to/kitty.conf   (in kitty.conf)"


@register
class Kitty(Target):
    name = "kitty"
    scope = "scheme"
    description = "kitty colors (include file)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r, t = scheme.resolve, scheme.terminal_color
        bg = t("background")
        function, warning = r("syntax.function"), r("diagnostic.warning")
        lines = [
            f"foreground {t('foreground')}", f"background {bg}", "selection_foreground none",
            f"selection_background {t('selection_background')}", f"cursor {t('cursor')}",
            f"cursor_text_color {t('cursor_text')}",
            f"url_color {function}", f"active_border_color {function}", f"inactive_border_color {r('bg_visual')}",
            f"bell_border_color {warning}", "visual_bell_color none", "",
            f"tab_bar_background {r('ui.bg')}", f"active_tab_foreground {bg}", f"active_tab_background {function}",
            f"inactive_tab_foreground {r('ui.comment')}", f"inactive_tab_background {r('ui.bg_alt')}", "",
            f"mark1_foreground {bg}", f"mark1_background {function}", f"mark2_foreground {bg}",
            f"mark2_background {warning}", f"mark3_foreground {bg}", f"mark3_background {r('syntax.constant')}", "",
        ]
        lines += [f"color{i} {scheme.ansi(i)}" for i in range(16)]
        return {f"{scheme.id}/kitty.conf": ctx.header("#", scheme, USAGE) + "\n" + "\n".join(lines) + "\n"}
