"""CopilotChat groups from CopilotChat.nvim/plugin/CopilotChat.lua."""
from ...scheme.model import ResolvedStyle as S, Scheme
from ._shared import linked


def groups(scheme: Scheme) -> dict[str, S]:
    """Assistant chat headings, resource kinds, help and selected text."""
    links: dict[str, str | S] = {
        "Header": "@markup.heading", "Separator": "@punctuation.special", "Selection": "Visual",
        "Status": "DiagnosticHint", "Help": "DiagnosticInfo", "Resource": "Constant", "Tool": "Function",
        "Prompt": "Statement", "Model": "Type", "Uri": "Underlined", "Annotation": "ColorColumn",
        "AnnotationHeader": S(scheme.resolve("diagnostic.hint"), scheme.resolve("bg_cursorline")),
    }
    return linked(scheme, {"CopilotChat" + name: style for name, style in links.items()})
