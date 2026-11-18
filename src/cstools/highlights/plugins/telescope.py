"""Telescope groups from telescope.nvim/plugin/telescope.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Style picker surfaces, borders, result kinds and git previews."""
    r = scheme.resolve
    links: dict[str, str | S] = {
        "TelescopeSelection": S(r("ui.fg"), r("bg_visual")),
        "TelescopeSelectionCaret": "syntax.function", "TelescopeMultiSelection": "Type",
        "TelescopeMultiIcon": "Identifier", "TelescopeNormal": "NormalFloat",
        "TelescopeBorder": S(r("border"), r("ui.bg_alt")), "TelescopeTitle": "Title",
        "TelescopePromptCounter": "NonText", "TelescopeMatching": "Special",
        "TelescopePromptPrefix": "Identifier", "TelescopePreviewLine": "Visual",
        "TelescopePreviewMatch": "Search", "TelescopePreviewPipe": "Constant",
        "TelescopePreviewCharDev": "Constant", "TelescopePreviewDirectory": "Directory",
        "TelescopePreviewBlock": "Constant", "TelescopePreviewLink": "Special",
        "TelescopePreviewSocket": "Statement", "TelescopePreviewRead": "Constant",
        "TelescopePreviewWrite": "Statement", "TelescopePreviewExecute": "String",
        "TelescopePreviewHyphen": "NonText", "TelescopePreviewSticky": "Keyword",
        "TelescopePreviewSize": "String", "TelescopePreviewUser": "Constant",
        "TelescopePreviewGroup": "Constant", "TelescopePreviewDate": "Directory",
        "TelescopePreviewMessage": "TelescopeNormal", "TelescopePreviewMessageFillchar": "TelescopeNormal",
        "TelescopeResultsClass": "Type", "TelescopeResultsConstant": "Constant",
        "TelescopeResultsField": "syntax.property", "TelescopeResultsFunction": "Function",
        "TelescopeResultsMethod": "Function", "TelescopeResultsOperator": "Operator",
        "TelescopeResultsStruct": "Type", "TelescopeResultsVariable": "Identifier",
        "TelescopeResultsLineNr": "LineNr", "TelescopeResultsIdentifier": "Identifier",
        "TelescopeResultsNumber": "Number", "TelescopeResultsComment": "Comment",
        "TelescopeResultsSpecialComment": "Comment", "TelescopeResultsDiffChange": "git.change",
        "TelescopeResultsDiffAdd": "git.add", "TelescopeResultsDiffDelete": "git.delete",
        "TelescopeResultsDiffUntracked": "git.add",
    }
    for part in ("Prompt", "Results", "Preview"):
        for kind in ("Normal", "Border", "Title"):
            links[f"Telescope{part}{kind}"] = "Telescope" + kind
    return linked(scheme, links)
