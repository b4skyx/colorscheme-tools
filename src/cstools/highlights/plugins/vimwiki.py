"""vimwiki groups from syntax/vimwiki.vim."""
from dataclasses import replace

from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Wiki prose, headings, inline styles, links and markup delimiters."""
    r = scheme.resolve
    links: dict[str, str | S] = {
        "VimwikiMarkers": "NonText", "VimwikiError": "DiagnosticError", "VimwikiEqIn": "Number",
        "VimwikiCode": "PreProc", "VimwikiPre": "PreProc", "VimwikiPreDelim": "PreProc", "VimwikiMath": "Number",
        "VimwikiNoExistsLink": "SpellBad", "VimwikiLink": "Underlined", "VimwikiList": "Identifier",
        "VimwikiListTodo": "Identifier", "VimwikiCheckBoxDone": "Comment", "VimwikiHR": "Identifier", "VimwikiTag": "Keyword",
        "VimwikiDelText": S(r("ui.comment"), strikethrough=True), "VimwikiSuperScript": "Number",
        "VimwikiSubScript": "Number", "VimwikiTodo": "Todo", "VimwikiComment": "Comment",
        "VimwikiMultilineComment": "Comment", "VimwikiPlaceholder": "Special", "VimwikiPlaceholderParam": "String",
        "VimwikiHTMLtag": "Special",
    }
    for index in range(1, 7):
        links[f"VimwikiHeader{index}"] = "Title"
    for name, flags in {"Bold": {"bold": True}, "Italic": {"italic": True}, "BoldItalic": {"bold": True, "italic": True},
                        "BoldUnderline": {"bold": True, "underline": True}, "ItalicUnderline": {"italic": True, "underline": True},
                        "BoldItalicUnderline": {"bold": True, "italic": True, "underline": True}}.items():
        links["Vimwiki" + name] = replace(scheme.style("syntax.variable"), **flags)
    for name in ("EqIn", "Bold", "Italic", "BoldItalic", "Code", "Pre", "Math", "NoExistsLink", "Link", "DelText",
                 "SuperScript", "SubScript"):
        links["Vimwiki" + name + "T"] = "Vimwiki" + name
    for name in ("EqIn", "Bold", "Italic", "BoldItalic", "ItalicBold", "DelText", "SuperScript", "SubScript", "Code", "Header"):
        links["Vimwiki" + name + "Char"] = "NonText"
        links["Vimwiki" + name + "CharT"] = "NonText"
    links["VimwikiCellSeparator"] = "NonText"
    return linked(scheme, links)
