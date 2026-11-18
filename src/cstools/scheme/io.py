"""Load and dump ``colorschemes.json`` (schema_version 2) with a stable key order."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .expr import SchemeError
from .model import Scheme

SCHEMA_VERSION = 2
KEY_ORDER = ("schema_version", "id", "name", "variant", "family", "description", "tags", "designed_for",
             "palette", "derived", "roles", "terminal")
ROLE_ORDER = ("ui", "syntax", "diagnostic", "git")


def from_dict(data: dict[str, Any]) -> Scheme:
    """Build a ``Scheme`` from parsed JSON (structure only; use ``validate`` for full checks)."""
    if data.get("schema_version") != SCHEMA_VERSION:
        raise SchemeError(f"expected schema_version {SCHEMA_VERSION}, got {data.get('schema_version')!r}")
    missing = [k for k in ("id", "name", "variant", "palette", "roles", "terminal") if k not in data]
    if missing:
        raise SchemeError("missing keys: " + ", ".join(missing))
    extra = {k: v for k, v in data.items() if k not in KEY_ORDER}
    return Scheme(
        id=data["id"], name=data["name"], variant=data["variant"], family=data.get("family", data["id"]),
        description=data.get("description", ""), tags=list(data.get("tags", [])),
        designed_for=dict(data.get("designed_for", {})), palette=dict(data["palette"]),
        derived=dict(data.get("derived", {})), roles=data["roles"], terminal=data["terminal"], extra=extra)


def to_dict(scheme: Scheme) -> dict[str, Any]:
    """Serialisable dict in canonical key order (``$schema`` first when present; empty ``derived`` omitted)."""
    out: dict[str, Any] = {}
    if "$schema" in scheme.extra:
        out["$schema"] = scheme.extra["$schema"]
    out.update({
        "schema_version": SCHEMA_VERSION, "id": scheme.id, "name": scheme.name, "variant": scheme.variant,
        "family": scheme.family, "description": scheme.description, "tags": list(scheme.tags),
        "designed_for": scheme.designed_for, "palette": scheme.palette,
    })
    if scheme.derived:
        out["derived"] = scheme.derived
    roles = {k: scheme.roles[k] for k in ROLE_ORDER if k in scheme.roles}
    roles.update({k: v for k, v in scheme.roles.items() if k not in roles})
    out["roles"] = roles
    out["terminal"] = scheme.terminal
    out.update({k: v for k, v in scheme.extra.items() if k != "$schema"})
    return out


def loads(text: str) -> Scheme:
    """Parse JSON text."""
    return from_dict(json.loads(text))


def load(path: str | Path) -> Scheme:
    """Read a ``colorschemes.json`` file."""
    return loads(Path(path).read_text(encoding="utf-8"))


def dumps(scheme: Scheme) -> str:
    """JSON text, 2-space indent, UTF-8 characters kept, trailing newline."""
    return json.dumps(to_dict(scheme), indent=2, ensure_ascii=False) + "\n"


def dump(scheme: Scheme, path: str | Path) -> None:
    """Write a ``colorschemes.json`` file."""
    Path(path).write_text(dumps(scheme), encoding="utf-8")
