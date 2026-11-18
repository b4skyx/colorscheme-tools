"""Git delta feature configuration with role-based diff and decoration styles."""
from __future__ import annotations

from ..scheme.model import Scheme
from .base import RenderContext, Target, register


def _quote(value: str) -> str:
    """Quote a git-config string, including subsection names."""
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\t', '\\t') + '"'


@register
class Delta(Target):
    name = "delta"
    scope = "scheme"
    description = "Git delta feature (gitconfig include)"

    def render(self, scheme: Scheme, ctx: RenderContext) -> dict[str, str]:
        r = scheme.resolve
        feature = f"{ctx.lua_module or 'cstools'}-{scheme.id}"
        values = {
            scheme.variant: "true",
            "plus-style": f"syntax {r('diff_add_bg')}",
            "minus-style": f"syntax {r('diff_delete_bg')}",
            "plus-emph-style": f"syntax {r({'mix': ['ui.bg', 'git.add', 0.45]})}",
            "minus-emph-style": f"syntax {r({'mix': ['ui.bg', 'git.delete', 0.45]})}",
            "zero-style": "syntax", "file-style": f"{r('syntax.function')} bold",
            "file-decoration-style": f"{r('border')} ul",
            "hunk-header-style": f"file line-number syntax {r('bg_cursorline')}",
            "hunk-header-decoration-style": f"{r('border')} box",
            "hunk-header-line-number-style": r("syntax.number"),
            "line-numbers-minus-style": r("git.delete"),
            "line-numbers-plus-style": r("git.add"), "line-numbers-zero-style": r("line_nr"),
            "line-numbers-left-style": r("line_nr"), "line-numbers-right-style": r("line_nr"),
            "commit-decoration-style": f"{r('syntax.keyword')} box",
            "blame-palette": " ".join(r({'raise': ['ui.bg', amount]}) for amount in (0.02, 0.04, 0.06, 0.08)),
            "merge-conflict-ours-diff-header-style": f"{r('git.add')} bold",
            "merge-conflict-ours-diff-header-decoration-style": f"{r('git.add')} box",
            "merge-conflict-theirs-diff-header-style": f"{r('git.change')} bold",
            "merge-conflict-theirs-diff-header-decoration-style": f"{r('git.change')} box",
        }
        text = (ctx.header("#", scheme, f"include this file in gitconfig; set delta.features = {feature}")
                + "# Set syntax-theme to any installed bat theme to customize syntax highlighting.\n\n"
                + f"[delta {_quote(feature)}]\n"
                + "".join(f"\t{key} = {_quote(value)}\n" for key, value in values.items()))
        return {f"{scheme.id}/delta.gitconfig": text}
