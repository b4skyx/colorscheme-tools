"""Yazi 26.x flavor and its shared TextMate syntax theme."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register
from .bat import render_tmtheme


@register
class Yazi(Target):
    name = "yazi"
    scope = "scheme"
    description = "Yazi flavor with TextMate syntax theme"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r = scheme.resolve
        # Keep the section/key layout of the yazi 26.x installed flavor reference.
        text = ctx.header("#", scheme, f"install {scheme.id}.yazi under yazi/flavors and select it in theme.toml") + f'''
[mgr]
cwd = {{ fg = "{r('syntax.function')}" }}
find_keyword = {{ fg = "{r('diagnostic.warning')}", bold = true, italic = true, underline = true }}
find_position = {{ fg = "{r('syntax.number')}", bg = "{r('ui.bg')}", bold = true, italic = true }}
symlink_target = {{ italic = true }}
marker_copied = {{ fg = "{r('git.add')}", bg = "{r('git.add')}" }}
marker_cut = {{ fg = "{r('git.delete')}", bg = "{r('git.delete')}" }}
marker_marked = {{ fg = "{r('syntax.function')}", bg = "{r('syntax.function')}" }}
marker_selected = {{ fg = "{r('diagnostic.warning')}", bg = "{r('diagnostic.warning')}" }}
count_copied = {{ fg = "{r('ui.bg')}", bg = "{r('git.add')}" }}
count_cut = {{ fg = "{r('ui.bg')}", bg = "{r('git.delete')}" }}
count_selected = {{ fg = "{r('ui.bg')}", bg = "{r('diagnostic.warning')}" }}
border_symbol = "│"
border_style = {{ fg = "{r('border')}" }}

[tabs]
active = {{ fg = "{r('ui.bg')}", bg = "{r('syntax.function')}" }}
inactive = {{ fg = "{r('ui.fg_dim')}", bg = "{r('ui.bg_alt')}" }}
sep_inner = {{ open = "", close = "" }}
sep_outer = {{ open = "", close = "" }}

[mode]
normal_main = {{ fg = "{r('ui.bg')}", bg = "{r('syntax.function')}", bold = true }}
normal_alt = {{ fg = "{r('syntax.function')}", bg = "{r('ui.bg_alt')}" }}
select_main = {{ fg = "{r('ui.bg')}", bg = "{r('diagnostic.warning')}", bold = true }}
select_alt = {{ fg = "{r('ui.fg_dim')}", bg = "{r('ui.bg_alt')}" }}
unset_main = {{ fg = "{r('ui.bg')}", bg = "{r('git.add')}", bold = true }}
unset_alt = {{ fg = "{r('ui.fg_dim')}", bg = "{r('ui.bg_alt')}" }}

[indicator]
parent = {{ reversed = true }}
current = {{ reversed = true }}
preview = {{ underline = true }}
padding = {{ open = "█", close = "█" }}

[status]
overall = {{ }}
sep_left = {{ open = "\ue0be", close = "\ue0b8" }}
sep_right = {{ open = "\ue0be", close = "\ue0b8" }}
perm_sep = {{ fg = "{r('border')}" }}
perm_type = {{ fg = "{r('syntax.type')}" }}
perm_read = {{ fg = "{r('git.add')}" }}
perm_write = {{ fg = "{r('git.change')}" }}
perm_exec = {{ fg = "{r('git.add')}" }}
progress_label = {{ fg = "{r('ui.fg')}", bold = true }}
progress_normal = {{ fg = "{r('syntax.function')}", bg = "{r('ui.bg_alt')}" }}
progress_error = {{ fg = "{r('diagnostic.error')}", bg = "{r('ui.bg_alt')}" }}

[which]
cols = 3
mask = {{ bg = "{r('ui.bg_alt')}" }}
cand = {{ fg = "{r('syntax.function')}" }}
rest = {{ fg = "{r('ui.fg_dim')}" }}
desc = {{ fg = "{r('syntax.string')}" }}
separator = "  "
separator_style = {{ fg = "{r('border')}" }}

[confirm]
border = {{ fg = "{r('border')}" }}
title = {{ fg = "{r('syntax.function')}" }}
body = {{ fg = "{r('ui.fg')}" }}
list = {{ fg = "{r('ui.fg')}" }}
btn_yes = {{ reversed = true, fg = "{r('ui.fg')}" }}
btn_no = {{}}
btn_labels = [ "  [Y]es  ", "  (N)o  " ]

[spot]
border = {{ fg = "{r('border')}" }}
title = {{ fg = "{r('syntax.function')}" }}
tbl_col = {{ fg = "{r('syntax.function')}" }}
tbl_cell = {{ fg = "{r('diagnostic.warning')}", reversed = true }}

[notify]
title_info = {{ fg = "{r('diagnostic.info')}" }}
title_warn = {{ fg = "{r('diagnostic.warning')}" }}
title_error = {{ fg = "{r('diagnostic.error')}" }}

[pick]
border = {{ fg = "{r('border')}" }}
active = {{ fg = "{r('syntax.function')}", bold = true }}
inactive = {{}}

[input]
border = {{ fg = "{r('border')}" }}
title = {{}}
value = {{}}
selected = {{ reversed = true }}

[cmp]
border = {{ fg = "{r('border')}" }}
active = {{ reversed = true, fg = "{r('syntax.function')}" }}
inactive = {{ fg = "{r('ui.fg')}" }}

[tasks]
border = {{ fg = "{r('border')}" }}
title = {{}}
hovered = {{ underline = true }}

[help]
border = {{ fg = "{r('border')}" }}
chord = {{ fg = "{r('syntax.function')}" }}
action = {{}}
hovered = {{ reversed = true, bold = true }}

[filetype]
rules = [
  {{ mime = "image/*", fg = "{r('syntax.type')}" }},
  {{ mime = "{{audio,video}}/*", fg = "{r('syntax.constant')}" }},
  {{ mime = "application/*zip", fg = "{r('git.delete')}" }},
  {{ mime = "application/x-{{tar,bzip*,7z-compressed,xz,rar}}", fg = "{r('git.delete')}" }},
  {{ mime = "application/{{pdf,doc,rtf,vnd.*}}", fg = "{r('syntax.string')}" }},
  {{ url = "*", fg = "{r('ui.fg')}" }},
  {{ url = "*/", fg = "{r('syntax.function')}" }},
]
'''
        base = f"{scheme.id}/yazi/{scheme.id}.yazi"
        return {f"{base}/flavor.toml": text, f"{base}/tmtheme.xml": render_tmtheme(scheme)}
