"""blink.cmp groups from lua/blink/cmp/{highlights,types}.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked

# LSP completion kinds from blink.cmp.types (not ANSI colour names).
KIND_ROLES = {
    "Text": "variable", "Method": "function", "Function": "function", "Constructor": "constructor",
    "Field": "property", "Variable": "variable", "Class": "type", "Interface": "type", "Module": "module",
    "Property": "property", "Unit": "number", "Value": "constant", "Enum": "type", "Keyword": "keyword",
    "Snippet": "macro", "Color": "constant", "File": "string", "Reference": "parameter", "Folder": "module",
    "EnumMember": "constant", "Constant": "constant", "Struct": "type", "Event": "type",
    "Operator": "operator", "TypeParameter": "type",
}


def groups(scheme: Scheme) -> dict[str, S]:
    """Completion menus, documentation, signatures and role-coloured item kinds."""
    r = scheme.resolve
    links: dict[str, str | S] = {
        "BlinkCmpLabel": "Identifier", "BlinkCmpLabelMatch": "Special",
        "BlinkCmpLabelDeprecated": S(r("ui.comment"), strikethrough=True),
        "BlinkCmpLabelDetail": "Comment", "BlinkCmpLabelDescription": "Comment", "BlinkCmpSource": "Comment",
        "BlinkCmpKind": "Type", "BlinkCmpScrollBarThumb": "PmenuThumb", "BlinkCmpScrollBarGutter": "PmenuSbar",
        "BlinkCmpGhostText": "NonText", "BlinkCmpMenu": "Pmenu", "BlinkCmpMenuBorder": "PmenuBorder",
        "BlinkCmpMenuSelection": "PmenuSel", "BlinkCmpDoc": "NormalFloat", "BlinkCmpDocBorder": "PmenuBorder",
        "BlinkCmpDocSeparator": "PmenuBorder", "BlinkCmpDocCursorLine": "Visual",
        "BlinkCmpSignatureHelp": "NormalFloat", "BlinkCmpSignatureHelpBorder": "PmenuBorder",
        "BlinkCmpSignatureHelpActiveParameter": "LspSignatureActiveParameter",
    }
    links.update({"BlinkCmpKind" + kind: "syntax." + role for kind, role in KIND_ROLES.items()})
    return linked(scheme, links)
