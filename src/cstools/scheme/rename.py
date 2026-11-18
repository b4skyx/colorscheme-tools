"""Rename palette base colours and rewrite every reference to them.

Renaming never changes a resolved colour: only palette keys and the references in ``derived``,
``roles`` and ``terminal`` change. UI role names (``bg``, ``fg``, …) are kept as they are.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from .defaults import DEFAULT_DERIVED
from .expr import SchemeError
from .model import UI_ROLES, Scheme
from .naming import name_colors


def auto_names(scheme: Scheme) -> dict[str, str]:
    """Old → new palette names using the current naming rules (UI role names are fixed)."""
    fixed = {name for name in scheme.palette if name in UI_ROLES}
    free = {name: hexv for name, hexv in scheme.palette.items() if name not in fixed}
    by_hex = name_colors(free.values())
    return {name: (name if name in fixed else by_hex[hexv.lower()]) for name, hexv in scheme.palette.items()}


def _rewrite(value: Any, mapping: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return mapping.get(value, value)       # role paths ("syntax.type") and unknown names pass through
    if isinstance(value, list):
        return [_rewrite(v, mapping) for v in value]
    if isinstance(value, dict):
        return {k: _rewrite(v, mapping) for k, v in value.items()}
    return value                               # numbers, booleans


def rename_palette(scheme: Scheme, mapping: Mapping[str, str] | None = None) -> Scheme:
    """Return a copy of ``scheme`` with palette keys renamed (``mapping`` defaults to ``auto_names``)."""
    mapping = dict(mapping or auto_names(scheme))
    new_names = list(mapping.values())
    if len(set(new_names)) != len(new_names):
        raise SchemeError(f"rename would merge palette colours: {sorted(n for n in new_names if new_names.count(n) > 1)}")
    taken = (set(scheme.derived) | set(DEFAULT_DERIVED)) - set(mapping)
    clash = sorted(set(new_names) & taken)
    if clash:
        raise SchemeError(f"new palette names collide with derived colours: {clash}")
    palette = {mapping.get(k, k): v for k, v in scheme.palette.items()}
    return replace(scheme, palette=palette, derived=_rewrite(scheme.derived, mapping),
                   roles=_rewrite(scheme.roles, mapping), terminal=_rewrite(scheme.terminal, mapping))
