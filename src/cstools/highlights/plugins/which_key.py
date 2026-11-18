"""which-key.nvim groups from lua/which-key/colors.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Role-based key hints, borders and icons (including source-named colour icons)."""
    links = {
        "": "Function", "Separator": "Comment", "Group": "Keyword", "Desc": "Identifier",
        "Normal": "NormalFloat", "Title": "FloatTitle", "Border": "PmenuBorder", "Value": "Comment",
        "Icon": "@markup.link", "IconAzure": "Function", "IconBlue": "DiagnosticInfo",
        "IconCyan": "DiagnosticHint", "IconGreen": "DiagnosticOk", "IconGrey": "Normal",
        "IconOrange": "DiagnosticWarn", "IconPurple": "Constant", "IconRed": "DiagnosticError",
        "IconYellow": "DiagnosticWarn",
    }
    return linked(scheme, {"WhichKey" + name: style for name, style in links.items()})
