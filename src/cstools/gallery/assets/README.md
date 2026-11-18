# Offline gallery and comparison dumps

Build a gallery and open `index.html` directly (no web server required):

```sh
PYTHONPATH=src python3 -m cstools gallery /path/to/theme-repo -o /tmp/gallery
```

The repository's `colorschemes.toml` selects schemes. Families keep dark/light
counterparts adjacent. The default score/simulation model is deutan severity 1;
`--model model.json` accepts, for example, `{"type":"protan","severity":0.8}`.
Scores and the SVG simulation use the same model. Role swatches show original and
simulated colours side by side and are not filtered a second time.

## Neovim comparison themes

`dump.lua` is packaged alongside this document. Find the installed copy with:

```sh
python3 -c 'from importlib.resources import files; print(files("cstools.gallery").joinpath("assets/dump.lua"))'
```

A headless Neovim invocation can load a theme from its runtime directory without
using or modifying the normal Neovim configuration. This example uses disposable
XDG directories; substitute the theme name, runtime directory and dump script path:

```sh
scratch="$(mktemp -d)"
mkdir -p ./dumps
XDG_CONFIG_HOME="$scratch/config" XDG_CACHE_HOME="$scratch/cache" \
XDG_DATA_HOME="$scratch/data" XDG_STATE_HOME="$scratch/state" \
CS=example PRE='vim.opt.rtp:prepend("/absolute/path/to/theme-runtime")' \
OUT="$PWD/dumps/example.json" \
nvim --headless -u NONE -l /absolute/path/to/cstools/gallery/assets/dump.lua
rm -rf "$scratch"

PYTHONPATH=src python3 -m cstools gallery /path/to/theme-repo \
  -o /tmp/gallery --extra-dumps ./dumps
```

`PRE` is optional Lua setup executed before `:colorscheme` (for plugin options or
runtime dependencies). Dumps have `{name, background, groups, terminal}`. Neovim
resolves linked highlight groups before exporting. A dump's `Normal` group must
provide foreground and background colours. Missing terminal entries are inferred
from its editor roles, as in the prototype, and the UI labels inferred palettes.
Comparison IDs are prefixed with `comparison:` to avoid scheme-ID collisions.

## Ratings and export

Stars, heart picks and notes persist in browser localStorage when permitted.
“Save my picks” posts JSON to `/api/results` when served over HTTP(S). With no
working endpoint, including `file://`, it downloads `gallery-picks.json` instead.
If browser settings deny localStorage, ratings still work for the current session
and can be exported. Moving the gallery may change its browser storage origin.
