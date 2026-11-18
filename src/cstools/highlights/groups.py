"""The role-based highlight template: Vim/Neovim groups, treesitter captures, diagnostics and git.

``build_groups(scheme)`` returns ``{group: ResolvedStyle}``. Core sections live here; extra sections are
discovered from ``cstools.highlights.plugins`` (each module exposes ``groups(scheme)``) and merged after
the core sections in module-name order.
"""
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import replace
from typing import Callable

from ..scheme.model import ResolvedStyle, Scheme
from . import plugins

Groups = dict[str, ResolvedStyle]
S = ResolvedStyle


def _editor_ui(s: Scheme) -> Groups:
    r = s.resolve
    bg, alt, fg, cm = r("ui.bg"), r("ui.bg_alt"), r("ui.fg"), r("ui.comment")
    warn, cursorline, visual = r("diagnostic.warning"), r("bg_cursorline"), r("bg_visual")
    return {
        "Normal": S(fg, bg), "NormalFloat": S(fg, alt), "FloatBorder": S(cm, alt),
        "Comment": s.style("syntax.comment"), "CursorLine": S(bg=cursorline),
        "CursorLineNr": S(warn, cursorline, bold=True), "LineNr": S(r("line_nr")), "Visual": S(bg=visual),
        "Search": S(fg, r("bg_search")), "IncSearch": S(bg, warn), "CurSearch": S(bg, warn),
        "StatusLine": S(fg, alt), "StatusLineNC": S(cm, alt), "Pmenu": S(fg, alt),
        "PmenuSel": S(fg, visual, bold=True), "SignColumn": S(bg=bg), "ColorColumn": S(bg=cursorline),
        "MatchParen": S(warn, visual, bold=True), "NonText": S(r("nontext")), "WinSeparator": S(r("border")),
        "Folded": S(cm, alt), "Title": replace(s.style("syntax.function"), bold=True),
    }


def _vim_syntax(s: Scheme) -> Groups:
    keyword = s.style("syntax.keyword")
    return {
        "Keyword": keyword, "Statement": keyword, "PreProc": s.style("syntax.macro"),
        "Function": s.style("syntax.function"), "String": s.style("syntax.string"), "Type": s.style("syntax.type"),
        "Constant": s.style("syntax.constant"), "Number": s.style("syntax.number"),
        "Boolean": s.style("syntax.boolean"), "Special": s.style("syntax.escape"),
        "Identifier": s.style("syntax.variable"), "Operator": s.style("syntax.operator"),
        "Delimiter": s.style("syntax.punctuation"), "Todo": s.style("syntax.todo"),
        "Error": S(s.resolve("diagnostic.error")),
    }


def _diagnostics(s: Scheme) -> Groups:
    out: Groups = {}
    for suffix, role in (("Error", "error"), ("Warn", "warning"), ("Info", "info"), ("Hint", "hint"), ("Ok", "ok")):
        c = s.resolve(f"diagnostic.{role}")
        out["Diagnostic" + suffix] = S(c)
        out["DiagnosticVirtualText" + suffix] = S(c, s.resolve(f"virtual_{role}_bg"))
        out["DiagnosticUnderline" + suffix] = S(sp=c, undercurl=True)
    return out


def _git(s: Scheme) -> Groups:
    add, change, delete = (s.resolve(f"git.{k}") for k in ("add", "change", "delete"))
    return {
        "DiffAdd": S(bg=s.resolve("diff_add_bg")), "DiffDelete": S(bg=s.resolve("diff_delete_bg")),
        "DiffChange": S(bg=s.resolve("diff_change_bg")), "DiffText": S(bg=s.resolve("diff_text_bg")),
        "GitSignsAdd": S(add), "GitSignsChange": S(change), "GitSignsDelete": S(delete),
        "Added": S(add), "Changed": S(change), "Removed": S(delete),
    }


def _treesitter(s: Scheme) -> Groups:
    st = s.style
    bg = s.resolve("ui.bg")
    keyword, function, typ, comment = st("syntax.keyword"), st("syntax.function"), st("syntax.type"), st("syntax.comment")
    return {
        "@variable": st("syntax.variable"), "@variable.builtin": st("syntax.builtin"),
        "@variable.parameter": st("syntax.parameter"), "@variable.member": st("syntax.property"),
        "@property": st("syntax.property"), "@constant": st("syntax.constant"),
        "@constant.builtin": replace(st("syntax.constant"), bold=True), "@constant.macro": st("syntax.constant"),
        "@module": st("syntax.module"), "@label": st("syntax.label"),
        "@string": st("syntax.string"), "@string.escape": st("syntax.escape"), "@string.regexp": st("syntax.regex"),
        "@string.special": st("syntax.escape"), "@string.documentation": replace(comment, italic=True),
        "@character": st("syntax.string"), "@boolean": st("syntax.boolean"), "@number": st("syntax.number"),
        "@number.float": st("syntax.number"), "@type": typ, "@type.builtin": replace(typ, italic=True),
        "@type.definition": typ, "@attribute": st("syntax.attribute"), "@function": function,
        "@function.builtin": replace(function, italic=True), "@function.call": function,
        "@function.macro": st("syntax.macro"), "@function.method": function, "@function.method.call": function,
        "@constructor": st("syntax.constructor"), "@operator": st("syntax.operator"),
        "@keyword": keyword, "@keyword.function": keyword, "@keyword.operator": S(keyword.fg),
        "@keyword.import": keyword, "@keyword.type": keyword, "@keyword.modifier": keyword,
        "@keyword.repeat": keyword, "@keyword.return": replace(keyword, bold=True), "@keyword.exception": keyword,
        "@keyword.conditional": keyword, "@keyword.coroutine": keyword,
        "@punctuation.delimiter": st("syntax.punctuation"), "@punctuation.bracket": st("syntax.punctuation"),
        "@punctuation.special": st("syntax.escape"),
        "@comment": comment, "@comment.documentation": comment,
        "@comment.todo": st("syntax.todo"), "@comment.note": st("syntax.note"),
        "@comment.warning": S(bg, s.resolve("diagnostic.warning"), bold=True),
        "@comment.error": S(bg, s.resolve("diagnostic.error"), bold=True),
        "@tag": st("syntax.tag"), "@tag.attribute": replace(typ, italic=True), "@tag.delimiter": st("syntax.punctuation"),
        "@markup.heading": replace(function, bold=True),
        "@diff.plus": S(s.resolve("git.add")), "@diff.minus": S(s.resolve("git.delete")),
        "@diff.delta": S(s.resolve("git.change")),
    }


CORE_SECTIONS: tuple[Callable[[Scheme], Groups], ...] = (_editor_ui, _vim_syntax, _diagnostics, _git, _treesitter)


def plugin_sections() -> list[Callable[[Scheme], Groups]]:
    """``groups`` functions of every module in ``cstools.highlights.plugins``, sorted by module name."""
    names = sorted(m.name for m in pkgutil.iter_modules(plugins.__path__) if not m.name.startswith("_"))
    return [importlib.import_module(f"{plugins.__name__}.{n}").groups for n in names]


def build_groups(scheme: Scheme) -> Groups:
    """Every highlight group of the template, resolved for ``scheme``."""
    out: Groups = {}
    for section in (*CORE_SECTIONS, *plugin_sections()):
        out.update(section(scheme))
    return out
