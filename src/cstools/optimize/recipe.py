"""Optimiser input: ``recipe.toml`` → ``Recipe``.

A recipe fixes the UI base colours, italic choices and design anchors for the accent roles, plus the
search limits for the editor and terminal optimisers.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping

from ..scheme.assemble import ACCENT_KEYS, STYLE_KEYS
from ..scheme.model import UI_ROLES

VARIANTS = ("dark", "light")


@dataclass(frozen=True)
class EditorSettings:
    """Limits for the editor-role search (``[editor]``) and the accent anchors (``[editor.anchors]``)."""

    contrast_min: float
    chroma_max: float
    hue_tolerance: float
    anchors: dict[str, str]
    lightness_min: float = 0.60
    lightness_max: float = 0.88


@dataclass(frozen=True)
class TerminalSettings:
    """Limits for the ANSI search (``[terminal]``)."""

    contrast_min: float
    chroma_max: float
    lightness_min: float
    lightness_max: float


@dataclass(frozen=True)
class OptimizerSettings:
    """Search budget and seeds (``[optimizer]``)."""

    seed: int = 1
    iterations: int = 5000
    restarts: int = 3
    terminal_seed: int = 7
    terminal_iterations: int = 6000


@dataclass(frozen=True)
class Recipe:
    """A parsed ``recipe.toml``."""

    id: str
    name: str
    variant: str
    family: str
    description: str
    tags: list[str]
    base: dict[str, str]
    styles: dict[str, bool]
    editor: EditorSettings
    terminal: TerminalSettings
    optimizer: OptimizerSettings = field(default_factory=OptimizerSettings)

    @property
    def is_light(self) -> bool:
        """True for light variants."""
        return self.variant == "light"

    def with_budget(self, iterations: int | None = None, seed: int | None = None) -> "Recipe":
        """Copy with the editor and terminal iteration counts and/or both seeds overridden."""
        opt = self.optimizer
        if iterations is not None:
            opt = replace(opt, iterations=iterations, terminal_iterations=iterations)
        if seed is not None:
            opt = replace(opt, seed=seed, terminal_seed=seed)
        return replace(self, optimizer=opt)


def _section(data: Mapping[str, Any], key: str, label: str | None = None) -> Mapping[str, Any]:
    value = data.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"recipe: missing [{label or key}] section")
    return value


def _require(section: Mapping[str, Any], name: str, keys: tuple[str, ...]) -> None:
    missing = [k for k in keys if k not in section]
    if missing:
        raise ValueError(f"recipe: [{name}] lacks " + ", ".join(missing))


def recipe_from_dict(data: Mapping[str, Any]) -> Recipe:
    """Build a ``Recipe`` from parsed TOML; raises ``ValueError`` on missing or invalid fields."""
    _require(data, "top level", ("id", "name"))
    variant = data.get("variant", "dark")
    if variant not in VARIANTS:
        raise ValueError(f"recipe: variant must be one of {', '.join(VARIANTS)}, got {variant!r}")
    base, editor, terminal = _section(data, "base"), _section(data, "editor"), _section(data, "terminal")
    anchors = _section(editor, "anchors", "editor.anchors")
    _require(base, "base", UI_ROLES)
    _require(editor, "editor", ("contrast_min", "chroma_max", "hue_tolerance"))
    _require(anchors, "editor.anchors", ACCENT_KEYS)
    _require(terminal, "terminal", ("contrast_min", "chroma_max", "lightness_min", "lightness_max"))
    styles = data.get("styles", {})
    editor_limits = {k: float(editor[k]) for k in ("lightness_min", "lightness_max") if k in editor}
    known_opt = ("seed", "iterations", "restarts", "terminal_seed", "terminal_iterations")
    return Recipe(
        id=data["id"], name=data["name"], variant=variant, family=data.get("family", data["id"]),
        description=data.get("description", ""), tags=list(data.get("tags", [])),
        base={k: base[k].lower() for k in UI_ROLES},
        styles={k: bool(styles.get(k, False)) for k in STYLE_KEYS},
        editor=EditorSettings(contrast_min=float(editor["contrast_min"]), chroma_max=float(editor["chroma_max"]),
                              hue_tolerance=float(editor["hue_tolerance"]),
                              anchors={k: anchors[k].lower() for k in ACCENT_KEYS}, **editor_limits),
        terminal=TerminalSettings(**{k: float(terminal[k]) for k in
                                     ("contrast_min", "chroma_max", "lightness_min", "lightness_max")}),
        optimizer=OptimizerSettings(**{k: int(v) for k, v in data.get("optimizer", {}).items() if k in known_opt}),
    )


def load_recipe(path: str | Path) -> Recipe:
    """Read and parse a ``recipe.toml``."""
    with open(path, "rb") as f:
        return recipe_from_dict(tomllib.load(f))
