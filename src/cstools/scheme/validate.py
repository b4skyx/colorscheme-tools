"""Structural and reference validation of schema_version 2 schemes (mirrors schema/colorscheme.schema.json)."""
from __future__ import annotations

import re
from typing import Any

from ..color.spaces import is_hex
from ..vision.model import VISION_TYPES
from .defaults import DEFAULT_DERIVED
from .expr import SchemeError, check_shape
from .io import KEY_ORDER, SCHEMA_VERSION, from_dict
from .model import ANSI_NAMES, ROLE_GROUPS, STYLE_COLORS, STYLE_FLAGS, TERMINAL_KEYS, Scheme

NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
TOP_TYPES: dict[str, type | tuple[type, ...]] = {
    "schema_version": int, "id": str, "name": str, "variant": str, "family": str, "description": str, "tags": list,
    "designed_for": dict, "palette": dict, "derived": dict, "roles": dict, "terminal": dict}
REQUIRED = ("schema_version", "id", "name", "variant", "palette", "roles", "terminal")


def _literals(value: Any) -> bool:
    """True if a colour value contains a hex literal anywhere."""
    if isinstance(value, str):
        return is_hex(value)
    if isinstance(value, dict):
        return any(_literals(a) for args in value.values() if isinstance(args, list) for a in args)
    return False


def _check_value(where: str, value: Any, errors: list[str]) -> None:
    try:
        check_shape(value)
    except SchemeError as e:
        errors.append(f"{where}: {e}")
        return
    if _literals(value):
        errors.append(f"{where}: hex literals are only allowed in palette")


def _structure(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED:
        if key not in data:
            errors.append(f"missing required key {key!r}")
    for key, value in data.items():
        if key == "$schema":
            if not isinstance(value, str):
                errors.append("$schema must be a string")
        elif key not in KEY_ORDER:
            errors.append(f"unknown top-level key {key!r}")
        elif not isinstance(value, TOP_TYPES[key]) or (key == "schema_version" and isinstance(value, bool)):
            errors.append(f"{key} must be of type {TOP_TYPES[key].__name__}")
    if errors:
        return errors
    if data["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if data["variant"] not in ("dark", "light"):
        errors.append("variant must be 'dark' or 'light'")
    if not all(isinstance(t, str) for t in data.get("tags", [])):
        errors.append("tags must be strings")
    designed = data.get("designed_for", {})
    if "vision" in designed and designed["vision"] not in VISION_TYPES:
        errors.append(f"designed_for.vision must be one of {', '.join(VISION_TYPES)}")
    severity = designed.get("severity", 0)
    if isinstance(severity, bool) or not isinstance(severity, (int, float)) or not 0 <= severity <= 1:
        errors.append("designed_for.severity must be a number within 0..1")

    seen: dict[str, str] = {}
    for name, hexv in data["palette"].items():
        if not NAME_RE.match(name):
            errors.append(f"palette name {name!r} must match {NAME_RE.pattern}")
        if not is_hex(hexv):
            errors.append(f"palette.{name}: must be a #rrggbb literal, got {hexv!r}")
            continue
        if hexv.lower() in seen:
            errors.append(f"palette.{name}: duplicate of palette.{seen[hexv.lower()]} ({hexv})")
        seen.setdefault(hexv.lower(), name)

    for name, value in data.get("derived", {}).items():
        if not NAME_RE.match(name):
            errors.append(f"derived name {name!r} must match {NAME_RE.pattern}")
        if name in data["palette"]:
            errors.append(f"derived.{name}: shadows a palette colour")
        _check_value(f"derived.{name}", value, errors)

    roles = data["roles"]
    for group, names in ROLE_GROUPS.items():
        block = roles.get(group)
        if not isinstance(block, dict):
            errors.append(f"roles.{group} missing or not an object")
            continue
        for role in names:
            if role not in block:
                errors.append(f"roles.{group}.{role} missing")
        for role, value in block.items():
            where = f"roles.{group}.{role}"
            if role not in names:
                errors.append(f"{where}: unknown role")
            elif group == "syntax":
                if not isinstance(value, dict) or "fg" not in value:
                    errors.append(f"{where}: must be a style object with fg")
                    continue
                for k, v in value.items():
                    if k in STYLE_COLORS:
                        _check_value(f"{where}.{k}", v, errors)
                    elif k in STYLE_FLAGS:
                        if not isinstance(v, bool):
                            errors.append(f"{where}.{k}: must be a boolean")
                    else:
                        errors.append(f"{where}: unknown style key {k!r}")
            else:
                _check_value(where, value, errors)
    for group in roles:
        if group not in ROLE_GROUPS:
            errors.append(f"roles.{group}: unknown role group")

    term = data["terminal"]
    for key in TERMINAL_KEYS:
        if key not in term:
            errors.append(f"terminal.{key} missing")
        else:
            _check_value(f"terminal.{key}", term[key], errors)
    for block in ("normal", "bright"):
        colours = term.get(block)
        if not isinstance(colours, dict):
            errors.append(f"terminal.{block} missing or not an object")
            continue
        for slot in ANSI_NAMES:
            if slot not in colours:
                errors.append(f"terminal.{block}.{slot} missing")
            else:
                _check_value(f"terminal.{block}.{slot}", colours[slot], errors)
        errors.extend(f"terminal.{block}.{k}: unknown slot" for k in colours if k not in ANSI_NAMES)
    errors.extend(f"terminal.{k}: unknown key" for k in term if k not in TERMINAL_KEYS + ("normal", "bright"))
    return errors


def _references(scheme: Scheme) -> list[str]:
    errors: list[str] = []

    def attempt(where: str, fn: Any) -> None:
        try:
            fn()
        except SchemeError as e:
            errors.append(f"{where}: {e}")

    for name in list(scheme.derived) + [n for n in DEFAULT_DERIVED if n not in scheme.derived]:
        attempt(f"derived.{name}", lambda n=name: scheme.resolve(n))
    for group, block in scheme.roles.items():
        for role in block:
            attempt(f"roles.{group}.{role}", lambda p=f"{group}.{role}": scheme.style(p))
    for key in TERMINAL_KEYS:
        attempt(f"terminal.{key}", lambda k=key: scheme.terminal_color(k))
    for i in range(16):
        attempt(f"terminal ANSI {i}", lambda i=i: scheme.ansi(i))
    return errors


def validate(data: dict[str, Any]) -> list[str]:
    """Return a list of human-readable problems; empty means the scheme is valid."""
    if not isinstance(data, dict):
        return ["scheme must be a JSON object"]
    errors = _structure(data)
    if errors:
        return errors
    return _references(from_dict(data))
