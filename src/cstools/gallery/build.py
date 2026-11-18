"""Build deterministic gallery data; samples and rendering live in the HTML asset."""
from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any

from ..color.spaces import is_hex
from ..highlights.groups import build_groups
from ..project import ProjectError, load_config, load_scheme
from ..scheme.model import STYLE_COLORS, STYLE_FLAGS, Scheme
from ..score.editor import score_groups
from ..score.terminal import score_palette, score_terminal
from ..vision.model import DEFAULT, VisionModel


def _scheme_data(scheme: Scheme, model: VisionModel) -> dict[str, Any]:
    groups = {name: style.to_dict() for name, style in build_groups(scheme).items()}
    score, score_roles = score_groups(groups, model.matrix)
    return {
        "id": scheme.id, "name": scheme.name, "kind": "scheme", "variant": scheme.variant,
        "family": scheme.family, "group": scheme.family, "description": scheme.description,
        "tags": scheme.tags, "groups": groups, "terminal": [scheme.ansi(i) for i in range(16)],
        "terminal_background": scheme.terminal_color("background"),
        "terminal_foreground": scheme.terminal_color("foreground"),
        "score": score, "term_score": score_terminal(scheme, model), "score_roles": score_roles,
        "roles": {f"{section}.{name}": scheme.style(f"{section}.{name}").fg
                  for section, block in scheme.roles.items() for name in block},
    }


def _dump_data(path: Path, model: VisionModel) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("groups"), dict):
        raise ValueError(f"{path}: expected a Neovim dump with a groups map")
    groups = data["groups"]
    for name, style in groups.items():
        if not isinstance(style, dict):
            raise ValueError(f"{path}: invalid highlight style for {name}")
        for key in STYLE_COLORS:
            if style.get(key) is not None and not is_hex(style[key]):
                raise ValueError(f"{path}: invalid {key} colour for {name}")
        for key in STYLE_FLAGS:
            if key in style and not isinstance(style[key], bool):
                raise ValueError(f"{path}: invalid {key} flag for {name}")
    normal = groups.get("Normal", {})
    if not normal.get("fg") or not normal.get("bg"):
        raise ValueError(f"{path}: Normal must have foreground and background colours")
    score, roles = score_groups(groups, model.matrix)
    # Like the prototype, fill missing terminal entries from the dump's editor roles.
    fallback = [roles["bg"], roles["err"], roles["add"], roles["warn"], roles["function"],
                roles["keyword"], roles["type"], roles["text"], roles["comment"], roles["err"],
                roles["add"], roles["warn"], roles["function"], roles["keyword"], roles["type"], roles["text"]]
    raw_terminal = data.get("terminal")
    # An empty Lua table is encoded as an object by some Neovim versions.
    if raw_terminal is None or raw_terminal == {}:
        raw_terminal = []
    if not isinstance(raw_terminal, list) or len(raw_terminal) > 16:
        raise ValueError(f"{path}: terminal must be a list of up to 16 colours")
    terminal = []
    for i in range(16):
        value = raw_terminal[i] if i < len(raw_terminal) else None
        if value is not None and not is_hex(value):
            raise ValueError(f"{path}: invalid terminal colour at index {i}")
        terminal.append(value or fallback[i] or normal["fg"])
    variant = data.get("background", "dark")
    if variant not in ("dark", "light"):
        raise ValueError(f"{path}: background must be dark or light")
    name = data.get("name", path.stem)
    if not isinstance(name, str):
        raise ValueError(f"{path}: name must be text")
    return {
        "id": f"comparison:{path.stem}", "name": name, "kind": "comparison", "variant": variant,
        "family": path.stem, "group": "Comparison themes", "description": "", "tags": [],
        "groups": groups, "terminal": terminal,
        "terminal_background": normal["bg"], "terminal_foreground": normal["fg"],
        "terminal_inferred": any(i >= len(raw_terminal) or not raw_terminal[i] for i in range(16)),
        "score": score, "score_roles": roles,
        "term_score": score_palette(dict(enumerate(terminal)), normal["bg"], normal["fg"], model.matrix),
    }


def gallery_data(repo: str | Path, extra_dumps: str | Path | None = None,
                 model: VisionModel = DEFAULT) -> dict[str, Any]:
    """Read configured schemes and comparison dumps into a JSON-compatible payload.

    Family order follows the repository configuration, with dark/light counterparts adjacent.
    Comparison IDs are namespaced so a dump can share a configured scheme's filename.
    """
    repo = Path(repo)
    config = load_config(repo)
    schemes = []
    for sid in config.schemes:
        scheme = load_scheme(repo / sid / "colorschemes.json")
        if scheme.id != sid:
            raise ProjectError(f"{sid}/colorschemes.json declares id {scheme.id!r}")
        schemes.append(_scheme_data(scheme, model))
    families = list(dict.fromkeys(s["family"] for s in schemes))
    schemes.sort(key=lambda s: (families.index(s["family"]), s["variant"] != "dark", s["id"]))
    if extra_dumps is not None:
        directory = Path(extra_dumps)
        if not directory.is_dir():
            raise ValueError(f"{directory}: comparison dump directory not found")
        schemes.extend(_dump_data(path, model) for path in sorted(directory.glob("*.json")))
    return {"project": config.name,
            "model": {"type": model.type, "severity": model.severity, "matrix": model.matrix},
            "schemes": schemes}


def build_gallery(repo: str | Path, output: str | Path, extra_dumps: str | Path | None = None,
                  model: VisionModel = DEFAULT) -> list[Path]:
    """Write ``index.html`` and ``gallery_data.js`` under output; return their paths.

    The data is a script assignment rather than a fetch response so the gallery works via file://.
    """
    data = gallery_data(repo, extra_dumps, model)
    assets = files("cstools.gallery").joinpath("assets")
    rendered = {"index.html": assets.joinpath("gallery.html").read_text(encoding="utf-8"),
                "gallery_data.js": "window.GALLERY_DATA = " + json.dumps(
                    data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + ";\n"}
    root = Path(output)
    root.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in rendered.items():
        path = root / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths
