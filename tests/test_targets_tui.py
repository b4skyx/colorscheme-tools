"""TUI targets: structure, role propagation, and isolated live-binary validation."""
from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import tomllib
import unittest

from cstools.scheme.io import load
from cstools.scheme.model import Scheme
from cstools.targets import REGISTRY
from cstools.targets.base import RenderContext
from cstools.targets.bat import render_tmtheme
from support import SCHEME_IDS, migrated

CTX = RenderContext(project_name="demo", lua_module="demo")
YAZI_REFERENCE = Path.home() / ".config/yazi/flavors/gruvbox-dark.yazi/flavor.toml"
SCOPES = {
    "comment", "string", "constant.numeric", "constant.language", "constant.character.escape", "constant.other",
    "keyword", "keyword.operator", "storage", "storage.type", "entity.name.function", "support.function",
    "meta.function-call", "entity.name.type", "entity.name.class", "support.type", "support.class", "variable",
    "variable.parameter", "variable.language", "variable.other.member", "entity.name.tag", "entity.other.attribute-name",
    "entity.name.namespace", "punctuation", "markup.heading", "markup.bold", "markup.italic", "markup.inserted",
    "markup.deleted", "markup.changed", "meta.diff.header", "invalid",
}
LAZYGIT_KEYS = {
    "activeBorderColor", "inactiveBorderColor", "searchingActiveBorderColor", "optionsTextColor",
    "selectedLineBgColor", "inactiveViewSelectedLineBgColor", "cherryPickedCommitFgColor", "cherryPickedCommitBgColor",
    "markedBaseCommitFgColor", "markedBaseCommitBgColor", "unstagedChangesColor", "defaultFgColor",
}
EZA_KEYS = {
    "filekinds": "normal directory symlink pipe block_device char_device socket special executable mount_point",
    "perms": "user_read user_write user_execute_file user_execute_other group_read group_write group_execute "
             "other_read other_write other_execute special_user_file special_other attribute",
    "size": "major minor number_byte number_kilo number_mega number_giga number_huge "
            "unit_byte unit_kilo unit_mega unit_giga unit_huge",
    "users": "user_you user_root user_other group_yours group_other group_root",
    "links": "normal multi_link_file", "git": "new modified deleted renamed ignored conflicted",
    "git_repo": "branch_main branch_other git_clean git_dirty",
    "file_type": "image video music crypto document compressed temp compiled build source",
}
EZA_LEAVES = set("punctuation date inode blocks header octal flags control_char broken_symlink broken_path_overlay".split())
YAZI_KEYS = {
    "mgr": "cwd find_keyword find_position symlink_target marker_copied marker_cut marker_marked marker_selected "
           "count_copied count_cut count_selected border_symbol border_style",
    "tabs": "active inactive sep_inner sep_outer",
    "mode": "normal_main normal_alt select_main select_alt unset_main unset_alt",
    "indicator": "parent current preview padding",
    "status": "overall sep_left sep_right perm_sep perm_type perm_read perm_write perm_exec "
              "progress_label progress_normal progress_error",
    "which": "cols mask cand rest desc separator separator_style",
    "confirm": "border title body list btn_yes btn_no btn_labels",
    "spot": "border title tbl_col tbl_cell", "notify": "title_info title_warn title_error",
    "pick": "border active inactive", "input": "border title value selected", "cmp": "border active inactive",
    "tasks": "border title hovered", "help": "border chord action hovered", "filetype": "rules",
}


def render(target: str, scheme: Scheme) -> dict[str, str]:
    """Render with a fixed project context."""
    return REGISTRY[target].render(scheme, CTX)


def yaml_mapping(text: str) -> dict:
    """Read only the generated YAML subset: indented mappings with JSON leaf values."""
    root: dict = {}
    stack = [(-2, root)]
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        key, value = line.strip().split(":", 1)
        while stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise ValueError(f"duplicate YAML key: {key}")
        parent[key] = json.loads(value) if value.strip() else {}
        if not value.strip():
            stack.append((indent, parent[key]))
    return root


class TuiStructureTest(unittest.TestCase):
    def test_paths_and_determinism(self) -> None:
        for sid in SCHEME_IDS:
            scheme = migrated(sid)
            for target, suffixes in {
                "bat": ["bat.tmTheme"], "delta": ["delta.gitconfig"], "lazygit": ["lazygit.yml"],
                "eza": ["eza.yml"], "yazi": [f"yazi/{sid}.yazi/flavor.toml", f"yazi/{sid}.yazi/tmtheme.xml"],
            }.items():
                with self.subTest(sid=sid, target=target):
                    files = render(target, scheme)
                    self.assertEqual(set(files), {f"{sid}/{suffix}" for suffix in suffixes})
                    self.assertEqual(files, render(target, scheme))
                    self.assertTrue(all(text.endswith("\n") for text in files.values()))

    def test_bat_plist_scopes_colours_and_styles(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid=sid):
                scheme = migrated(sid)
                data = plistlib.loads(render_tmtheme(scheme).encode())
                self.assertEqual(plistlib.loads(plistlib.dumps(data)), data)
                self.assertEqual(data["name"], scheme.name)
                globals_ = data["settings"][0]["settings"]
                expected = {
                    "background": "ui.bg", "foreground": "ui.fg", "lineHighlight": "bg_cursorline",
                    "selection": "bg_visual", "gutterForeground": "line_nr", "invisibles": "nontext",
                    "findHighlight": "bg_search",
                }
                self.assertEqual(globals_, {**{key: scheme.resolve(role) for key, role in expected.items()},
                                            "caret": scheme.terminal_color("cursor")})
                scopes = {item["scope"]: item["settings"] for item in data["settings"][1:]}
                self.assertEqual(set(scopes), SCOPES)
                self.assertEqual(len(data["settings"]), len(SCOPES) + 1)
                for scope, role in {"comment": "syntax.comment", "keyword": "syntax.keyword",
                                    "entity.name.function": "syntax.function", "markup.inserted": "git.add",
                                    "markup.deleted": "git.delete", "markup.changed": "git.change",
                                    "invalid": "diagnostic.error"}.items():
                    self.assertEqual(scopes[scope]["foreground"], scheme.resolve(role))
                    style = scheme.style(role)
                    self.assertEqual("italic" in scopes[scope]["fontStyle"], style.italic)
                    self.assertEqual("bold" in scopes[scope]["fontStyle"], style.bold)
                self.assertIn("bold", scopes["markup.bold"]["fontStyle"])
                self.assertIn("italic", scopes["markup.italic"]["fontStyle"])

    def test_bat_explicit_role_style_flags_and_xml_escaping(self) -> None:
        scheme = migrated("haze")
        scheme.name = 'A & B <Theme> "name"'
        scheme.roles["syntax"]["function"].update(bold=True, italic=True)
        data = plistlib.loads(render_tmtheme(scheme).encode())
        self.assertEqual(data["name"], scheme.name)
        function = next(item for item in data["settings"][1:] if item["scope"] == "entity.name.function")
        self.assertEqual(set(function["settings"]["fontStyle"].split()), {"bold", "italic"})

    def test_delta_settings_and_light_variant(self) -> None:
        for variant in ("dark", "light"):
            scheme = migrated("haze")
            scheme.variant = variant
            data = configparser.ConfigParser(interpolation=None)
            data.read_string(render("delta", scheme)[f"{scheme.id}/delta.gitconfig"])
            section = data['delta "demo-haze"']
            self.assertEqual(json.loads(section[variant]), "true")
            self.assertNotIn("light" if variant == "dark" else "dark", section)
            self.assertNotIn("syntax-theme", section)
            expected = {
                "plus-style": f"syntax {scheme.resolve('diff_add_bg')}",
                "minus-style": f"syntax {scheme.resolve('diff_delete_bg')}", "zero-style": "syntax",
                "plus-emph-style": f"syntax {scheme.resolve({'mix': ['ui.bg', 'git.add', 0.45]})}",
                "minus-emph-style": f"syntax {scheme.resolve({'mix': ['ui.bg', 'git.delete', 0.45]})}",
            }
            for key, value in expected.items():
                self.assertEqual(json.loads(section[key]), value)
            for key in ("file-style", "file-decoration-style", "hunk-header-style", "hunk-header-decoration-style",
                        "hunk-header-line-number-style", "line-numbers-minus-style", "line-numbers-plus-style",
                        "line-numbers-zero-style", "line-numbers-left-style", "line-numbers-right-style",
                        "commit-decoration-style", "merge-conflict-ours-diff-header-style",
                        "merge-conflict-theirs-diff-header-style", "merge-conflict-ours-diff-header-decoration-style",
                        "merge-conflict-theirs-diff-header-decoration-style"):
                self.assertTrue(json.loads(section[key]))
            shades = json.loads(section["blame-palette"]).split()
            self.assertEqual(shades, [scheme.resolve({"raise": ["ui.bg", amount]}) for amount in (0.02, 0.04, 0.06, 0.08)])

    def test_lazygit_theme_keys_and_colours(self) -> None:
        scheme = migrated("haze")
        data = yaml_mapping(render("lazygit", scheme)["haze/lazygit.yml"])
        self.assertEqual(set(data), {"gui"})
        self.assertEqual(set(data["gui"]), {"theme"})
        theme = data["gui"]["theme"]
        self.assertEqual(set(theme), LAZYGIT_KEYS)
        self.assertEqual(theme["activeBorderColor"], [scheme.resolve("syntax.function"), "bold"])
        self.assertEqual(theme["unstagedChangesColor"], [scheme.resolve("git.delete")])
        self.assertEqual(theme["selectedLineBgColor"], [scheme.resolve("bg_visual")])
        for value in theme.values():
            self.assertRegex(value[0], r"^#[0-9a-f]{6}$")

    def test_eza_documented_key_set_and_role_mapping(self) -> None:
        scheme = migrated("haze")
        data = yaml_mapping(render("eza", scheme)["haze/eza.yml"])
        self.assertEqual(set(data), set(EZA_KEYS) | EZA_LEAVES)
        for section, keys in EZA_KEYS.items():
            self.assertEqual(set(data[section]), set(keys.split()))
        for key, role in {"directory": "syntax.function", "executable": "git.add", "symlink": "syntax.type"}.items():
            self.assertEqual(data["filekinds"][key]["foreground"], scheme.resolve(role))
        self.assertTrue(data["filekinds"]["directory"]["is_bold"])
        self.assertTrue(data["filekinds"]["executable"]["is_bold"])
        for key, role in {"new": "git.add", "modified": "git.change", "deleted": "git.delete"}.items():
            self.assertEqual(data["git"][key]["foreground"], scheme.resolve(role))

    def test_yazi_toml_key_set_and_shared_tmtheme(self) -> None:
        for sid in SCHEME_IDS:
            scheme = migrated(sid)
            files = render("yazi", scheme)
            base = f"{sid}/yazi/{sid}.yazi"
            data = tomllib.loads(files[f"{base}/flavor.toml"])
            self.assertEqual(set(data), set(YAZI_KEYS))
            for section, keys in YAZI_KEYS.items():
                self.assertEqual(set(data[section]), set(keys.split()))
            self.assertEqual(data["mgr"]["cwd"]["fg"], scheme.resolve("syntax.function"))
            self.assertEqual(files[f"{base}/tmtheme.xml"], render_tmtheme(scheme))
            plistlib.loads(files[f"{base}/tmtheme.xml"].encode())

    @unittest.skipUnless(YAZI_REFERENCE.is_file(), "installed yazi 26.x flavor reference not available")
    def test_yazi_key_set_parity_with_installed_reference(self) -> None:
        reference = tomllib.loads(YAZI_REFERENCE.read_text(encoding="utf-8"))
        data = tomllib.loads(render("yazi", migrated("haze"))["haze/yazi/haze.yazi/flavor.toml"])

        def shape(value: object) -> object:
            if isinstance(value, dict):
                return {key: shape(item) for key, item in value.items()}
            if isinstance(value, list):
                return [shape(item) for item in value]
            return None

        self.assertEqual(shape(data), shape(reference))

    def test_palette_changes_reach_every_target(self) -> None:
        scheme = migrated("haze")
        before = {target: render(target, scheme) for target in ("bat", "delta", "lazygit", "eza", "yazi")}
        role = scheme.roles["syntax"]["function"]["fg"]
        scheme.palette[role] = "#123456"
        for target, old in before.items():
            self.assertNotEqual(old, render(target, scheme), target)

    def test_available_theme_repository_fixtures(self) -> None:
        root = Path(__file__).resolve().parents[3] / "colorschemes"
        # Portable unit coverage above does not require the separate theme repository.
        if not root.is_dir():
            root = Path.home() / "colorblind-lab/colorschemes"
        paths = sorted(root.glob("*/colorschemes.json"))
        if not paths:
            self.skipTest("separate colorschemes repository not available")
        for path in paths:
            scheme = load(path)
            for target in ("bat", "delta", "lazygit", "eza", "yazi"):
                self.assertTrue(render(target, scheme), (path, target))


class TuiBinaryTest(unittest.TestCase):
    """Every subprocess receives the same complete set of temporary config/cache overrides."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="cstools-tui-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = os.environ.copy()
        for key in tuple(self.env):
            if key.startswith(("BAT_", "DELTA_", "GIT_", "EZA_", "EXA_", "LAZYGIT_")) or key == "LS_COLORS":
                del self.env[key]
        self.env.update({
            "HOME": str(self.root), "BAT_CONFIG_DIR": str(self.root / "bat"),
            "BAT_CACHE_PATH": str(self.root / "bat-cache"), "XDG_CONFIG_HOME": str(self.root / "config"),
            "XDG_CACHE_HOME": str(self.root / "xdg-cache"), "EZA_CONFIG_DIR": str(self.root / "eza"),
            "GIT_CONFIG_GLOBAL": str(self.root / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1",
            "XDG_DATA_HOME": str(self.root / "data"), "XDG_STATE_HOME": str(self.root / "state"),
            "TERM": "xterm-256color", "COLORTERM": "truecolor",
        })
        for key in ("BAT_CONFIG_DIR", "BAT_CACHE_PATH", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "EZA_CONFIG_DIR"):
            Path(self.env[key]).mkdir(parents=True)
        Path(self.env["GIT_CONFIG_GLOBAL"]).write_text("", encoding="utf-8")
        self.scheme = migrated("haze")

    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run once, with bounded runtime and no access to the user's configuration."""
        proc = subprocess.run(args, cwd=self.root, env=self.env, capture_output=True, text=True, timeout=45)
        self.assertEqual(proc.returncode, 0, f"{args}:\n{proc.stdout}\n{proc.stderr}")
        return proc

    def test_bat_live_validation_disabled(self) -> None:
        self.skipTest("bat live validation disabled by owner")

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_delta_gitconfig_parses_with_git(self) -> None:
        path = self.root / "delta.gitconfig"
        path.write_text(render("delta", self.scheme)["haze/delta.gitconfig"], encoding="utf-8")
        proc = self.run_tool("git", "config", "-f", str(path), "--list")
        self.assertNotIn("delta.demo-haze.syntax-theme=", proc.stdout)
        self.assertIn(f"delta.demo-haze.plus-style=syntax {self.scheme.resolve('diff_add_bg')}", proc.stdout)

    @unittest.skipUnless(shutil.which("delta"), "delta not installed")
    def test_delta_show_config_uses_feature_styles(self) -> None:
        path = self.root / "delta.gitconfig"
        path.write_text(render("delta", self.scheme)["haze/delta.gitconfig"], encoding="utf-8")
        config = f"[include]\n\tpath = {path}\n[delta]\n\tfeatures = demo-haze\n"
        Path(self.env["GIT_CONFIG_GLOBAL"]).write_text(config, encoding="utf-8")
        # delta's libgit2 may ignore GIT_CONFIG_GLOBAL; HOME remains fully isolated.
        (self.root / ".gitconfig").write_text(config, encoding="utf-8")
        proc = self.run_tool("delta", "--show-config")
        # delta may decorate its diagnostic output; match the actual option values.
        import re
        plain = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout)
        options = dict(tuple(part.strip() for part in line.split(" = ", 1))
                       for line in plain.splitlines() if " = " in line)
        self.assertIn(self.scheme.resolve("diff_add_bg"), options["plus-style"])

    @unittest.skipUnless(shutil.which("lazygit"), "lazygit not installed")
    def test_lazygit_version_with_temporary_config(self) -> None:
        config = Path(self.env["XDG_CONFIG_HOME"]) / "lazygit"
        config.mkdir()
        (config / "config.yml").write_text(render("lazygit", self.scheme)["haze/lazygit.yml"], encoding="utf-8")
        self.assertIn("version", self.run_tool("lazygit", "--version").stdout.lower())

    @unittest.skipUnless(shutil.which("eza"), "eza not installed")
    def test_eza_lists_with_truecolour_theme(self) -> None:
        (Path(self.env["EZA_CONFIG_DIR"]) / "theme.yml").write_text(
            render("eza", self.scheme)["haze/eza.yml"], encoding="utf-8")
        files = self.root / "files"
        files.mkdir()
        (files / "sample.txt").write_text("sample\n", encoding="utf-8")
        (files / "directory").mkdir()
        (files / "link").symlink_to("sample.txt")
        proc = self.run_tool("eza", "-l", "--color=always", str(files))
        self.assertIn("38;2;", proc.stdout)
        self.assertIn("sample.txt", proc.stdout)
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
