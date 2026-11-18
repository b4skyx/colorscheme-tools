"""Shared test helpers: fixture paths, migrated fixtures and frozen reference outputs (parity only)."""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

from cstools.scheme.migrate import migrate_v1, read_recipe_metadata
from cstools.scheme.model import Scheme

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
SCHEME_IDS = ("haze", "fog", "abyss", "dusk")


def reference(name: str) -> Any:
    """Fresh parse of ``fixtures/parity/<name>.json``: frozen outputs of the original prototype scripts."""
    return json.loads((FIXTURES / "parity" / f"{name}.json").read_text(encoding="utf-8"))


def v1(sid: str) -> dict[str, Any]:
    """Parsed schema v1 fixture."""
    return json.loads((FIXTURES / "v1" / f"{sid}.json").read_text(encoding="utf-8"))


def recipe_path(sid: str) -> Path:
    return FIXTURES / "v1" / f"{sid}.recipe.toml"


@cache
def _migrated_json(sid: str) -> str:
    from cstools.scheme import io
    return io.dumps(migrate_v1(v1(sid), read_recipe_metadata(recipe_path(sid))))


def migrated(sid: str) -> Scheme:
    """Fresh v2 scheme migrated from the v1 fixture (with recipe metadata)."""
    from cstools.scheme import io
    return io.loads(_migrated_json(sid))


def v1_highlights(sid: str) -> dict[str, dict[str, Any]]:
    """v1 highlight groups flattened to ``{group: {fg/bg/sp: hex, flag: True}}``."""
    out = {}
    for group, entry in v1(sid)["highlights"].items():
        out[group] = {k: (v["hex"] if isinstance(v, dict) else v) for k, v in entry.items()}
    return out


def write_repo(root: Path, targets: list[str], schemes: tuple[str, ...] = SCHEME_IDS) -> Path:
    """Create a minimal theme repository with migrated fixtures under ``root``."""
    from cstools.scheme import io
    for sid in schemes:
        (root / sid).mkdir(parents=True, exist_ok=True)
        io.dump(migrated(sid), root / sid / "colorschemes.json")
    quoted = ", ".join(f'"{t}"' for t in targets)
    ids = ", ".join(f'"{s}"' for s in schemes)
    (root / "colorschemes.toml").write_text(
        f'[project]\nname = "demo"\nlua_module = "demo"\nurl = ""\n\n[build]\nschemes = [{ids}]\ntargets = [{quoted}]\n',
        encoding="utf-8")
    return root


def strip_header(text: str) -> str:
    """Drop the leading comment block (header lines) of a generated file."""
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith("#"):
        i += 1
    return "".join(lines[i:])
