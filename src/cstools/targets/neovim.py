"""Project-level Neovim theme data and the packaged Lua runtime."""
from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, Sequence

from ..highlights.groups import build_groups
from ..scheme.defaults import DEFAULT_DERIVED
from ..scheme.model import Scheme
from .base import RenderContext, Target, register


def lua_value(value: Any, level: int = 0) -> str:
    """Serialize theme data as deterministic Lua tables (including capture-name keys)."""
    if isinstance(value, str):
        text = json.dumps(value, ensure_ascii=False)
        # JSON's Unicode control escapes are not Lua string escapes.
        for code in range(32):
            text = text.replace(f"\\u{code:04x}", f"\\{code:03d}")
        return text
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "nil"
    if isinstance(value, dict):
        entries = [f"[{lua_value(k)}] = {lua_value(v, level + 1)}" for k, v in sorted(value.items())]
    elif isinstance(value, (list, tuple)):
        entries = [lua_value(v, level + 1) for v in value]
    else:
        return str(value)
    if not entries:
        return "{}"
    indent = "  " * (level + 1)
    return "{\n" + ",\n".join(indent + e for e in entries) + ",\n" + "  " * level + "}"


@register
class Neovim(Target):
    """Render all groups as Lua data, plus setup/load/palette runtime functions."""

    name = "neovim"
    scope = "project"
    description = "Neovim Lua themes and configurable runtime"

    def render_project(self, schemes: Sequence[Scheme], ctx: RenderContext) -> dict[str, str]:
        module = ctx.lua_module or ctx.project_name
        if not module:
            raise ValueError("neovim requires a lua_module or project_name")
        root = f"lua/{module.replace('.', '/')}"
        out = {}
        for name in ("init.lua", "config.lua"):
            runtime = files(__package__).joinpath("neovim_runtime", name).read_text(encoding="utf-8")
            out[f"{root}/{name}"] = ctx.header("--") + runtime.replace("@MODULE@", module)
        for scheme in schemes:
            palette = {key: scheme.resolve(key) for key in sorted(
                set(scheme.palette) | set(DEFAULT_DERIVED) | set(scheme.derived))}
            data = {"name": scheme.name, "id": scheme.id, "variant": scheme.variant, "palette": palette,
                    "groups": {k: v.to_dict() for k, v in build_groups(scheme).items()},
                    "terminal": [scheme.ansi(i) for i in range(16)]}
            out[f"{root}/themes/{scheme.id}.lua"] = ctx.header("--", scheme) + "return " + lua_value(data) + "\n"
        return out
