"""Shell targets: tmux, fish, starship and fzf — structure plus live-binary validation."""
from __future__ import annotations

import shutil
import subprocess
import tomllib
import unittest

from cstools.targets import REGISTRY
from cstools.targets.base import RenderContext
from support import SCHEME_IDS, migrated

CTX = RenderContext(project_name="demo", lua_module="clearsight")

TMUX_STYLE_OPTIONS = ("status-style", "status-left-style", "status-right-style", "window-status-style",
                      "window-status-current-style", "window-status-activity-style", "window-status-bell-style",
                      "pane-border-style", "pane-active-border-style", "message-style", "message-command-style",
                      "mode-style", "copy-mode-match-style", "copy-mode-current-match-style", "popup-style",
                      "popup-border-style", "menu-style", "menu-selected-style", "menu-border-style")
TMUX_COLOUR_OPTIONS = ("display-panes-colour", "display-panes-active-colour", "clock-mode-colour")
TMUX_USER_ROLES = ("bg", "bg_alt", "fg", "fg_dim", "comment", "accent", "error", "warning", "info", "hint", "add",
                   "change", "delete")

FISH_COLORS = ("normal", "command", "keyword", "quote", "redirection", "end", "error", "param", "valid_path",
               "option", "comment", "selection", "operator", "escape", "autosuggestion", "cwd", "cwd_root", "user",
               "host", "host_remote", "status", "cancel", "search_match", "history_current")
FISH_PAGER_COLORS = ("progress", "background", "prefix", "completion", "description", "selected_background",
                     "selected_prefix", "selected_completion", "selected_description", "secondary_background",
                     "secondary_prefix", "secondary_completion", "secondary_description")

FZF_KEYS = ("fg", "bg", "hl", "fg+", "bg+", "hl+", "info", "prompt", "pointer", "marker", "spinner", "header",
            "border", "gutter", "query", "label", "separator", "scrollbar", "preview-fg", "preview-bg")


def render_one(target: str, sid: str, path: str) -> str:
    """Render one target for one scheme and return the text of the single expected file."""
    files = REGISTRY[target].render(migrated(sid), CTX)
    assert path in files, f"{path} missing from {target} output: {sorted(files)}"
    return files[path]


class TmuxTargetTest(unittest.TestCase):
    def test_styles_and_user_options(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                text = render_one("tmux", sid, f"{sid}/tmux.conf")
                body = {line.split(" ", 3)[2]: line.split(" ", 3)[3]
                        for line in text.splitlines() if line.startswith("set -g ")}
                for option in TMUX_STYLE_OPTIONS + TMUX_COLOUR_OPTIONS:
                    self.assertIn(option, body)
                self.assertIn("bold", body["window-status-current-style"])
                for role in TMUX_USER_ROLES:
                    self.assertIn(f"set -g @clearsight_{role} ", text)
                for line in text.splitlines():
                    if not line.startswith("set -g "):
                        continue
                    value = line.split(None, 3)[3]
                    if value.startswith('"'):
                        self.assertTrue(value.endswith('"'), line)  # plain-colour/user options are quoted
                    else:
                        self.assertNotIn('"', line)

    def test_source_file_accepted_by_tmux(self) -> None:
        if not shutil.which("tmux"):
            self.skipTest("tmux not installed")
        for sid in SCHEME_IDS:
            path = f"/tmp/cstools-test-{sid}.tmux.conf"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(render_one("tmux", sid, f"{sid}/tmux.conf"))
            socket = f"cs-test-{id(self)}"
            cmd = ["tmux", "-L", socket, "-f", "/dev/null", "start-server", ";", "source-file", path, ";",
                   "show", "-g", "status-style", ";", "kill-server"]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertIn("status-style", proc.stdout)
                self.assertNotIn("empty value", proc.stdout + proc.stderr)
                self.assertNotIn("invalid", proc.stdout + proc.stderr)
            finally:
                subprocess.run(["tmux", "-L", socket, "kill-server"], capture_output=True)


class FishTargetTest(unittest.TestCase):
    def test_names_and_args(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                text = render_one("fish", sid, f"{sid}/fish.theme")
                self.assertIn(f"# name: '{migrated(sid).name}'", text)
                entries = {}
                for line in text.splitlines():
                    if line.startswith("# name:") or not line or line.startswith("# Generated"):
                        continue
                    if line.startswith("#"):
                        continue
                    name, _, args = line.partition(" ")
                    entries[name] = args
                    self.assertNotIn("#", args, f"fish theme hex must be bare: {line}")
                for name in FISH_COLORS:
                    self.assertIn(f"fish_color_{name}", entries)
                for name in FISH_PAGER_COLORS:
                    self.assertIn(f"fish_pager_color_{name}", entries)
                self.assertTrue(entries["fish_color_valid_path"].endswith("--underline"))

    def test_set_color_accepts_every_line(self) -> None:
        if not shutil.which("fish"):
            self.skipTest("fish not installed")
        script = (
            'for line in (cat $argv[1])\n'
            '    if string match -q "#*" -- $line; or test -z "$line"; continue; end\n'
            '    set -l parts (string split " " -- $line)\n'
            '    if not string match -q "fish_*color*" -- $parts[1]; echo "bad name: $parts[1]"; exit 1; end\n'
            '    set_color $parts[2..-1] >/dev/null; or begin; echo "bad colour: $line"; exit 1; end\n'
            'end\n'
        )
        script_path = "/tmp/cstools-test-setcolor.fish"
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(script)
        for sid in SCHEME_IDS:
            path = f"/tmp/cstools-test-{sid}.fish.theme"
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(render_one("fish", sid, f"{sid}/fish.theme"))
            proc = subprocess.run(["fish", "--no-config", script_path, path],
                                  capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class StarshipTargetTest(unittest.TestCase):
    def test_palette_table(self) -> None:
        expected = ("bg", "fg", "comment", "accent", "error", "warning", "info", "hint", "success",
                    "black", "red", "green", "yellow", "blue", "purple", "cyan", "white",
                    "bright_black", "bright_red", "bright_green", "bright_yellow", "bright_blue",
                    "bright_purple", "bright_cyan", "bright_white")
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                text = render_one("starship", sid, f"{sid}/starship.toml")
                data = tomllib.loads(text)
                palette = data["palettes"][sid]
                self.assertEqual(set(palette), set(expected))
                self.assertTrue(all(v.startswith("#") and len(v) == 7 for v in palette.values()))
                scheme = migrated(sid)
                self.assertEqual(palette["success"], scheme.resolve("git.add"))
                self.assertEqual(palette["purple"], scheme.ansi(5))
                self.assertEqual(palette["bright_white"], scheme.ansi(15))


class FzfTargetTest(unittest.TestCase):
    def test_color_option_keys(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                text = render_one("fzf", sid, f"{sid}/fzf.sh")
                fish_text = render_one("fzf", sid, f"{sid}/fzf.fish")
                for body in (text, fish_text):
                    self.assertIn("FZF_DEFAULT_OPTS", body)
                    self.assertIn("--color=", body)
                spec = text.split("--color=", 1)[1].strip().strip('"')
                pairs = dict(item.split(":", 1) for item in spec.split(","))
                self.assertEqual(set(pairs), set(FZF_KEYS))
                self.assertTrue(all(v.startswith("#") for v in pairs.values()))

    def test_fzf_filter_accepts_options(self) -> None:
        if not shutil.which("fzf"):
            self.skipTest("fzf not installed")
        from cstools.targets.fzf import color_option
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                proc = subprocess.run(["fzf", "--filter", "a", f"--color={color_option(migrated(sid))}"],
                                      input="abc\n", capture_output=True, text=True, timeout=30)
                self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
