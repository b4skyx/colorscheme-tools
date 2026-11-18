"""Terminal emulator targets: wezterm, ghostty and rio."""
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from cstools.targets import REGISTRY, RenderContext
from support import SCHEME_IDS, migrated, strip_header


def render(target: str, sid: str) -> tuple[str, str]:
    """One rendered file for ``target`` and scheme ``sid``."""
    files = REGISTRY[target].render(migrated(sid), RenderContext(project_name="demo"))
    (path, text), = files.items()
    return path, text


class RegistryTest(unittest.TestCase):
    def test_registered(self) -> None:
        for name in ("wezterm", "ghostty", "rio"):
            self.assertIn(name, REGISTRY)
            self.assertEqual(REGISTRY[name].scope, "scheme")


class WezTermTest(unittest.TestCase):
    def test_structure(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                path, text = render("wezterm", sid)
                self.assertEqual(path, f"{sid}/wezterm.toml")
                data = tomllib.loads(text)
                self.assertEqual(data["metadata"]["name"], migrated(sid).name)
                colors = data["colors"]
                self.assertEqual(len(colors["ansi"]), 8)
                self.assertEqual(len(colors["brights"]), 8)
                for key in ("foreground", "background", "cursor_bg", "cursor_fg", "cursor_border",
                            "selection_fg", "selection_bg", "scrollbar_thumb", "split", "compose_cursor"):
                    self.assertIn(key, colors)
                tab_bar = colors["tab_bar"]
                self.assertIn("background", tab_bar)
                self.assertEqual(set(tab_bar) - {"background"},
                                 {"active_tab", "inactive_tab", "inactive_tab_hover", "new_tab", "new_tab_hover"})
                for section in ("active_tab", "inactive_tab", "inactive_tab_hover", "new_tab", "new_tab_hover"):
                    self.assertEqual(set(tab_bar[section]), {"bg_color", "fg_color"})
                self.assertEqual(text.splitlines()[0].startswith("# "), True)

    def test_header_stripped_is_toml_without_metadata_collision(self) -> None:
        _, text = render("wezterm", "haze")
        self.assertTrue(strip_header(text).lstrip().startswith("[metadata]"))


class GhosttyTest(unittest.TestCase):
    def test_parse(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                path, text = render("ghostty", sid)
                self.assertEqual(path, f"{sid}/ghostty")
                palette: dict[int, str] = {}
                keys: dict[str, str] = {}
                for line in text.splitlines():
                    if not line or line.startswith("#"):
                        continue
                    key, _, value = line.partition(" = ")
                    self.assertTrue(key, line)
                    if key == "palette":
                        index, _, hex_value = value.partition("=")
                        palette[int(index)] = hex_value
                    else:
                        keys[key] = value
                self.assertEqual(sorted(palette), list(range(16)))
                self.assertEqual(set(keys), {"background", "foreground", "cursor-color", "cursor-text",
                                             "selection-background", "selection-foreground"})

    def test_ghostty_validate_config(self) -> None:
        """`ghostty +validate-config` accepts the generated theme (snap needs a $HOME temp dir)."""
        if not shutil.which("ghostty"):
            self.skipTest("ghostty not installed")
        home = Path(tempfile.mkdtemp(prefix="cs-ghostty-"))
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                path, text = render("ghostty", sid)
                config = home / f"{sid}.ghostty"
                config.write_text(text, encoding="utf-8")
                proc = subprocess.run(
                    ["ghostty", "+validate-config", f"--config-file={config}"],
                    capture_output=True, text=True, env={"HOME": str(home), "PATH": "/usr/bin:/snap/bin"})
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class RioTest(unittest.TestCase):
    def test_structure(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                path, text = render("rio", sid)
                self.assertEqual(path, f"{sid}/rio.toml")
                data = tomllib.loads(text)
                colors = data["colors"]
                expected = ({'background', 'foreground', 'cursor', 'vi-cursor',
                             'selection-background', 'selection-foreground',
                             'tabs', 'tabs-foreground', 'tabs-active', 'tabs-active-foreground', 'split'}
                            | {n for n in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")}
                            | {f"light-{n}" for n in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")}
                            | {f"dim-{n}" for n in ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")})
                self.assertEqual(set(colors), expected)
                # dim-* is the normal colour mixed 35% towards the background.
                bg = colors["background"]
                self.assertNotEqual(colors["dim-red"], colors["red"])
                self.assertTrue(all(v.startswith("#") for v in colors.values()))

    def test_tab_colours_present(self) -> None:
        _, text = render("rio", "haze")
        self.assertIn('tabs = "#35373c"', text)


if __name__ == "__main__":
    unittest.main()
