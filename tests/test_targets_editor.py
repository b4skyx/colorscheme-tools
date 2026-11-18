"""Editor targets: template parity, runtime options and accessible lualine modes."""
from __future__ import annotations

import copy
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from cstools.highlights.groups import CORE_SECTIONS, build_groups, plugin_sections
from cstools.score.editor import roles_of
from cstools.scheme.assemble import ACCENT_KEYS, assemble_scheme
from cstools.scheme.model import ANSI_NAMES, Scheme
from cstools.targets import REGISTRY, RenderContext
from cstools.targets.lualine import MODE_ROLES, mode_roles
from cstools.targets.neovim import lua_value
from cstools.vision.cvd import de_seen
from cstools.vision.model import DEFAULT
from support import SCHEME_IDS, legacy, migrated, write_repo

CTX = RenderContext(project_name="demo", lua_module="demo")
EDITOR_TARGETS = ("vim", "neovim", "lualine")
SELECTED = (
    "Normal", "NormalFloat", "Comment", "Keyword", "Function", "String", "Type", "Visual", "FloatBorder",
    "@variable", "@keyword", "@function.builtin", "@string", "@lsp.type.function", "@lsp.mod.readonly",
    "DiagnosticError", "DiagnosticSignWarn", "DiagnosticFloatingInfo", "DiagnosticDeprecated",
    "LspInlayHint", "GitSignsAdd", "GitSignsChangeNr", "GitSignsAddLn", "GitSignsCurrentLineBlame",
    "TelescopeNormal", "TelescopeBorder", "TelescopeMatching", "BlinkCmpKindFunction", "IblScope",
    "NvimTreeGitNewIcon", "DiffviewStatusDeleted", "CodeCompanionChatHeader", "CopilotChatHelp",
)


def editor_schemes() -> list[Scheme]:
    """Migrated dark fixtures and the four light variants from the behavioural reference."""
    schemes = [migrated(sid) for sid in SCHEME_IDS]
    gen = legacy("gen_schemes")
    accents = dict(zip(ACCENT_KEYS, ("K", "F", "S", "T", "C", "P", "err", "warn", "info", "hint", "add", "change", "delete")))
    for style in gen.STYLES:
        if not style.get("light"):
            continue
        terminal = gen.terminal_for(style, style["a"])
        schemes.append(assemble_scheme(
            {"id": style["id"], "name": style["name"], "variant": "light"},
            {"bg": style["bg"], "bg_alt": style["alt"], "fg": style["fg"], "fg_dim": style["dim"], "comment": style["comment"]},
            {key: style["a"][value] for key, value in accents.items()},
            {f"{key}_italic": value for key, value in style["italic"].items()},
            dict(zip(ANSI_NAMES, terminal[:8])), dict(zip(ANSI_NAMES, terminal[8:]))))
    return schemes


class EditorTargetTest(unittest.TestCase):
    def test_pure_deterministic_project_targets(self) -> None:
        schemes = editor_schemes()
        before = copy.deepcopy(schemes)
        for name in EDITOR_TARGETS:
            target = REGISTRY[name]
            self.assertEqual(target.scope, "project")
            self.assertEqual(target.render_project(schemes, CTX), target.render_project(schemes, CTX))
        self.assertEqual(schemes, before)
        lua = REGISTRY["neovim"].render_project(schemes, CTX)
        self.assertEqual(len(lua), len(schemes) + 2)
        self.assertIn('"@lsp.type.function"', lua["lua/demo/themes/haze.lua"])
        vim = REGISTRY["vim"].render_project(schemes, CTX)["colors/haze.vim"]
        self.assertIn('lua require("demo").load("haze")', vim)
        self.assertNotIn("hi @", vim)
        self.assertNotIn("hi Telescope", vim)
        self.assertNotIn("hi GitSigns", vim)
        self.assertIn("hi DiagnosticSignError ", vim)
        self.assertIn("let g:terminal_ansi_colors = [", vim)

    def test_dotted_module_name(self) -> None:
        ctx = RenderContext(project_name="demo", lua_module="demo.theme")
        out = REGISTRY["neovim"].render_project([migrated("haze")], ctx)
        self.assertIn("lua/demo/theme/init.lua", out)
        self.assertIn('require("demo.theme.config")', out["lua/demo/theme/init.lua"])

    def test_plugin_sections_preserve_core_and_git_roles(self) -> None:
        scheme = migrated("haze")
        core = {name: style for section in CORE_SECTIONS for name, style in section(scheme).items()}
        all_groups = build_groups(scheme)
        names = set(core)
        for section in plugin_sections():
            groups = section(scheme)
            self.assertFalse(names & groups.keys(), section.__module__)
            names.update(groups)
        for name, style in core.items():
            self.assertEqual(all_groups[name], style)
        for name, role in {
            "GitSignsUntrackedNr": "git.add", "DiffviewStatusDeleted": "git.delete",
            "NvimTreeGitDirtyIcon": "git.change", "TelescopeResultsDiffAdd": "git.add",
        }.items():
            self.assertEqual(all_groups[name].fg, scheme.resolve(role))
        self.assertEqual(all_groups["@lsp.type.function"], all_groups["@function"])
        self.assertIsNot(all_groups["@lsp.type.function"], all_groups["@function"])
        self.assertEqual(all_groups["BlinkCmpKindClass"], scheme.style("syntax.type"))

    def test_lualine_mode_colors_pairwise_default_vision(self) -> None:
        for scheme in editor_schemes():
            sid = scheme.id
            roles, minimum = mode_roles(scheme)
            scored = roles_of(build_groups(scheme))
            self.assertEqual(scheme.resolve(roles["normal"]), scored["function"])
            self.assertGreaterEqual(minimum, 10, sid)
            for a, b in itertools.combinations(roles.values(), 2):
                self.assertGreaterEqual(de_seen(scheme.resolve(a), scheme.resolve(b), DEFAULT.matrix), 10, (sid, a, b))
            text = REGISTRY["lualine"].render_project([scheme], CTX)[f"lua/lualine/themes/{sid}.lua"]
            for mode, role in roles.items():
                self.assertIn(f"{mode}={role}", text)
            self.assertIn("Minimum mode separation:", text)

    def test_lualine_overrides_and_best_effort_warning(self) -> None:
        scheme = migrated("haze")
        roles, _ = mode_roles(scheme)
        scheme.derived["lualine_command"] = roles["command"]
        self.assertEqual(mode_roles(scheme)[0]["command"], "lualine_command")
        # Pin every mode to two colours: optimum minimum is zero, not a render error.
        for index, mode in enumerate(MODE_ROLES):
            scheme.derived["lualine_" + mode] = "syntax.function" if index % 2 else "syntax.string"
        warnings = []
        ctx = RenderContext(project_name="demo", lua_module="demo", warn=warnings.append)
        result = REGISTRY["lualine"].render_project([scheme], ctx)
        self.assertEqual(mode_roles(scheme)[1], 0)
        self.assertTrue(result)
        self.assertEqual(len(warnings), 1)
        self.assertIn("haze: lualine mode separation is 0.00", warnings[0])

    def test_build_warning_channel(self) -> None:
        from cstools.project import render_repo
        from cstools.scheme import io
        with tempfile.TemporaryDirectory() as tmp:
            root = write_repo(Path(tmp), ["lualine"], schemes=("haze",))
            scheme = migrated("haze")
            for mode in MODE_ROLES:
                scheme.derived["lualine_" + mode] = "syntax.function"
            io.dump(scheme, root / "haze/colorschemes.json")
            warnings = []
            self.assertIn("lua/lualine/themes/haze.lua", render_repo(root, warn=warnings.append))
            self.assertEqual(len(warnings), 1)

    def test_lualine_best_effort_maximises_minimum(self) -> None:
        scheme = migrated("haze")
        # Exactly six distinct colours: the optimum must use all six. Compare the
        # exact minimum against the search result, rather than accepting a greedy score.
        refs = ("ui.bg", "ui.comment", "syntax.function", "syntax.string", "syntax.type", "diagnostic.error")
        colors = [scheme.resolve(ref) for ref in refs]
        for group in ("syntax", "diagnostic", "git"):
            for index, role in enumerate(scheme.roles[group]):
                color = colors[index % len(colors)] if group == "syntax" else colors[1]
                scheme.palette[f"test_{group}_{index}"] = color
                scheme.roles[group][role] = f"test_{group}_{index}"
        expected = min(de_seen(a, b, DEFAULT.matrix) for a, b in itertools.combinations(colors, 2))
        self.assertLess(expected, 10)
        self.assertAlmostEqual(mode_roles(scheme)[1], expected)


@unittest.skipUnless(shutil.which("nvim"), "nvim is not installed")
class NeovimRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.schemes = editor_schemes()
        for name in EDITOR_TARGETS:
            for relative, text in REGISTRY[name].render_project(self.schemes, CTX).items():
                path = self.root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
        self.env = dict(os.environ)
        for name in ("XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
            path = self.root / name
            path.mkdir()
            self.env[name] = str(path)

    def run_nvim(self, script: str, *commands: str) -> dict:
        dump = self.root / "dump.json"
        lua = self.root / "test.lua"
        lua.write_text(script + "\nvim.fn.writefile({vim.json.encode(result)}, " + json.dumps(str(dump)) + ")\n", encoding="utf-8")
        command = ["nvim", "--headless", "-u", "NONE", "-i", "NONE", "--cmd", f"set rtp^={self.root}"]
        for cmd in commands:
            command.extend(["--cmd", cmd])
        command.extend(["-l", str(lua)])
        run = subprocess.run(command, capture_output=True, text=True, env=self.env, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(dump.exists(), run.stdout + run.stderr)
        return json.loads(dump.read_text(encoding="utf-8"))

    def test_colorscheme_lua_delegation_all_schemes(self) -> None:
        script = "local result = {}\n"
        for scheme in self.schemes:
            names = lua_value(SELECTED)
            script += f'vim.cmd("colorscheme {scheme.id}")\n'
            script += f'assert(package.loaded["demo.themes.{scheme.id}"])\n'
            script += 'local item = {name=vim.g.colors_name, background=vim.o.background, groups={}, terminal={}}\n'
            script += f'for _, name in ipairs({names}) do item.groups[name] = vim.api.nvim_get_hl(0, {{name=name, link=false}}) end\n'
            script += 'for i=0,15 do item.terminal[i+1] = vim.g["terminal_color_"..i] end\n'
            script += f'result["{scheme.id}"] = item\n'
        result = self.run_nvim(script)
        for scheme in self.schemes:
            item = result[scheme.id]
            self.assertEqual(item["name"], scheme.id)
            self.assertEqual(item["background"], scheme.variant)
            self.assertEqual(item["terminal"], [scheme.ansi(i) for i in range(16)])
            expected = build_groups(scheme)
            for name in SELECTED:
                got, want = item["groups"][name], expected[name]
                for key in ("fg", "bg", "sp"):
                    self.assertEqual(got.get(key), int(getattr(want, key)[1:], 16) if getattr(want, key) else None,
                                     (scheme.id, name, key))
                for key in ("italic", "bold", "undercurl", "strikethrough"):
                    self.assertEqual(got.get(key, False), getattr(want, key), (scheme.id, name, key))

    def test_vimscript_opt_out(self) -> None:
        result = self.run_nvim('''
vim.cmd("colorscheme haze")
local result = {name=vim.g.colors_name, terminal=vim.g.terminal_ansi_colors,
  lua_loaded=package.loaded["demo"] ~= nil, groups={}}
for _, name in ipairs({"Normal", "Comment", "Keyword", "DiffAdd", "DiagnosticSignError"}) do
  result.groups[name] = vim.api.nvim_get_hl(0, {name=name, link=false})
end
''', "let g:demo_vimscript=1")
        scheme = migrated("haze")
        self.assertEqual(result["name"], "haze")
        self.assertFalse(result["lua_loaded"])
        self.assertEqual(result["terminal"], [scheme.ansi(i) for i in range(16)])
        for name, got in result["groups"].items():
            style = build_groups(scheme)[name]
            for key in ("fg", "bg"):
                expected = getattr(style, key)
                self.assertEqual(got.get(key), int(expected[1:], 16) if expected else None, (name, key))
            self.assertEqual(got.get("italic", False), style.italic)

    def test_runtime_options_callbacks_overrides_reload_palette(self) -> None:
        result = self.run_nvim('''
local theme = require("demo")
local palette = theme.palette("haze")
local original_bg = palette.bg
palette.bg = palette.fg
assert(theme.palette("haze").bg == original_bg)
theme.setup({transparent=true, italics=false, bold=false, dim_inactive=true, terminal_colors=false,
  on_highlights=function(groups, p) groups.Comment.fg = p.fg end,
  overrides={Normal={fg=palette.fg}, Comment={bold=true}}})
vim.g.terminal_color_0 = "unchanged"
vim.cmd("colorscheme haze")
local result = {groups={}, terminal=vim.g.terminal_color_0}
for _, name in ipairs({"Normal", "NormalFloat", "NormalNC", "SignColumn", "FloatBorder", "Keyword", "Title", "Comment"}) do
  result.groups[name] = vim.api.nvim_get_hl(0, {name=name, link=false})
end
theme.setup({dim_inactive=true})
theme.load("haze")
result.dim = vim.api.nvim_get_hl(0, {name="NormalNC", link=false})
theme.setup({})
theme.load("haze")
result.reloaded = vim.api.nvim_get_hl(0, {name="Normal", link=false})
''')
        scheme = migrated("haze")
        self.assertEqual(result["terminal"], "unchanged")
        for name in ("Normal", "NormalFloat", "NormalNC", "SignColumn", "FloatBorder"):
            self.assertNotIn("bg", result["groups"][name])
        self.assertNotIn("italic", result["groups"]["Keyword"])
        self.assertNotIn("bold", result["groups"]["Title"])
        self.assertTrue(result["groups"]["Comment"]["bold"])
        self.assertEqual(result["groups"]["Comment"]["fg"], int(scheme.resolve("ui.fg")[1:], 16))
        self.assertEqual(result["dim"]["bg"], int(scheme.resolve("ui.bg_alt")[1:], 16))
        self.assertEqual(result["reloaded"]["bg"], int(scheme.resolve("ui.bg")[1:], 16))

    def test_lualine_seven_modes_and_theme_palette(self) -> None:
        ids = lua_value([scheme.id for scheme in self.schemes])
        result = self.run_nvim('local result = {themes={}, palette=require("demo").palette("haze")}\n'
                               + 'for _, id in ipairs(' + ids + ') do\n'
                               + '  result.themes[id] = require("lualine.themes."..id)\nend\n')
        for scheme in self.schemes:
            theme = result["themes"][scheme.id]
            self.assertEqual(set(theme), {*MODE_ROLES, "inactive"})
            for sections in theme.values():
                self.assertEqual(set(sections), set("abc"))
            for a, b in itertools.combinations(MODE_ROLES, 2):
                self.assertGreaterEqual(de_seen(theme[a]["a"]["bg"], theme[b]["a"]["bg"], DEFAULT.matrix), 10)
        scheme = migrated("haze")
        for key in ("bg", "bg_alt", "bg_visual", "border", "diff_add_bg"):
            self.assertEqual(result["palette"][key], scheme.resolve(key))

    def test_vim_is_preferred_to_same_name_lua_entry(self) -> None:
        # Neovim 0.12 help :colorscheme: colors/{name}.vim is tried first.
        (self.root / "colors/haze.lua").write_text('error("unexpected Lua entry")\n', encoding="utf-8")
        result = self.run_nvim('vim.cmd("colorscheme haze"); local result = {name=vim.g.colors_name}')
        self.assertEqual(result["name"], "haze")

    def test_light_background(self) -> None:
        scheme = migrated("haze")
        scheme.id, scheme.variant = "sample-light", "light"
        for target in ("vim", "neovim"):
            for relative, text in REGISTRY[target].render_project([scheme], CTX).items():
                (self.root / relative).write_text(text, encoding="utf-8")
        result = self.run_nvim('vim.cmd("colorscheme sample-light"); local result = {bg=vim.o.background}')
        self.assertEqual(result["bg"], "light")


if __name__ == "__main__":
    unittest.main()
