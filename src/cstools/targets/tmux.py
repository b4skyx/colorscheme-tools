"""tmux style file (``<id>/tmux.conf``), meant to be ``source-file``d from tmux.conf."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register

USAGE = "source-file /path/to/tmux.conf   (in tmux.conf)"

#: option → style spec; roles are resolved per scheme, ``bold`` is passed through
STYLES: tuple[tuple[str, str], ...] = (
    ("status-style", "fg=ui.fg,bg=ui.bg"),
    ("status-left-style", "fg=ui.fg_dim,bg=ui.bg"),
    ("status-right-style", "fg=ui.fg_dim,bg=ui.bg"),
    ("window-status-style", "fg=ui.fg_dim,bg=ui.bg"),
    ("window-status-current-style", "fg=ui.bg,bg=syntax.function,bold"),
    ("window-status-activity-style", "bg=bg_visual"),
    ("window-status-bell-style", "bg=diagnostic.warning,fg=ui.bg"),
    ("pane-border-style", "fg=border"),
    ("pane-active-border-style", "fg=syntax.function"),
    ("message-style", "fg=ui.fg,bg=ui.bg"),
    ("message-command-style", "fg=ui.fg,bg=ui.bg_alt"),
    ("mode-style", "fg=ui.fg,bg=bg_visual"),
    ("copy-mode-match-style", "fg=ui.bg,bg=diagnostic.warning"),
    ("copy-mode-current-match-style", "fg=ui.bg,bg=syntax.function"),
    ("popup-style", "fg=ui.fg,bg=ui.bg"),
    ("popup-border-style", "fg=border"),
    ("menu-style", "fg=ui.fg,bg=ui.bg"),
    ("menu-selected-style", "fg=ui.bg,bg=syntax.function"),
    ("menu-border-style", "fg=border"),
)

#: plain colour options (tmux rejects ``fg=``/``bg=`` prefixes on these)
COLOURS: tuple[tuple[str, str], ...] = (
    ("display-panes-colour", "syntax.function"),
    ("display-panes-active-colour", "diagnostic.warning"),
    ("clock-mode-colour", "syntax.function"),
)

#: user options (@<module>_<name>) exposing the palette to custom status formats
USER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("bg", "ui.bg"), ("bg_alt", "ui.bg_alt"), ("fg", "ui.fg"), ("fg_dim", "ui.fg_dim"),
    ("comment", "ui.comment"), ("accent", "syntax.function"), ("error", "diagnostic.error"),
    ("warning", "diagnostic.warning"), ("info", "diagnostic.info"), ("hint", "diagnostic.hint"),
    ("add", "git.add"), ("change", "git.change"), ("delete", "git.delete"),
)


def _style(scheme: Scheme, spec: str) -> str:
    """Turn a ``fg=role,bg=role,bold`` spec into a tmux style value."""
    parts = []
    for item in spec.split(","):
        if item == "bold":
            parts.append(item)
        else:
            key, _, role = item.partition("=")
            parts.append(f"{key}={scheme.resolve(role)}")
    return ",".join(parts)


@register
class Tmux(Target):
    name = "tmux"
    scope = "scheme"
    description = "tmux styles (source-file)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        module = ctx.lua_module or "cstools"
        lines = [f"set -g {option} {_style(scheme, spec)}" for option, spec in STYLES]
        lines += [f'set -g {option} "{scheme.resolve(role)}"' for option, role in COLOURS]
        lines += [f'set -g @{module}_{name} "{scheme.resolve(role)}"' for name, role in USER_OPTIONS]
        text = ctx.header("#", scheme, USAGE) + "\n" + "\n".join(lines) + "\n"
        return {f"{scheme.id}/tmux.conf": text}
