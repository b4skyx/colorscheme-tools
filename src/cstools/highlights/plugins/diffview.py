"""diffview-plus.nvim groups from lua/diffview/hl.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Diff panels, file statuses and inline overlays, preserving git-role colours."""
    links: dict[str, str | S] = {
        "Normal": "Normal", "NonText": "NonText", "CursorLine": "CursorLine", "WinSeparator": "WinSeparator",
        "SignColumn": "Normal", "StatusLine": "StatusLine", "StatusLineNC": "StatusLineNC",
        "EndOfBuffer": "EndOfBuffer", "FilePanelTitle": "Title", "FilePanelCounter": "Number",
        "FilePanelRootPath": "Title", "FilePanelFileName": "Normal", "FilePanelSelected": "Type",
        "FilePanelPath": "Comment", "FilePanelInsertions": "git.add", "FilePanelDeletions": "git.delete",
        "FilePanelConflicts": "DiagnosticSignWarn", "FilePanelMarked": "DiagnosticSignInfo",
        "FolderName": "Directory", "FolderSign": "PreProc", "Hash": "Identifier", "Reference": "Function",
        "ReflogSelector": "Special", "CommitRemoteRef": "Function", "CommitLocalOnly": "WarningMsg",
        "CommitMerged": "String", "CommitSelected": S(bold=True), "Dim1": "Comment",
        "Primary": "Function", "Secondary": "String", "StatusIgnored": "Comment",
    }
    for names, role in (("Added Untracked", "add"), ("Modified Renamed Copied TypeChange Unmerged", "change"),
                        ("Unknown Deleted Broken", "delete")):
        links.update({"Status" + name: "git." + role for name in names.split()})
    for kind in ("Add", "Delete", "Change", "Text"):
        links["Diff" + kind] = "Diff" + kind
    r = scheme.resolve
    links.update({"DiffAddAsDelete": "DiffDelete", "DiffDeleteDim": "Comment",
                  "DiffDeleteInline": S(r("git.delete"), r("diff_delete_bg"), strikethrough=True),
                  "DiffTextInline": S(bg=r("diff_text_bg")), "DiffAddInline": S(bg=r("diff_add_bg"))})
    return linked(scheme, {"Diffview" + name: style for name, style in links.items()})
