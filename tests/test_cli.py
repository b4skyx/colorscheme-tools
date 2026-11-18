"""CLI smoke tests (in-process, temporary directories only)."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cstools.cli import main
from support import FIXTURES, ROOT, migrated, recipe_path, strip_header, write_repo


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_migrate_validate_render(self) -> None:
        out = self.dir / "haze" / "colorschemes.json"
        out.parent.mkdir()
        code, _, err = run("migrate", str(FIXTURES / "v1" / "haze.json"), "-o", str(out),
                           "--recipe", str(recipe_path("haze")))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out.read_text())["schema_version"], 2)
        self.assertEqual(run("validate", str(out))[0], 0)
        code, _, err = run("validate", str(FIXTURES / "v1" / "haze.json"))
        self.assertEqual(code, 1)
        self.assertIn("migrate", err)
        code, text, _ = run("render", str(out), "--target", "kitty")
        self.assertEqual(code, 0)
        golden = (FIXTURES / "golden" / "haze.kitty.conf").read_text()
        self.assertEqual(strip_header(text), strip_header(golden))
        code, _, _ = run("render", str(out), "--target", "alacritty", "--out", str(self.dir / "rendered"))
        self.assertTrue((self.dir / "rendered" / "haze" / "alacritty.toml").is_file())
        self.assertEqual(run("render", str(out), "--target", "nope")[0], 2)

    def test_migrate_stdout(self) -> None:
        code, text, _ = run("migrate", str(FIXTURES / "v1" / "dusk.json"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["id"], "dusk")

    def test_build_and_check(self) -> None:
        repo = write_repo(self.dir / "repo", ["alacritty", "kitty", "later_target"], ("haze",))
        code, _, _ = run("build", str(repo), "--check")
        self.assertEqual(code, 1)
        code, text, err = run("build", str(repo))
        self.assertEqual(code, 0)
        self.assertIn("changed: haze/kitty.conf", text)
        self.assertIn("later_target", err)
        code, text, _ = run("build", str(repo), "--check", "--targets", "kitty,alacritty")
        self.assertEqual((code, text.strip()), (0, "up to date"))

    def test_score_inspect_targets(self) -> None:
        path = self.dir / "abyss.json"
        from cstools.scheme import io as scheme_io
        scheme_io.dump(migrated("abyss"), path)
        code, text, _ = run("score", str(path), "--json")
        self.assertEqual(code, 0)
        data = json.loads(text)
        self.assertEqual(data["model"], {"type": "deutan", "severity": 1.0})
        self.assertIn("syntax_kept", data["editor"])
        self.assertIn("minN", data["terminal"])
        model = self.dir / "model.json"
        model.write_text('{"type": "protan", "severity": 0.5}')
        code, text, _ = run("score", str(path), "--model", str(model))
        self.assertEqual(code, 0)
        self.assertIn("protan", text)
        code, text, _ = run("inspect", str(path))
        self.assertEqual(code, 0)
        self.assertIn("terminal.normal.black", text)
        code, text, _ = run("inspect", str(path), "--json")
        self.assertIn("used_by", json.loads(text)["bg"])
        code, text, _ = run("targets")
        self.assertIn("alacritty", text)

    def test_stubs_exit_2(self) -> None:
        self.assertEqual(run("gallery", "repo")[0], 2)

    def test_python_dash_m(self) -> None:
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run([sys.executable, "-m", "cstools", "targets"], capture_output=True, text=True, env=env,
                              cwd=self.dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("kitty", proc.stdout)


if __name__ == "__main__":
    unittest.main()
