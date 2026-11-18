"""Additional built-in UI, diagnostic and LSP groups from Neovim's runtime."""
from __future__ import annotations

from dataclasses import replace

from ...scheme.model import ResolvedStyle as S, Scheme
from ..groups import _treesitter


def groups(scheme: Scheme) -> dict[str, S]:
    """Built-in additions, kept separate so the legacy core remains byte-identical."""
    r = scheme.resolve
    out = {
        "FloatTitle": S(r("syntax.function"), r("ui.bg_alt"), bold=True),
        "PmenuBorder": S(r("border"), r("ui.bg_alt")),
        "PmenuSbar": S(bg=r("bg_cursorline")), "PmenuThumb": S(bg=r("border")),
        "PmenuKind": S(r("syntax.type")), "PmenuExtra": S(r("ui.comment")),
        "EndOfBuffer": S(r("nontext")), "FoldColumn": S(r("ui.comment"), r("ui.bg")),
        "NormalNC": S(r("ui.fg"), r("ui.bg")),
        "DiagnosticDeprecated": S(strikethrough=True), "DiagnosticUnnecessary": S(r("ui.comment")),
        "LspReferenceText": S(bg=r("bg_visual")), "LspReferenceRead": S(bg=r("bg_visual")),
        "LspReferenceWrite": S(bg=r("bg_visual"), bold=True),
        "LspReferenceTarget": S(bg=r("bg_visual")),
        "LspInlayHint": S(r("ui.comment"), r("bg_cursorline")),
        "LspCodeLens": S(r("ui.comment")), "LspCodeLensSeparator": S(r("border")),
        "LspSignatureActiveParameter": S(r("syntax.parameter"), bold=True),
    }
    for suffix, role in (("Error", "error"), ("Warn", "warning"), ("Info", "info"), ("Hint", "hint"), ("Ok", "ok")):
        for prefix in ("DiagnosticSign", "DiagnosticFloating"):
            out[prefix + suffix] = S(r(f"diagnostic.{role}"))
    captures = _treesitter(scheme)
    # Neovim runtime/doc/lsp.txt standard semantic token types and modifiers.
    tokens = {
        "namespace": "@module", "type": "@type", "class": "@type", "enum": "@type",
        "interface": "@type", "struct": "@type", "typeParameter": "@type.definition",
        "parameter": "@variable.parameter", "variable": "@variable", "property": "@property",
        "enumMember": "@constant", "event": "@type", "function": "@function",
        "method": "@function.method", "macro": "@function.macro", "keyword": "@keyword",
        "modifier": "@keyword.modifier", "comment": "@comment", "string": "@string",
        "number": "@number", "regexp": "@string.regexp", "operator": "@operator",
        "decorator": "@attribute",
    }
    out.update({"@lsp.type." + token: replace(captures[capture]) for token, capture in tokens.items()})
    modifiers = {
        "declaration": "@variable", "definition": "@variable", "readonly": "@constant",
        "static": "@constant", "deprecated": "@comment", "abstract": "@type",
        "async": "@keyword.coroutine", "modification": "@variable", "documentation": "@comment.documentation",
        "defaultLibrary": "@variable.builtin",
    }
    out.update({"@lsp.mod." + mod: replace(captures[capture]) for mod, capture in modifiers.items()})
    return out
