"""lspsaga.nvim groups from lua/lspsaga/{highlight,lspkind}.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """LSP actions, hover/rename/finder windows, winbar and symbol kinds."""
    r = scheme.resolve
    links: dict[str, str | S] = {
        "SagaTitle": "Title", "SagaBorder": "PmenuBorder", "SagaNormal": "NormalFloat", "SagaToggle": "Comment",
        "SagaBeacon": S(bg=r("syntax.function")), "SagaVirtLine": "NonText", "SagaSpinnerTitle": "Statement",
        "SagaSpinner": "Statement", "SagaText": "Comment", "SagaSelect": "String", "SagaSearch": "Search",
        "SagaFinderFname": "Function", "SagaDetail": "Comment", "SagaInCurrent": "Keyword",
        "SagaCount": S(r("ui.fg"), r("bg_visual"), bold=True), "SagaSep": "Comment",
        "ActionPreviewNormal": "NormalFloat", "ActionPreviewBorder": "PmenuBorder", "ActionPreviewTitle": "Title",
        "CodeActionText": "@variable", "CodeActionNumber": "git.add", "CodeActionCursorLine": "CursorLine",
        "HoverNormal": "NormalFloat", "HoverBorder": "PmenuBorder", "RenameBorder": "PmenuBorder",
        "RenameNormal": "NormalFloat", "RenameMatch": "Search", "DiagnosticBorder": "PmenuBorder",
        "DiagnosticNormal": "NormalFloat", "DiagnosticText": "Normal", "DiagnosticShowNormal": "NormalFloat",
        "DiagnosticShowBorder": "PmenuBorder", "SagaLightBulb": "DiagnosticSignHint", "TerminalBorder": "PmenuBorder",
        "TerminalNormal": "NormalFloat", "SagaImpIcon": "PreProc", "SagaWinbarSep": "Operator",
        "SagaWinbarFileName": "Comment", "SagaWinbarFolderName": "Comment", "SagaWinbarFolder": "Directory",
        "SagaFileName": "Comment", "SagaFolderName": "Comment", "SagaButton": "DiagnosticHint",
        "SagaActionTitle": S(r("ui.bg"), r("diagnostic.hint")),
    }
    kinds = {
        "File": "tag", "Module": "module", "Namespace": "module", "Package": "module", "Class": "type",
        "Method": "function", "Property": "property", "Field": "property", "Constructor": "constructor",
        "Enum": "type", "Interface": "type", "Function": "function", "Variable": "variable", "Constant": "constant",
        "String": "string", "Number": "number", "Boolean": "boolean", "Array": "type", "Object": "type",
        "Key": "constant", "Null": "constant", "EnumMember": "constant", "Struct": "type", "Event": "type",
        "Operator": "operator", "TypeParameter": "type", "TypeAlias": "type", "Parameter": "parameter",
        "StaticMethod": "function", "Macro": "macro", "Text": "variable", "Snippet": "macro", "Folder": "module",
        "Unit": "number", "Value": "constant",
    }
    links.update({"Saga" + kind: "syntax." + role for kind, role in kinds.items()})
    for severity in ("Error", "Warn", "Info", "Hint"):
        role = "warning" if severity == "Warn" else severity.lower()
        links[f"Diagnostic{severity.upper()}Reverse"] = S(r("ui.bg"), r("diagnostic." + role))
    return linked(scheme, links)
