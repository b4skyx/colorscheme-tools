"""Theme-repository configuration (``colorschemes.toml``) and build orchestration."""
from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from .scheme.io import from_dict
from .scheme.model import Scheme
from .scheme.validate import validate
from .targets import REGISTRY, RenderContext

CONFIG_NAME = "colorschemes.toml"
SCHEME_FILE = "colorschemes.json"
Warn = Callable[[str], None]


class ProjectError(Exception):
    """Invalid project configuration, invalid scheme or conflicting target output."""


@dataclass(frozen=True)
class ProjectConfig:
    """Contents of ``colorschemes.toml``."""

    name: str = ""
    lua_module: str = ""
    url: str = ""
    schemes: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)

    def context(self, warn: Warn | None = None) -> RenderContext:
        """Render context for this project, sharing the build's warning channel."""
        return RenderContext(project_name=self.name, lua_module=self.lua_module, url=self.url,
                             warn=_stderr_warn if warn is None else warn)


def _stderr_warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def load_config(repo: str | Path) -> ProjectConfig:
    """Read ``<repo>/colorschemes.toml``."""
    path = Path(repo) / CONFIG_NAME
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise ProjectError(f"{path} not found") from None
    except tomllib.TOMLDecodeError as e:
        raise ProjectError(f"{path}: {e}") from None
    project, build = data.get("project", {}), data.get("build", {})
    return ProjectConfig(name=project.get("name", ""), lua_module=project.get("lua_module", ""),
                         url=project.get("url", ""), schemes=list(build.get("schemes", [])),
                         targets=list(build.get("targets", [])))


def load_scheme(path: str | Path) -> Scheme:
    """Load and validate one ``colorschemes.json``; raises ``ProjectError`` listing every problem."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise ProjectError(f"{path}: {e}") from None
    errors = validate(data)
    if errors:
        raise ProjectError(f"{path}: invalid scheme:\n  " + "\n  ".join(errors))
    return from_dict(data)


def render_repo(repo: str | Path, targets: Sequence[str] | None = None, schemes: Sequence[str] | None = None,
                warn: Warn = _stderr_warn) -> dict[str, str]:
    """Render the selected (default: configured) targets for the selected schemes → ``{relative_path: text}``.

    Explicitly requested unknown targets are errors; configured targets that are not registered only warn.
    """
    repo = Path(repo)
    config = load_config(repo)
    if targets is None:
        names = []
        for name in config.targets:
            if name in REGISTRY:
                names.append(name)
            else:
                warn(f"target {name!r} from {CONFIG_NAME} is not available in this version; skipped")
    else:
        unknown = [t for t in targets if t not in REGISTRY]
        if unknown:
            raise ProjectError("unknown targets: " + ", ".join(unknown))
        names = list(targets)
    ids = list(schemes) if schemes is not None else config.schemes
    loaded = [load_scheme(repo / sid / SCHEME_FILE) for sid in ids]
    for sid, scheme in zip(ids, loaded):
        if scheme.id != sid:
            raise ProjectError(f"{sid}/{SCHEME_FILE} declares id {scheme.id!r}")
    ctx = config.context(warn)
    files: dict[str, str] = {}
    owner: dict[str, str] = {}
    for name in names:
        target = REGISTRY[name]
        outputs = [target.render_project(loaded, ctx)] if target.scope == "project" else \
            [target.render(s, ctx) for s in loaded]
        for out in outputs:
            for rel, text in out.items():
                if rel in owner:
                    raise ProjectError(f"{rel} produced by both {owner[rel]!r} and {name!r}")
                owner[rel] = name
                files[rel] = text
    return files


def build(repo: str | Path, targets: Sequence[str] | None = None, schemes: Sequence[str] | None = None,
          check: bool = False, warn: Warn = _stderr_warn) -> list[str]:
    """Render and write files under ``repo``; return the sorted relative paths that changed.

    With ``check`` nothing is written and the paths that *would* change are returned.
    """
    repo = Path(repo)
    changed = []
    for rel, text in sorted(render_repo(repo, targets, schemes, warn).items()):
        path = repo / rel
        try:
            current = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = None
        if current == text:
            continue
        changed.append(rel)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    return changed
