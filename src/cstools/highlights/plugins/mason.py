"""mason.nvim groups from lua/mason/ui/colors.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Installer UI blocks and status text, resolved from scheme roles."""
    r = scheme.resolve
    links: dict[str, str | S] = {
        "MasonBackdrop": S(bg=r("ui.bg")), "MasonNormal": "NormalFloat",
        "MasonHeader": S(r("ui.bg"), r("syntax.function"), bold=True),
        "MasonHeaderSecondary": S(r("ui.bg"), r("syntax.constant"), bold=True),
        "MasonLink": "Underlined", "MasonError": "DiagnosticError", "MasonWarning": "DiagnosticWarn",
        "MasonHeading": S(bold=True),
    }
    for suffix, color in (("", "syntax.function"), ("Secondary", "syntax.constant")):
        links["MasonHighlight" + suffix] = S(r(color))
        links["MasonHighlightBlock" + suffix] = S(r("ui.bg"), r(color))
        links["MasonHighlightBlockBold" + suffix] = S(r("ui.bg"), r(color), bold=True)
    links.update({"MasonMuted": "Comment", "MasonMutedBlock": S(r("ui.bg"), r("ui.comment")),
                  "MasonMutedBlockBold": S(r("ui.bg"), r("ui.comment"), bold=True)})
    return linked(scheme, links)
