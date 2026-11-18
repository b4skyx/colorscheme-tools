"""fzf colour options: ``<id>/fzf.sh`` (POSIX shell) and ``<id>/fzf.fish`` (fish)."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = "eval this file (or add it to your shell rc) to extend FZF_DEFAULT_OPTS"

#: fzf colour key → role reference; ``bg+``/``hl+`` use the selection background
COLOR_KEYS: tuple[tuple[str, str], ...] = (
    ("fg", "ui.fg"),
    ("bg", "ui.bg"),
    ("hl", "syntax.function"),
    ("fg+", "ui.fg"),
    ("bg+", "bg_visual"),
    ("hl+", "syntax.function"),
    ("info", "ui.comment"),
    ("prompt", "syntax.function"),
    ("pointer", "diagnostic.warning"),
    ("marker", "git.add"),
    ("spinner", "syntax.function"),
    ("header", "diagnostic.warning"),
    ("border", "border"),
    ("gutter", "ui.bg"),
    ("query", "ui.fg"),
    ("separator", "border"),
    ("scrollbar", "border"),
    ("preview-fg", "ui.fg_dim"),
    ("preview-bg", "ui.bg_alt"),
    ("label", "ui.fg_dim"),
)


def color_option(scheme: Scheme) -> str:
    """The ``--color=key:hex,...`` value for one scheme."""
    return ",".join(f"{key}:{scheme.resolve(role)}" for key, role in COLOR_KEYS)


@register
class Fzf(Target):
    name = "fzf"
    scope = "scheme"
    description = "fzf colors (shell + fish)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        colors = color_option(scheme)
        sh = (ctx.header("#", scheme, USAGE) + "\n"
              + f'export FZF_DEFAULT_OPTS="$FZF_DEFAULT_OPTS --color={colors}"\n')
        fish = (ctx.header("#", scheme, USAGE) + "\n"
                + f"set -gx FZF_DEFAULT_OPTS $FZF_DEFAULT_OPTS --color={colors}\n")
        return {f"{scheme.id}/fzf.sh": sh, f"{scheme.id}/fzf.fish": fish}
