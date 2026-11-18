"""nvim-tree.lua groups from lua/nvim-tree/appearance/init.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Tree surfaces, folder/file names, git state and diagnostic indicators."""
    links: dict[str, str | S] = {
        "Normal": "NormalFloat", "NormalFloat": "NormalFloat", "NormalFloatBorder": "PmenuBorder",
        "NormalNC": "NormalFloat", "LineNr": "LineNr", "WinSeparator": "WinSeparator",
        "EndOfBuffer": "EndOfBuffer", "Popup": "NormalFloat", "SignColumn": "NormalFloat",
        "CursorColumn": "CursorColumn", "CursorLine": "CursorLine", "CursorLineNr": "CursorLineNr",
        "StatusLine": "StatusLine", "StatusLineNC": "StatusLineNC", "ExecFile": "String",
        "ImageFile": "String", "SpecialFile": "Title", "Symlink": "Underlined", "RootFolder": "Title",
        "FolderName": "Directory", "EmptyFolderName": "Directory", "OpenedFolderName": "Directory",
        "SymlinkFolderName": "Directory", "FileIcon": "Identifier", "SymlinkIcon": "Special",
        "FolderIcon": "Directory", "OpenedFolderIcon": "Directory", "ClosedFolderIcon": "Directory",
        "FolderArrowClosed": "NonText", "FolderArrowOpen": "NonText", "IndentMarker": "NonText",
        "WindowPicker": S(scheme.resolve("ui.bg"), scheme.resolve("syntax.function"), bold=True),
        "LiveFilterPrefix": "PreProc", "LiveFilterValue": "String", "CutHL": "SpellBad", "CopiedHL": "SpellRare",
        "BookmarkIcon": "Special", "BookmarkHL": "SpellLocal", "ModifiedIcon": "git.change",
        "ModifiedFileHL": "git.change", "ModifiedFolderHL": "git.change", "HiddenIcon": "Comment",
        "HiddenFileHL": "Comment", "HiddenFolderHL": "Comment", "HiddenDisplay": "Comment", "OpenedHL": "Special",
    }
    for status, role in {"Deleted": "git.delete", "Dirty": "git.change", "Ignored": "ui.comment",
                         "Merge": "git.change", "New": "git.add", "Renamed": "git.change", "Staged": "git.add"}.items():
        links[f"Git{status}Icon"] = role
        for part in ("File", "Folder"):
            links[f"Git{part}{status}HL"] = role
    for severity in ("Error", "Warn", "Info", "Hint"):
        links[f"Diagnostic{severity}Icon"] = "Diagnostic" + severity
        for part in ("File", "Folder"):
            links[f"Diagnostic{severity}{part}HL"] = "DiagnosticUnderline" + severity
    return linked(scheme, {"NvimTree" + name: style for name, style in links.items()})
