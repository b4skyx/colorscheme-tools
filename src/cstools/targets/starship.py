"""starship prompt palette (``<id>/starship.toml``), merged into the user's starship.toml."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = 'merge into your starship.toml and set palette = "<id>"'

#: palette alias → role reference resolved per scheme
PALETTE_ROLES: tuple[tuple[str, str], ...] = (
    ("bg", "ui.bg"), ("fg", "ui.fg"), ("comment", "ui.comment"), ("accent", "syntax.function"),
    ("error", "diagnostic.error"), ("warning", "diagnostic.warning"), ("info", "diagnostic.info"),
    ("hint", "diagnostic.hint"), ("success", "git.add"),
)

#: terminal colour aliases: starship name → ANSI index (``purple`` is magenta)
TERMINAL_ALIASES: tuple[tuple[str, int], ...] = (
    ("black", 0), ("red", 1), ("green", 2), ("yellow", 3), ("blue", 4), ("purple", 5), ("cyan", 6), ("white", 7),
    ("bright_black", 8), ("bright_red", 9), ("bright_green", 10), ("bright_yellow", 11), ("bright_blue", 12),
    ("bright_purple", 13), ("bright_cyan", 14), ("bright_white", 15),
)


@register
class Starship(Target):
    name = "starship"
    scope = "scheme"
    description = "starship palette (TOML)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        entries = [(key, scheme.resolve(role)) for key, role in PALETTE_ROLES]
        entries += [(name, scheme.ansi(i)) for name, i in TERMINAL_ALIASES]
        lines = [f"# Merge this table into your starship.toml and set palette = \"{scheme.id}\".", "",
                 f"[palettes.{scheme.id}]"]
        lines += [f'{key} = "{value}"' for key, value in entries]
        text = ctx.header("#", scheme, USAGE) + "\n" + "\n".join(lines) + "\n"
        return {f"{scheme.id}/starship.toml": text}
