"""Vimscript colourschemes with a Neovim Lua delegation path."""
from __future__ import annotations

from typing import Sequence

from ..highlights.groups import CORE_SECTIONS, build_groups
from ..highlights.plugins import editor
from ..scheme.model import STYLE_FLAGS, Scheme
from .base import RenderContext, Target, register
from .neovim import lua_value


def _vim_string(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


@register
class Vim(Target):
    """Emit standalone Vim highlights; Neovim prefers this .vim entry over .lua."""

    name = "vim"
    scope = "project"
    description = "Vim colourschemes with Neovim delegation"

    def render_project(self, schemes: Sequence[Scheme], ctx: RenderContext) -> dict[str, str]:
        module = ctx.lua_module or ctx.project_name
        if not module:
            raise ValueError("vim requires a lua_module or project_name")
        out = {}
        for scheme in schemes:
            lines = [ctx.header('"', scheme).rstrip(),
                     f'" Neovim tries colors/{scheme.id}.vim before colors/{scheme.id}.lua.',
                     f"if has('nvim') && !exists({_vim_string('g:' + module + '_vimscript')})",
                     f"  lua require({lua_value(module)}).load({lua_value(scheme.id)})",
                     "  finish", "endif", "hi clear", "if exists('syntax_on')", "  syntax reset", "endif",
                     f"set background={scheme.variant}", f"let g:colors_name = {_vim_string(scheme.id)}"]
            core_names = {name for section in CORE_SECTIONS for name in section(scheme)} | editor.groups(scheme).keys()
            for name, style in sorted(build_groups(scheme).items()):
                if name.startswith(("@", "GitSigns")) or name not in core_names:
                    continue
                flags = ",".join(flag for flag in STYLE_FLAGS if getattr(style, flag)) or "NONE"
                lines.append(f"hi {name} guifg={style.fg or 'NONE'} guibg={style.bg or 'NONE'} "
                             f"guisp={style.sp or 'NONE'} gui={flags}")
            ansi = ", ".join(_vim_string(scheme.ansi(i)) for i in range(16))
            lines.append(f"let g:terminal_ansi_colors = [{ansi}]")
            out[f"colors/{scheme.id}.vim"] = "\n".join(lines) + "\n"
        return out
