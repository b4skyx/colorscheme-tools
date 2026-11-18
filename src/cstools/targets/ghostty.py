"""Ghostty theme file (``<id>/ghostty``)."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = "copy to ~/.config/ghostty/themes/<Name> and set theme = <Name> in ~/.config/ghostty/config"


@register
class Ghostty(Target):
    name = "ghostty"
    scope = "scheme"
    description = "Ghostty theme file"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        t = scheme.terminal_color
        lines = [f"palette = {i}={scheme.ansi(i)}" for i in range(16)]
        lines += [
            f"background = {t('background')}",
            f"foreground = {t('foreground')}",
            f"cursor-color = {t('cursor')}",
            f"cursor-text = {t('cursor_text')}",
            f"selection-background = {t('selection_background')}",
            f"selection-foreground = {t('selection_foreground')}",
        ]
        return {f"{scheme.id}/ghostty": ctx.header("#", scheme, USAGE) + "\n" + "\n".join(lines) + "\n"}
