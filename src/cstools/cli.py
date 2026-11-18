"""Command-line front-end (argparse only; logic lives in the library modules)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence, TextIO

from . import __version__
from .color.spaces import oklch_string
from .optimize.build import optimize_recipe
from .optimize.recipe import load_recipe
from .project import CONFIG_NAME, ProjectError, build, load_config, load_scheme
from .scheme import io
from .scheme.expr import SchemeError
from .scheme.migrate import migrate_v1, read_recipe_metadata
from .scheme.model import Scheme
from .scheme.validate import validate
from .score.editor import score_editor
from .score.terminal import score_terminal
from .targets import REGISTRY, RenderContext
from .vision.model import DEFAULT, VisionModel


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _context_for(scheme_path: str) -> RenderContext:
    """Project context when the scheme lives in ``<repo>/<id>/colorschemes.json`` next to a config."""
    repo = Path(scheme_path).resolve().parent.parent
    return load_config(repo).context() if (repo / CONFIG_NAME).exists() else RenderContext()


def _split(values: list[str] | None) -> list[str] | None:
    return None if values is None else [v for item in values for v in item.split(",") if v]


def cmd_validate(args: argparse.Namespace) -> int:
    failed = False
    for path in args.paths:
        try:
            data = _read_json(path)
        except (OSError, json.JSONDecodeError) as e:
            print(f"{path}: {e}", file=sys.stderr)
            failed = True
            continue
        if isinstance(data, dict) and data.get("$schema_version") == 1:
            errors = ["schema v1 file; convert it with `cstools migrate`"]
        else:
            errors = validate(data)
        if errors:
            failed = True
            print(f"{path}: {len(errors)} problem(s)", file=sys.stderr)
            for e in errors:
                print(f"  {e}", file=sys.stderr)
        else:
            print(f"{path}: ok")
    return 1 if failed else 0


def cmd_migrate(args: argparse.Namespace) -> int:
    meta = read_recipe_metadata(args.recipe) if args.recipe else None
    scheme = migrate_v1(_read_json(args.old), meta)
    errors = validate(io.to_dict(scheme))
    if errors:
        print("migrated scheme is invalid:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    if args.output:
        io.dump(scheme, args.output)
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(io.dumps(scheme))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    changed = build(args.repo, _split(args.targets), _split(args.schemes), check=args.check)
    verb = "would change" if args.check else "changed"
    for rel in changed:
        print(f"{verb}: {rel}")
    if not changed:
        print("up to date")
    return 1 if args.check and changed else 0


def cmd_render(args: argparse.Namespace) -> int:
    if args.target not in REGISTRY:
        print(f"unknown target {args.target!r}; see `cstools targets`", file=sys.stderr)
        return 2
    scheme, target, ctx = load_scheme(args.scheme), REGISTRY[args.target], _context_for(args.scheme)
    files = target.render_project([scheme], ctx) if target.scope == "project" else target.render(scheme, ctx)
    if args.out:
        for rel, text in sorted(files.items()):
            path = Path(args.out) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
        return 0
    for i, (rel, text) in enumerate(sorted(files.items())):
        if len(files) > 1:
            sys.stdout.write(("\n" if i else "") + f"==> {rel} <==\n")
        sys.stdout.write(text)
    return 0


def _scores(scheme: Scheme, model: VisionModel) -> dict[str, Any]:
    return {"model": {"type": model.type, "severity": model.severity},
            "editor": score_editor(scheme, model), "terminal": score_terminal(scheme, model)}


def _print_score_summary(scheme: Scheme, model: VisionModel, result: dict[str, Any], file: TextIO | None = None) -> None:
    out = file or sys.stdout
    e, t = result["editor"], result["terminal"]
    print(f"{scheme.name} ({model.type}, severity {model.severity})", file=out)
    worst = "≈".join(e["core_worst"]) if e["core_worst"] else "-"
    print(f"  editor:   kept {e['syntax_kept'] * 100:.0f}% ({e['syntax_lost']}/{e['syntax_pairs']} lost)  "
          f"core min {e['core_min']} ({worst})  err/warn {e['errwarn']}  add/del {e['add_del']}  "
          f"git min {e['git_min']}  fg/bg {e['fgbg']}", file=out)
    print(f"  terminal: normal min {t['minN']} ({t['worst']})  key {t['key']}  bright min {t['minB']}  "
          f"vs fg {t['fgSep']}  min contrast {t['read']}  fg/bg {t['fgbg']}", file=out)


def cmd_score(args: argparse.Namespace) -> int:
    scheme = load_scheme(args.scheme)
    model = VisionModel.from_dict(_read_json(args.model)) if args.model else DEFAULT
    result = _scores(scheme, model)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    _print_score_summary(scheme, model, result)
    return 0


def cmd_optimize(args: argparse.Namespace) -> int:
    recipe = load_recipe(args.recipe).with_budget(args.iterations, args.seed)
    scheme = optimize_recipe(recipe, DEFAULT)
    errors = validate(io.to_dict(scheme))
    if errors:
        print("optimised scheme is invalid:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1
    if args.output:
        io.dump(scheme, args.output)
        print(f"wrote {args.output}")
        _print_score_summary(scheme, DEFAULT, _scores(scheme, DEFAULT))
    else:
        sys.stdout.write(io.dumps(scheme))
        _print_score_summary(scheme, DEFAULT, _scores(scheme, DEFAULT), file=sys.stderr)
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    scheme = load_scheme(args.scheme)
    usage = scheme.palette_usage()
    if args.json:
        print(json.dumps({n: {"hex": scheme.palette[n], "used_by": u} for n, u in usage.items()}, indent=2))
        return 0
    width = max(len(n) for n in usage)
    for name, sites in usage.items():
        h = scheme.palette[name]
        print(f"{name:<{width}}  {h}  {oklch_string(h)}  {len(sites)} use(s)")
        for site in sites:
            print(f"{'':<{width}}    {site}")
        if not sites:
            print(f"{'':<{width}}    (unused)")
    return 0


def cmd_targets(args: argparse.Namespace) -> int:
    for name in sorted(REGISTRY):
        t = REGISTRY[name]
        print(f"{name:<12} {t.scope:<8} {t.description}")
    return 0


def cmd_not_implemented(args: argparse.Namespace) -> int:
    print(f"cstools {args.command}: not implemented yet", file=sys.stderr)
    return 2


def make_parser() -> argparse.ArgumentParser:
    """Argument parser for every subcommand."""
    p = argparse.ArgumentParser(prog="cstools", description="Create, convert and render colourschemes.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True, metavar="COMMAND")

    s = sub.add_parser("validate", help="schema, reference and cycle checks")
    s.add_argument("paths", nargs="+", metavar="PATH")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("migrate", help="convert a schema v1 file to v2")
    s.add_argument("old", metavar="OLD.json")
    s.add_argument("-o", "--output", metavar="NEW.json", help="output file (default: stdout); may equal OLD.json")
    s.add_argument("--recipe", metavar="RECIPE.toml", help="take name, family, description and tags from a recipe")
    s.set_defaults(func=cmd_migrate)

    s = sub.add_parser("optimize", help="optimise a recipe's editor roles and terminal into a v2 scheme")
    s.add_argument("recipe", metavar="RECIPE.toml")
    s.add_argument("-o", "--output", metavar="OUT.json", help="output file (default: stdout; scores go to stderr)")
    s.add_argument("--iterations", type=int, metavar="N", help="override editor and terminal iterations")
    s.add_argument("--seed", type=int, metavar="N", help="override editor and terminal seeds")
    s.set_defaults(func=cmd_optimize)

    s = sub.add_parser("build", help="render every configured target of a theme repository")
    s.add_argument("repo", metavar="REPO")
    s.add_argument("--targets", nargs="+", metavar="NAME", help="only these targets (space or comma separated)")
    s.add_argument("--schemes", nargs="+", metavar="ID", help="only these schemes (space or comma separated)")
    s.add_argument("--check", action="store_true", help="write nothing; exit 1 if any file would change")
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("render", help="print or write one target for one scheme")
    s.add_argument("scheme", metavar="SCHEME.json")
    s.add_argument("--target", required=True, metavar="NAME")
    s.add_argument("--out", metavar="DIR", help="write files below DIR instead of printing")
    s.set_defaults(func=cmd_render)

    s = sub.add_parser("score", help="colour-vision separation scores")
    s.add_argument("scheme", metavar="SCHEME.json")
    s.add_argument("--model", metavar="MODEL.json", help='vision model, e.g. {"type": "protan", "severity": 0.8}')
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("inspect", help="palette usage per base colour")
    s.add_argument("scheme", metavar="SCHEME.json")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_inspect)

    s = sub.add_parser("targets", help="list registered targets")
    s.set_defaults(func=cmd_targets)

    s = sub.add_parser("gallery", help="HTML gallery (not implemented yet)")
    s.add_argument("repo", metavar="REPO")
    s.add_argument("-o", "--output", metavar="DIR")
    s.add_argument("--extra-dumps", metavar="DIR")
    s.set_defaults(func=cmd_not_implemented)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    args = make_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ProjectError, SchemeError, OSError, json.JSONDecodeError, ValueError) as e:
        print(f"cstools {args.command}: {e}", file=sys.stderr)
        return 1
