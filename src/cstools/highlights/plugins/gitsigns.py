"""GitSigns groups from gitsigns.nvim/lua/gitsigns/highlight.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme


def groups(scheme: Scheme) -> dict[str, S]:
    """Line, number, staged, preview and blame highlights using only git-role hues."""
    r = scheme.resolve
    out = {}
    kinds = {"Add": "add", "Change": "change", "Delete": "delete", "Changedelete": "change",
             "Topdelete": "delete", "Untracked": "add"}
    for staged in ("", "Staged"):
        for kind, role in kinds.items():
            for suffix in ("", "Nr", "Ln", "Cul"):
                if (not staged and not suffix and kind in ("Add", "Change", "Delete")) or (
                        suffix == "Ln" and kind in ("Delete", "Topdelete")):
                    continue
                color = r(f"git.{role}")
                out[f"GitSigns{staged}{kind}{suffix}"] = (
                    S(bg=r(f"diff_{role}_bg")) if suffix == "Ln" else S(color))
    for kind, role in (("Add", "add"), ("Delete", "delete"), ("Change", "change")):
        for suffix in ("Inline", "LnInline"):
            out[f"GitSigns{kind}{suffix}"] = S(bg=r(f"diff_{role}_bg"))
    out.update({
        "GitSignsAddPreview": S(r("git.add"), r("diff_add_bg")),
        "GitSignsDeletePreview": S(r("git.delete"), r("diff_delete_bg")),
        "GitSignsNoEOLPreview": S(r("git.delete"), r("diff_delete_bg")),
        "GitSignsCurrentLineBlame": S(r("ui.comment"), italic=True),
        "GitSignsDiffStaged": S(r("ui.comment")),
        "GitSignsDeleteVirtLn": S(r("git.delete"), r("diff_delete_bg")),
        "GitSignsDeleteVirtLnInLine": S(bg=r("diff_delete_bg")), "GitSignsVirtLnum": S(r("line_nr")),
    })
    return out
