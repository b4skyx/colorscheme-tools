# colorscheme-tools: architecture contract

This document is the contract every contributor (human or agent) follows. If code and this document
disagree, fix one of them in the same change.

`colorscheme-tools` creates, converts and renders colourschemes whose **single source of truth** is one
`colorschemes.json` per scheme. It is a pure-Python (≥ 3.11, **stdlib only**) package `cstools` with a CLI.
The first consumer is the theme repository **clearsight** (`~/colorblind-lab/colorschemes`), but nothing
in this package may hard-code clearsight names, paths or colours.

```
colorscheme-tools/
├── pyproject.toml            name "colorscheme-tools", package "cstools", console script "cstools"
├── README.md · LICENSE (MIT) · ARCHITECTURE.md
├── schema/colorscheme.schema.json     JSON Schema (draft 2020-12) for schema_version 2
├── src/cstools/
│   ├── __init__.py           __version__
│   ├── __main__.py           python -m cstools
│   ├── cli.py                argparse front-end only; no business logic
│   ├── color/                pure colour maths, no I/O, no scheme knowledge
│   │   ├── spaces.py         hex ⇄ sRGB ⇄ linear ⇄ XYZ ⇄ Lab/Luv ⇄ OKLab/OKLCH, gamut mapping
│   │   ├── difference.py     ciede2000(lab1, lab2)
│   │   ├── contrast.py       relative_luminance, wcag_contrast
│   │   └── ops.py            mix (OKLab), lighten/darken (OKLCH L), raise_(variant-aware), with_chroma
│   ├── vision/
│   │   ├── cvd.py            Machado 2009 matrices, cvd_matrix(protan, deutan, mix), simulate(hex, M)
│   │   └── model.py          VisionModel dataclass (type, severity) → matrix; DEFAULT = deutan 1.0
│   ├── scheme/
│   │   ├── model.py          Scheme / Style / Terminal dataclasses + reference resolution
│   │   ├── expr.py           derived-colour expression evaluator (see below)
│   │   ├── defaults.py       default derived colours (variant-aware) shared by all schemes
│   │   ├── io.py             load / dump colorschemes.json (stable key order, 2-space indent)
│   │   ├── validate.py       structural validation without third-party libs (mirrors the JSON Schema)
│   │   ├── naming.py         automatic base-colour names from OKLCH (used by migrate/optimize)
│   │   └── migrate.py        schema v1 → v2
│   ├── score/
│   │   ├── editor.py         syntax/diagnostic/git separation for a VisionModel
│   │   └── terminal.py       ANSI separation for a VisionModel
│   ├── optimize/
│   │   ├── recipe.py         Recipe dataclass ← recipe.toml (tomllib)
│   │   ├── search.py         generic seeded hill-climb over OKLCH points
│   │   ├── editor.py         editor-role optimiser (port of legacy/gen_schemes.py)
│   │   ├── terminal.py       ANSI optimiser (port of legacy/export_schemes.py), variant-aware
│   │   └── build.py          recipe → Scheme (palette naming + dedup + roles + terminal)
│   ├── highlights/
│   │   └── groups.py         ONE role-based highlight template (Vim/Neovim groups, treesitter, LSP,
│   │                         diagnostics, git/diff, plugin groups) → {group: ResolvedStyle}
│   ├── targets/
│   │   ├── base.py           Target protocol, RenderContext, header() helper, registry decorator
│   │   ├── __init__.py       imports all target modules; REGISTRY
│   │   └── <name>.py         one module per output format (see "Targets")
│   ├── project.py            theme-repo config (colorschemes.toml) + build orchestration
│   └── gallery/              HTML gallery renderer (port of legacy/gallery.html + build_gallery.py)
├── tests/                    unittest (python -m unittest discover -s tests); golden checks
└── legacy/                   original prototype scripts, reference only, never imported
```

## Design rules
1. **One source of truth.** A scheme's colours live only in `colorschemes.json`. Every hex appears **once**,
   in `palette`. Everything else is a reference or a formula. Changing one base colour must update every
   target after `cstools build`.
2. **Layering.** `color` ← `vision` ← `scheme` ← (`score`, `highlights`, `optimize`) ← `targets` ← `project` ← `cli`.
   Lower layers never import higher ones. `color` and `vision` have no I/O.
3. **Targets are pure functions**: `render(scheme, ctx) -> dict[relative_path, text]`. No file writing, no
   environment access, no hard-coded hex. Colours come from roles, the terminal block, or the shared
   derived colours (`scheme.resolve("diff_add_bg")`). If a target needs a new derived colour, add it to
   `scheme/defaults.py`, not to the target.
4. **Deterministic output**: same input → byte-identical files (sorted where order is free, seeded RNG).
5. **No user-environment side effects** in code or tests: never write to `~/.config`, never run
   `fish_config theme save`, never use the default tmux socket, never build bat caches in the real HOME.
   Use temporary directories and `XDG_*`/`BAT_CACHE_PATH`/`tmux -L <tmp>` for validation.
6. **Neutral wording** in generated files: names, tags, descriptions and headers contain no personal labels
   ("favourite", "for you", "your") and no references to other themes ("X-like", other themes' colour names).
   Accessibility wording (e.g. "deutan-optimised") is fine.
7. Small modules, type hints, docstrings on public functions, no global mutable state except the target
   registry. Prefer dataclasses over dicts at module boundaries.

## colorschemes.json (schema_version 2)

```jsonc
{
  "$schema": "../schema/colorscheme.schema.json",   // optional; path or URL
  "schema_version": 2,
  "id": "haze", "name": "Haze", "variant": "dark",    // variant: "dark" | "light"
  "family": "haze",                                     // dark/light counterparts share a family
  "description": "…", "tags": ["dark", "muted", "low-contrast"],
  "designed_for": { "vision": "deutan", "severity": 1.0, "metric": "CIEDE2000 on simulated colours" },

  "palette": {                     // BASE COLOURS: the only hex values in the file, all unique
    "bg": "#2d2f33", "bg_alt": "#35373c", "fg": "#c0bdb5", "fg_dim": "#94928c", "comment": "#74736f",
    "lavender": "#7b81b9", "sky": "#9ecfff", "sand": "#e2c88a", "sage": "#739b69", "mauve": "#bb8cab"
    // … every other distinct colour, named by naming.py (hue name + lightness suffix when needed)
  },

  "derived": {                     // OPTIONAL per-scheme additions/overrides of scheme/defaults.py
    "bg_visual": { "mix": [{ "raise": ["bg", 0.10] }, "syntax.type", 0.12] }
  },

  "roles": {
    "ui":         { "bg": "bg", "bg_alt": "bg_alt", "fg": "fg", "fg_dim": "fg_dim", "comment": "comment" },
    "syntax":     { "keyword":  { "fg": "lavender", "italic": true },
                    "function": { "fg": "sky" }, "string": { "fg": "sand" } /* … */ },
    "diagnostic": { "error": "copper", "warning": "butter", "info": "steel", "hint": "mint", "ok": "denim" },
    "git":        { "add": "denim", "change": "lilac", "delete": "tan" }
  },

  "terminal": {                    // every value is a reference or expression
    "background": "bg", "foreground": "fg", "cursor": "fg", "cursor_text": "bg",
    "selection_background": "bg_visual", "selection_foreground": "fg",
    "normal": { "black": { "raise": ["bg_alt", 0.06] }, "red": "rust", "green": "mint", /* … */ "white": "fg" },
    "bright": { "black": "comment", "red": "rust_bright", /* … */ "white": { "raise": ["fg", 0.07] } }
  }
}
```

Not stored (derivable, generated on demand): resolved highlight maps, OKLCH strings, per-colour usage lists
(`cstools inspect`), scores (`cstools score`).

### References and expressions (`scheme/expr.py`)
A colour value is one of:
- `"#rrggbb"`: literal (allowed **only** in `palette`; `validate` rejects literals elsewhere),
- `"name"`: a `palette` or derived name,
- `"group.role"`: a role path, e.g. `"syntax.type"`, `"diagnostic.warning"`, `"git.add"`, `"ui.bg"`
  (for syntax roles this means the role's `fg`),
- an expression object with exactly one key:
  `{"mix": [a, b, t]}` (OKLab, t=0 → a) · `{"lighten": [c, dL]}` · `{"darken": [c, dL]}` ·
  `{"raise": [c, dL]}` (lighten on dark variants, darken on light) · `{"chroma": [c, C]}` (set OKLCH chroma).

Resolution order for a bare name: palette → scheme `derived` → `defaults.py`. Cycles raise `SchemeError`.
Results are hex strings rounded exactly like `legacy/cvd.py` (`lin2hex`), so migrated schemes reproduce
the legacy output byte-for-byte.

### Canonical role names
- `syntax`: `variable`, `comment`, `keyword`, `function`, `string`, `type`, `constant`, `number`, `boolean`,
  `property`, `parameter`, `builtin`, `operator`, `punctuation`, `module`, `attribute`, `tag`, `escape`,
  `regex`, `macro`, `constructor`, `label`, `todo`, `note`. Each is a Style: `fg`, optional `bg`, `sp`, and
  booleans `bold`, `italic`, `underline`, `undercurl`, `strikethrough`, `reverse`.
- `diagnostic`: `error`, `warning`, `info`, `hint`, `ok`
- `git`: `add`, `change`, `delete`
- `ui`: `bg`, `bg_alt`, `fg`, `fg_dim`, `comment`

### Default derived colours (`scheme/defaults.py`; legacy formulas from `gen_schemes.groups_for`)
`bg_cursorline = raise(bg, .035)` · `bg_visual = mix(raise(bg, .10), syntax.type, .12)` ·
`line_nr = mix(comment, bg, .35)` · `nontext = mix(comment, bg, .4)` · `border = raise(bg_alt, .08)` ·
`bg_search = mix(bg, diagnostic.warning, .35)` · `diff_add_bg = mix(bg, git.add, .22)` ·
`diff_delete_bg = mix(bg, git.delete, .22)` · `diff_change_bg = mix(bg, git.change, .12)` ·
`diff_text_bg = mix(bg, git.change, .32)` · `virtual_<error|warning|info|hint|ok>_bg = mix(bg, diagnostic.X, .10)`.

## Theme repository contract (e.g. clearsight)
```
<repo>/colorschemes.toml        [project] name, lua_module, url; [build] targets = [...], schemes = [...]
<repo>/<id>/recipe.toml         optimiser input (design), optional
<repo>/<id>/colorschemes.json   SOURCE OF TRUTH
<repo>/<id>/<generated files>   per-scheme targets (see below)
<repo>/colors/ <repo>/lua/      generated project-level targets (vim, neovim, lualine)
```
`cstools build <repo>` renders every configured target for every configured scheme and writes files,
creating directories as needed, and reports changed files. `cstools build --check` exits non-zero if
anything would change (for CI).

## Targets
Each module in `targets/` registers one or more `Target`s:

```python
@register
class Kitty(Target):
    name = "kitty"; scope = "scheme"          # "scheme": once per scheme; "project": once for all schemes
    def render(self, scheme, ctx) -> dict[str, str]: ...        # scope == "scheme"
    # def render_project(self, schemes, ctx) -> dict[str, str]  # scope == "project"
```
`RenderContext` carries `project_name`, `lua_module`, `tools_version`, and `header(comment_prefix)` which
returns a "Generated by colorscheme-tools vX from <id>/colorschemes.json. Do not edit." banner.

| Target | Output (relative to repo) | Validation in tests |
|---|---|---|
| alacritty | `<id>/alacritty.toml` | tomllib parse; keys under `colors.*` |
| kitty | `<id>/kitty.conf` | `key value` lines; color0–15 present |
| wezterm | `<id>/wezterm.toml` | tomllib; `[colors] ansi/brights` 8 each; `[metadata] name` |
| ghostty | `<id>/ghostty` (theme file, copy to `themes/<Name>`) | `palette = N=#hex` 0–15 |
| rio | `<id>/rio.toml` | tomllib; keys as in Rio's `[colors]` |
| tmux | `<id>/tmux.conf` | `tmux -L <tmp> -f file start-server \; show -g …` |
| fish | `<id>/fish.theme` | `fish_color_*` / `fish_pager_color_*` lines, hex without `#` |
| starship | `<id>/starship.toml` | tomllib; `[palettes.<id>]` |
| fzf | `<id>/fzf.sh`, `<id>/fzf.fish` | `--color=` contains all keys |
| bat | `<id>/bat.tmTheme` | plistlib parse; `bat` with temp cache renders |
| delta | `<id>/delta.gitconfig` | `git config -f file --list` parses |
| lazygit | `<id>/lazygit.yml` | YAML subset written by hand; key set checked |
| eza | `<id>/eza.yml` | eza theme keys; `EZA_CONFIG_DIR=<tmp> eza` runs |
| yazi | `<id>/yazi/<id>.yazi/{flavor.toml,tmtheme.xml}` | tomllib; plistlib |
| vim | `colors/<id>.vim` (Neovim delegates to Lua) | nvim headless loads; vimscript path via test flag |
| neovim | `lua/<module>/themes/<id>.lua` + static `lua/<module>/{init,config}.lua` | nvim headless: groups equal highlight template |
| lualine | `lua/lualine/themes/<id>.lua` | nvim headless `require` returns table |

## Vision model and scoring
`VisionModel` defaults to deutan severity 1.0 (Machado 2009), metric CIEDE2000 on simulated colours.
Scores are computed on demand (`cstools score`) and never stored in `colorschemes.json`.

## CLI
```
cstools validate PATH...                 schema + reference + cycle checks
cstools migrate OLD.json -o NEW.json     v1 → v2 (+ --recipe RECIPE.toml for metadata)
cstools optimize RECIPE.toml -o OUT.json optimise editor roles + terminal, write v2
cstools build REPO [--targets ..] [--schemes ..] [--check]
cstools render SCHEME.json --target NAME [--out DIR]   print or write one target
cstools score SCHEME.json [--model MODEL.json] [--json]
cstools inspect SCHEME.json               palette usage (which roles/targets use each base colour)
cstools targets                           list registered targets
cstools gallery REPO -o DIR [--extra-dumps DIR]
```
