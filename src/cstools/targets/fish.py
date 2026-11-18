"""fish theme file (``<id>/fish.theme``) for ``~/.config/fish/themes/<Name>.theme``."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = "copy to ~/.config/fish/themes/<Name>.theme, then run: fish_config theme save <Name>"

#: fish_color_* name → (fg role, extra flags); ``valid_path`` is always underlined
SYNTAX_COLORS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("normal", "ui.fg", ()),
    ("command", "syntax.function", ()),
    ("keyword", "syntax.keyword", ()),
    ("quote", "syntax.string", ()),
    ("redirection", "syntax.operator", ()),
    ("end", "syntax.operator", ()),
    ("error", "diagnostic.error", ()),
    ("param", "syntax.variable", ()),
    ("valid_path", "ui.fg", ("--underline",)),
    ("option", "syntax.constant", ()),
    ("comment", "ui.comment", ()),
    ("selection", "bg_visual", ()),
    ("operator", "syntax.operator", ()),
    ("escape", "syntax.escape", ()),
    ("autosuggestion", "ui.comment", ()),
    ("cwd", "syntax.function", ()),
    ("cwd_root", "syntax.function", ()),
    ("user", "syntax.function", ()),
    ("host", "syntax.function", ()),
    ("host_remote", "diagnostic.warning", ()),
    ("status", "diagnostic.error", ()),
    ("cancel", "diagnostic.error", ()),
    ("search_match", "ui.fg", ()),
    ("history_current", "bg_visual", ()),
)

#: pager colour names, in output order
PAGER_COLORS: tuple[str, ...] = (
    "progress", "background", "prefix", "completion", "description",
    "selected_background", "selected_prefix", "selected_completion", "selected_description",
    "secondary_background", "secondary_prefix", "secondary_completion", "secondary_description",
)


def _strip(hex_: str) -> str:
    """Drop the leading ``#``: fish themes carry bare hex."""
    return hex_.lstrip("#")


def _fish_args(scheme: Scheme, role: str, flags: tuple[str, ...], background: bool = False) -> str:
    """``<hex> --flag…`` argument list; selection-style entries become ``--background=<hex>``."""
    hex_ = _strip(scheme.resolve(role))
    if background:
        flags = (*flags, f"--background={hex_}")
        return " ".join(flags)
    return " ".join((hex_, *flags)).strip()


@register
class Fish(Target):
    name = "fish"
    scope = "scheme"
    description = "fish theme (fish_config theme)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        lines = [f"# name: '{scheme.name}'"]
        style = scheme.style("syntax.comment")
        comment_flags = ("--italics",) if style.italic else ()
        for name, role, flags in SYNTAX_COLORS:
            if name == "comment":
                flags = (*flags, *comment_flags)
            bg_only = name in ("selection", "history_current")
            lines.append(f"fish_color_{name} {_fish_args(scheme, role, flags, background=bg_only)}")
        pager_args = _pager_args(scheme)
        for name in PAGER_COLORS:
            lines.append(f"fish_pager_color_{name} {pager_args[name]}")
        text = ctx.header("#", scheme, USAGE) + "\n" + "\n".join(lines) + "\n"
        return {f"{scheme.id}/fish.theme": text}


def _pager_args(scheme: Scheme) -> dict[str, str]:
    """fish_pager_color_* argument lists derived from the scheme roles (hex without ``#``)."""
    fg, fg_dim, comment = scheme.resolve("ui.fg"), scheme.resolve("ui.fg_dim"), scheme.resolve("ui.comment")
    alt, visual, function = scheme.resolve("ui.bg_alt"), scheme.resolve("bg_visual"), scheme.resolve("syntax.function")
    return {
        "progress": _strip(fg_dim),
        "background": f"--background={_strip(scheme.resolve('ui.bg'))}",
        "prefix": _strip(function),
        "completion": _strip(fg),
        "description": _strip(comment),
        "selected_background": f"--background={_strip(visual)}",
        "selected_prefix": _strip(function),
        "selected_completion": _strip(fg),
        "selected_description": _strip(comment),
        "secondary_background": f"--background={_strip(alt)}",
        "secondary_prefix": _strip(fg_dim),
        "secondary_completion": _strip(fg_dim),
        "secondary_description": _strip(fg_dim),
    }
