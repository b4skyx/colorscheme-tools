"""indent-blankline.nvim groups from lua/ibl/highlights.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme


def groups(scheme: Scheme) -> dict[str, S]:
    """Indent and whitespace guides with a stronger scope guide."""
    return {"IblIndent": S(scheme.resolve("nontext")), "IblWhitespace": S(scheme.resolve("nontext")),
            "IblScope": S(scheme.resolve("border"))}
