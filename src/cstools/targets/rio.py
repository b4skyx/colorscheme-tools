"""Rio theme file (``<id>/rio.toml``)."""
from __future__ import annotations

from ..scheme.model import ANSI_NAMES, Scheme
from .base import RenderContext, Target, register

USAGE = 'copy to ~/.config/rio/themes/<id>.toml and set theme = "<id>" in ~/.config/rio/config.toml'


@register
class Rio(Target):
    name = "rio"
    scope = "scheme"
    description = "Rio theme file"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r, t = scheme.resolve, scheme.terminal_color
        normal = {name: scheme.ansi(i) for i, name in enumerate(ANSI_NAMES)}
        bright = {name: scheme.ansi(i + 8) for i, name in enumerate(ANSI_NAMES)}
        dim = {name: r({"mix": [scheme.terminal["normal"][name], "bg", 0.35]}) for name in ANSI_NAMES}
        values = {
            "background": t("background"), "foreground": t("foreground"),
            "cursor": t("cursor"), "vi-cursor": r("diagnostic.warning"),
            "selection-background": t("selection_background"),
            "selection-foreground": t("selection_foreground"),
            "tabs": r("ui.bg_alt"), "tabs-foreground": r("ui.comment"),
            "tabs-active": r("syntax.function"), "tabs-active-foreground": t("background"),
            "split": r("bg_visual"),
            **normal, **{f"light-{k}": v for k, v in bright.items()},
            **{f"dim-{k}": v for k, v in dim.items()},
        }
        lines = [f"{k} = \"{v}\"\n" for k, v in values.items()]
        return {f"{scheme.id}/rio.toml": ctx.header("#", scheme, USAGE) + "\n[colors]\n" + "".join(lines)}
