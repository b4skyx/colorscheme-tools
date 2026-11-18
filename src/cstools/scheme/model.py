"""Scheme model and reference resolution."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

from ..color.spaces import is_hex
from .defaults import DEFAULT_DERIVED, DIAGNOSTIC_ROLES
from .expr import ColorValue, SchemeError, evaluate, references

UI_ROLES = ("bg", "bg_alt", "fg", "fg_dim", "comment")
SYNTAX_ROLES = ("variable", "comment", "keyword", "function", "string", "type", "constant", "number", "boolean",
                "property", "parameter", "builtin", "operator", "punctuation", "module", "attribute", "tag", "escape",
                "regex", "macro", "constructor", "label", "todo", "note")
GIT_ROLES = ("add", "change", "delete")
ROLE_GROUPS: dict[str, tuple[str, ...]] = {"ui": UI_ROLES, "syntax": SYNTAX_ROLES, "diagnostic": DIAGNOSTIC_ROLES,
                                           "git": GIT_ROLES}
STYLE_COLORS = ("fg", "bg", "sp")
STYLE_FLAGS = ("bold", "italic", "underline", "undercurl", "strikethrough", "reverse")
ANSI_NAMES = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
TERMINAL_KEYS = ("background", "foreground", "cursor", "cursor_text", "selection_background", "selection_foreground")


@dataclass(frozen=True)
class ResolvedStyle:
    """A highlight style with every colour resolved to hex (``None`` = unset)."""

    fg: str | None = None
    bg: str | None = None
    sp: str | None = None
    bold: bool = False
    italic: bool = False
    underline: bool = False
    undercurl: bool = False
    strikethrough: bool = False
    reverse: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Only the set attributes: colours that are not ``None`` and flags that are true."""
        return {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name)}


@dataclass
class Scheme:
    """One colourscheme (schema_version 2). Colours are references resolved on demand."""

    id: str
    name: str
    variant: str
    family: str
    description: str
    tags: list[str]
    designed_for: dict[str, Any]
    palette: dict[str, str]
    derived: dict[str, ColorValue]
    roles: dict[str, dict[str, Any]]
    terminal: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)  # unknown top-level keys such as "$schema", kept on dump

    @property
    def is_light(self) -> bool:
        """True for light variants (``raise`` darkens)."""
        return self.variant == "light"

    def resolve(self, value: ColorValue) -> str:
        """Resolve a name, role path (``"syntax.type"``) or expression to hex."""
        return self._evaluate(value, ())

    def style(self, role_path: str) -> ResolvedStyle:
        """Resolve a role to a style; colour-only roles (``"diagnostic.error"``) become ``fg``."""
        group, role = self._split_path(role_path)
        raw = self._role_value(group, role)
        stack = (role_path,)
        if not isinstance(raw, dict) or not any(k in raw for k in STYLE_COLORS + STYLE_FLAGS):
            return ResolvedStyle(fg=self._evaluate(raw, stack))
        colours = {k: self._evaluate(raw[k], stack) for k in STYLE_COLORS if raw.get(k) is not None}
        return ResolvedStyle(**colours, **{k: bool(raw.get(k, False)) for k in STYLE_FLAGS})

    def terminal_color(self, key: str) -> str:
        """Resolve a top-level terminal entry such as ``"background"`` or ``"selection_background"``."""
        if key not in self.terminal or key in ("normal", "bright"):
            raise SchemeError(f"unknown terminal colour {key!r}")
        return self.resolve(self.terminal[key])

    def ansi(self, i: int) -> str:
        """ANSI colour 0..15 (0–7 normal, 8–15 bright)."""
        if not 0 <= i < 16:
            raise SchemeError(f"ANSI index out of range: {i}")
        block = "normal" if i < 8 else "bright"
        return self.resolve(self.terminal[block][ANSI_NAMES[i % 8]])

    def palette_dependencies(self, value: ColorValue) -> set[str]:
        """Palette names a colour value ultimately depends on."""
        out: set[str] = set()
        self._collect(value, out, ())
        return out

    def palette_usage(self) -> dict[str, list[str]]:
        """Palette name → sorted roles, derived colours and terminal entries that depend on it."""
        usage: dict[str, set[str]] = {name: set() for name in self.palette}

        def note(site: str, value: ColorValue) -> None:
            for name in self.palette_dependencies(value):
                usage[name].add(site)

        for group, block in self.roles.items():
            for role, value in block.items():
                if isinstance(value, dict) and any(k in value for k in STYLE_COLORS):
                    for k in STYLE_COLORS:
                        if value.get(k) is not None:
                            note(f"{group}.{role}" + ("" if k == "fg" else f".{k}"), value[k])
                else:
                    note(f"{group}.{role}", value)
        for name in dict.fromkeys([*DEFAULT_DERIVED, *self.derived]):
            note(f"derived.{name}", name)
        for key in TERMINAL_KEYS:
            note(f"terminal.{key}", self.terminal[key])
        for block in ("normal", "bright"):
            for slot in ANSI_NAMES:
                note(f"terminal.{block}.{slot}", self.terminal[block][slot])
        return {name: sorted(sites) for name, sites in usage.items()}

    # internals ----------------------------------------------------------
    def _collect(self, value: ColorValue, out: set[str], stack: tuple[str, ...]) -> None:
        for ref in references(value):
            if ref in stack:
                raise SchemeError("reference cycle: " + " -> ".join(stack + (ref,)))
            if ref in self.palette:
                out.add(ref)
            elif "." in ref:
                group, role = self._split_path(ref)
                raw = self._role_value(group, role)
                self._collect(raw["fg"] if isinstance(raw, dict) and "fg" in raw else raw, out, stack + (ref,))
            elif ref in self.derived:
                self._collect(self.derived[ref], out, stack + (ref,))
            elif ref in DEFAULT_DERIVED:
                self._collect(DEFAULT_DERIVED[ref], out, stack + (ref,))

    def _evaluate(self, value: ColorValue, stack: tuple[str, ...]) -> str:
        return evaluate(value, lambda ref: self._lookup(ref, stack), self.is_light)

    def _lookup(self, ref: str, stack: tuple[str, ...]) -> str:
        if ref in stack:
            raise SchemeError("reference cycle: " + " -> ".join(stack + (ref,)))
        inner = stack + (ref,)
        if ref in self.palette:
            value = self.palette[ref]
            if not is_hex(value):
                raise SchemeError(f"palette colour {ref!r} must be a #rrggbb literal, got {value!r}")
            return value.lower()
        if "." in ref:
            group, role = self._split_path(ref)
            raw = self._role_value(group, role)
            if isinstance(raw, dict) and "fg" in raw:
                raw = raw["fg"]
            elif isinstance(raw, dict) and any(k in raw for k in STYLE_COLORS + STYLE_FLAGS):
                raise SchemeError(f"role {ref!r} has no fg colour")
            return self._evaluate(raw, inner)
        if ref in self.derived:
            return self._evaluate(self.derived[ref], inner)
        if ref in DEFAULT_DERIVED:
            return self._evaluate(DEFAULT_DERIVED[ref], inner)
        raise SchemeError(f"unknown colour reference {ref!r}")

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        group, sep, role = path.partition(".")
        if not sep or not role or "." in role:
            raise SchemeError(f"role path must look like 'group.role', got {path!r}")
        return group, role

    def _role_value(self, group: str, role: str) -> Any:
        try:
            return self.roles[group][role]
        except (KeyError, TypeError):
            raise SchemeError(f"unknown role {group}.{role}") from None
