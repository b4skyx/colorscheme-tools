"""cstools.project: config loading, build, --check and unknown-target handling (temporary repos only)."""
import tempfile
import unittest
from pathlib import Path

from cstools.project import ProjectError, build, load_config, render_repo
from support import write_repo


class ProjectBuildTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = write_repo(Path(self.tmp.name), ["alacritty", "kitty", "not_a_target"])
        self.warnings: list[str] = []

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_config(self) -> None:
        cfg = load_config(self.repo)
        self.assertEqual((cfg.name, cfg.lua_module, cfg.url), ("demo", "demo", ""))
        self.assertEqual(cfg.schemes, ["haze", "fog", "abyss", "dusk"])
        self.assertEqual(cfg.context().lua_module, "demo")

    def test_build_writes_then_is_idempotent(self) -> None:
        changed = build(self.repo, warn=self.warnings.append)
        self.assertEqual(changed, sorted(f"{s}/{f}" for s in ("haze", "fog", "abyss", "dusk")
                                         for f in ("alacritty.toml", "kitty.conf")))
        self.assertTrue((self.repo / "haze" / "kitty.conf").is_file())
        self.assertEqual(len(self.warnings), 1)
        self.assertIn("not_a_target", self.warnings[0])
        self.assertEqual(build(self.repo, check=True, warn=self.warnings.append), [])
        self.assertEqual(build(self.repo, warn=self.warnings.append), [])

    def test_check_reports_without_writing(self) -> None:
        changed = build(self.repo, targets=["kitty"], schemes=["haze"], check=True, warn=self.warnings.append)
        self.assertEqual(changed, ["haze/kitty.conf"])
        self.assertFalse((self.repo / "haze" / "kitty.conf").exists())

    def test_edit_propagates(self) -> None:
        build(self.repo, warn=self.warnings.append)
        path = self.repo / "haze" / "colorschemes.json"
        path.write_text(path.read_text().replace('"bg": "#2d2f33"', '"bg": "#202124"'))
        changed = build(self.repo, schemes=["haze"], warn=self.warnings.append)
        self.assertEqual(changed, ["haze/alacritty.toml", "haze/kitty.conf"])
        self.assertIn("background #202124", (self.repo / "haze" / "kitty.conf").read_text())

    def test_explicit_unknown_target_is_an_error(self) -> None:
        with self.assertRaises(ProjectError):
            render_repo(self.repo, targets=["not_a_target"], warn=self.warnings.append)

    def test_invalid_scheme_is_an_error(self) -> None:
        path = self.repo / "fog" / "colorschemes.json"
        path.write_text(path.read_text().replace('"fg": "ui.fg"', '"fg": "missing"', 1))
        with self.assertRaisesRegex(ProjectError, "missing"):
            render_repo(self.repo, warn=self.warnings.append)

    def test_missing_config(self) -> None:
        with self.assertRaises(ProjectError):
            load_config(Path(self.tmp.name) / "nowhere")


if __name__ == "__main__":
    unittest.main()
