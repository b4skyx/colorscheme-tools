"""CodeCompanion groups from codecompanion.nvim/plugin/codecompanion.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Chat/tool states, review annotations and git-role diff highlights."""
    links = {
        "ChatError": "DiagnosticError", "ChatFold": "@markup.quote", "ChatHeader": "@markup.heading",
        "ChatInfo": "DiagnosticInfo", "ChatSeparator": "@punctuation.special", "ChatSubtext": "Comment",
        "ChatTokens": "Comment", "ChatTool": "Special", "ChatToolFailureIcon": "DiagnosticError",
        "ChatToolGroup": "Constant", "ChatToolInProgress": "DiagnosticInfo", "ChatToolInProgressIcon": "DiagnosticInfo",
        "ChatToolPending": "DiagnosticWarn", "ChatToolPendingIcon": "DiagnosticWarn", "ChatToolSuccessIcon": "DiagnosticOk",
        "ChatEditorContext": "Identifier", "ChatWarn": "DiagnosticWarn", "DiffAdd": "DiffAdd", "DiffDelete": "DiffDelete",
        "DiffText": "DiffText", "DiffTextDelete": "DiffDelete", "DiffBanner": "DiagnosticHint", "DiffBannerInline": "Comment",
        "CLIPath": "Directory", "CodeReviewAdded": "git.add", "CodeReviewComment": "DiagnosticHint",
        "CodeReviewHeader": "Comment", "CodeReviewPath": "Directory", "CodeReviewRemoved": "git.delete",
        "CodeReviewSent": "Comment", "VirtualText": "Comment",
    }
    return linked(scheme, {"CodeCompanion" + name: style for name, style in links.items()})
