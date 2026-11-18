"""lazy.nvim groups from lua/lazy/view/colors.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Plugin-manager headings, progress, reasons and diagnostics."""
    links: dict[str, str | S] = {
        "H1": "IncSearch", "H2": "Bold", "Comment": "Comment", "Normal": "NormalFloat", "Commit": "@variable.builtin",
        "CommitIssue": "Number", "CommitType": "Title", "CommitScope": "Italic", "Dimmed": "Comment", "Prop": "Comment",
        "Value": "@string", "NoCond": "DiagnosticWarn", "Local": "Constant", "ProgressDone": "Constant",
        "ProgressTodo": "LineNr", "Special": "@punctuation.special", "ReasonRuntime": "@macro",
        "ReasonPlugin": "Special", "ReasonEvent": "Constant", "ReasonKeys": "Statement", "ReasonStart": "@variable.member",
        "ReasonSource": "Character", "ReasonFt": "Character", "ReasonCmd": "Operator", "ReasonImport": "Identifier",
        "ReasonRequire": "@variable.parameter", "Button": "CursorLine", "ButtonActive": "Visual", "TaskOutput": "Normal",
        "Error": "DiagnosticError", "Warning": "DiagnosticWarn", "Info": "DiagnosticInfo", "Dir": "@markup.link",
        "Url": "@markup.link", "Bold": S(bold=True), "Italic": S(italic=True),
    }
    return linked(scheme, {"Lazy" + name: style for name, style in links.items()})
