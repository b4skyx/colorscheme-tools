"""Schema v1 → v2 migration.

v1 files store resolved hexes for every palette entry, terminal colour and highlight group. Migration
keeps the base colours, accents, italic choices and ANSI colours and rebuilds everything else through
``assemble_scheme``, so derived colours become formulas again.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from .assemble import ACCENT_KEYS, assemble_scheme
from .expr import SchemeError
from .model import ANSI_NAMES, UI_ROLES, Scheme

#: Tags that describe a person rather than the scheme; never carried over.
PERSONAL_TAGS = frozenset({"favourite", "favorite"})
RECIPE_META_KEYS = ("name", "family", "description", "tags", "variant")


def read_recipe_metadata(path: str | Path) -> dict[str, Any]:
    """Metadata fields (name, family, description, tags, variant) of a ``recipe.toml``."""
    with open(path, "rb") as f:
        recipe = tomllib.load(f)
    return {k: recipe[k] for k in RECIPE_META_KEYS if k in recipe}


def _designed_for(v1: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(str(v1.get(k, "")) for k in ("simulation", "vision")).lower()
    vision = next((t for t in ("deutan", "protan", "tritan") if t in text), "deutan")
    m = re.search(r"severity\s*([0-9.]+)", text)
    out: dict[str, Any] = {"vision": vision, "severity": float(m.group(1)) if m else 1.0}
    if "metric" in v1:
        out["metric"] = v1["metric"]
    return out


def _italic(highlights: dict[str, Any], group: str) -> bool:
    return bool(highlights.get(group, {}).get("italic"))


def migrate_v1(data: dict[str, Any], recipe_meta: dict[str, Any] | None = None) -> Scheme:
    """Convert a parsed v1 scheme; ``recipe_meta`` (see ``read_recipe_metadata``) overrides metadata."""
    if data.get("$schema_version") != 1:
        raise SchemeError(f"not a schema v1 file ($schema_version = {data.get('$schema_version')!r})")
    hexes = {k: v["hex"] for k, v in data["palette"].items()}
    missing = [k for k in UI_ROLES + ACCENT_KEYS if k not in hexes]
    if missing:
        raise SchemeError("v1 palette lacks: " + ", ".join(missing))
    highlights = data.get("highlights", {})
    meta: dict[str, Any] = {
        "id": data["id"], "name": data["name"], "variant": data.get("variant", "dark"),
        "family": data["id"].removesuffix("-light"), "description": data.get("description", ""),
        "tags": [t for t in data.get("tags", []) if t not in PERSONAL_TAGS],
        "designed_for": _designed_for(data.get("designed_for", {})),
    }
    if recipe_meta:
        meta.update(recipe_meta)
        meta["tags"] = [t for t in meta["tags"] if t not in PERSONAL_TAGS]
    styles = {
        "comment_italic": _italic(highlights, "Comment"),
        "keyword_italic": _italic(highlights, "@keyword"),
        "parameter_italic": _italic(highlights, "@variable.parameter"),
    }
    term = data["terminal"]
    return assemble_scheme(
        meta, {k: hexes[k] for k in UI_ROLES}, {k: hexes[k] for k in ACCENT_KEYS}, styles,
        {k: term["normal"][k] for k in ANSI_NAMES}, {k: term["bright"][k] for k in ANSI_NAMES})
