"""Optimiser tests: recipe parsing, search, reference parity (small budgets), light-variant rules, CLI."""
import contextlib
import io as stdio
import random
import tempfile
import tomllib
import unittest
from pathlib import Path

from cstools.cli import main
from cstools.color.spaces import hex_to_oklch
from cstools.optimize.build import optimize_recipe
from cstools.optimize.editor import evaluate_editor, optimize_editor
from cstools.optimize.recipe import Recipe, load_recipe, recipe_from_dict
from cstools.optimize.search import Bounds, climb, search
from cstools.optimize.terminal import (BRIGHT_STEP, DARK_L_CLAMP, EXTREMES, LIGHT_L_MARGINS, anchors_for,
                                       bright_step, optimize_terminal, repair_bright_step)
from cstools.scheme import io
from cstools.scheme.assemble import ACCENT_KEYS, assemble_scheme
from cstools.scheme.model import ANSI_NAMES, UI_ROLES
from cstools.scheme.validate import validate
from support import SCHEME_IDS, migrated, recipe_path, reference, v1

LIGHT_RECIPE = """
schema_version = 1
id = "paper"
name = "Paper"
variant = "light"
family = "paper"
description = "Light test scheme."
tags = ["light"]

[base]
bg = "#e8e5de"
bg_alt = "#dedad2"
fg = "#46443f"
comment = "#8c8981"
fg_dim = "#6b6862"

[styles]
comment_italic = true
keyword_italic = true
parameter_italic = true

[editor]
contrast_min = 3.6
chroma_max = 0.10
hue_tolerance = 35
lightness_min = 0.38
lightness_max = 0.66

[editor.anchors]
keyword = "#5d62a0"
function = "#3f78b0"
string = "#8a6a1e"
type = "#4f7a52"
constant = "#9a5f85"
property = "#5e5a50"
error = "#a5502f"
warning = "#8f6a00"
info = "#3f6fa8"
hint = "#4b7f7a"
git_add = "#3d65a8"
git_change = "#7e5fa8"
git_delete = "#9a6a1a"

[terminal]
contrast_min = 3.6
chroma_max = 0.12
lightness_min = 0.36
lightness_max = 0.62

[optimizer]
seed = 1
iterations = 5000
restarts = 3
terminal_seed = 7
terminal_iterations = 6000
"""


def light_recipe() -> Recipe:
    return recipe_from_dict(tomllib.loads(LIGHT_RECIPE))


class RecipeTest(unittest.TestCase):
    def test_load_fixture(self) -> None:
        r = load_recipe(recipe_path("haze"))
        self.assertEqual((r.id, r.variant, r.family), ("haze", "dark", "haze"))
        self.assertEqual(set(r.base), set(UI_ROLES))
        self.assertEqual(tuple(r.editor.anchors), ACCENT_KEYS)
        self.assertEqual((r.editor.lightness_min, r.editor.lightness_max), (0.58, 0.84))
        self.assertEqual((r.optimizer.seed, r.optimizer.iterations, r.optimizer.restarts), (1, 5000, 3))
        self.assertFalse(r.is_light)
        self.assertTrue(light_recipe().is_light)

    def test_editor_lightness_defaults(self) -> None:
        data = tomllib.loads(LIGHT_RECIPE)
        del data["editor"]["lightness_min"], data["editor"]["lightness_max"]
        r = recipe_from_dict(data)
        self.assertEqual((r.editor.lightness_min, r.editor.lightness_max), (0.60, 0.88))

    def test_missing_fields(self) -> None:
        data = tomllib.loads(LIGHT_RECIPE)
        del data["editor"]["anchors"]["hint"]
        with self.assertRaisesRegex(ValueError, r"editor.anchors\] lacks hint"):
            recipe_from_dict(data)
        data = tomllib.loads(LIGHT_RECIPE)
        del data["terminal"]
        with self.assertRaisesRegex(ValueError, r"missing \[terminal\]"):
            recipe_from_dict(data)
        with self.assertRaisesRegex(ValueError, "variant"):
            recipe_from_dict(tomllib.loads(LIGHT_RECIPE.replace('variant = "light"', 'variant = "dim"')))

    def test_with_budget(self) -> None:
        r = light_recipe().with_budget(iterations=10, seed=3)
        self.assertEqual((r.optimizer.iterations, r.optimizer.terminal_iterations), (10, 10))
        self.assertEqual((r.optimizer.seed, r.optimizer.terminal_seed), (3, 3))
        self.assertEqual(r.optimizer.restarts, 3)
        self.assertEqual(light_recipe().with_budget(), light_recipe())


class SearchTest(unittest.TestCase):
    START = {"a": (0.6, 0.05, 10.0), "b": (0.7, 0.08, 200.0)}

    @staticmethod
    def objective(points, origin) -> float:
        return sum(L + 2 * C for L, C, _ in points.values())

    def test_bounds_respected(self) -> None:
        bounds = Bounds(0.55, 0.75, 0.02, 0.09)
        seen = []

        def objective(points, origin) -> float:
            seen.extend(points.values())
            return self.objective(points, origin)

        result = search(self.START, objective, lambda _k: bounds, 300, restarts=2, seed=5)
        for L, C, h in seen[1:]:
            self.assertTrue(0.55 <= L <= 0.75 and 0.02 <= C <= 0.09 and 0 <= h < 360)
        # the objective rewards L and C, so the climb ends near the upper bounds
        self.assertGreater(min(p[0] for p in result.points.values()), 0.7)

    def test_deterministic(self) -> None:
        bounds = Bounds(0.0, 1.0, 0.0, 0.4)
        a = search(self.START, self.objective, lambda _k: bounds, 200, restarts=3, seed=11)
        b = search(self.START, self.objective, lambda _k: bounds, 200, restarts=3, seed=11)
        c = search(self.START, self.objective, lambda _k: bounds, 200, restarts=3, seed=12)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)

    def test_origin_passed_to_objective(self) -> None:
        origins = []
        climb(self.START, lambda p, o: origins.append(o) or 0.0, lambda _k: Bounds(0, 1, 0, 1), 3,
              random.Random(1), origin={"a": (0.1, 0.1, 0.1), "b": (0.2, 0.2, 0.2)})
        self.assertTrue(all(o["a"] == (0.1, 0.1, 0.1) for o in origins))
        with self.assertRaises(ValueError):
            search(self.START, self.objective, lambda _k: Bounds(0, 1, 0, 1), 1, restarts=0)


class ReferenceParityTest(unittest.TestCase):
    """The ports consume random numbers exactly like the original prototype (frozen in parity/optimize.json)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ref = reference("optimize")

    def test_editor_matches_reference(self) -> None:
        ref = self.ref["editor"]
        self.assertEqual(list(ref), ["haze", "dusk", "light"])
        for sid in ("haze", "dusk"):
            r = load_recipe(recipe_path(sid)).with_budget(iterations=ref[sid]["iterations"])
            self.assertEqual(r.optimizer.iterations, 60)
            self.assertEqual(optimize_editor(r), ref[sid]["accents"], sid)
        r = light_recipe().with_budget(iterations=ref["light"]["iterations"])
        self.assertEqual(r.optimizer.iterations, 40)
        self.assertEqual(optimize_editor(r), ref["light"]["accents"])

    def test_evaluate_matches_reference(self) -> None:
        ref = self.ref["evaluate"]
        r = load_recipe(recipe_path(ref["scheme"]))
        mine = evaluate_editor(r, r.editor.anchors, ref["matrix"])
        self.assertEqual(mine[0], ref["value"][0])
        self.assertEqual(mine[1], ref["value"][1])

    def test_terminal_matches_reference(self) -> None:
        self.assertEqual(list(self.ref["terminal"]), list(SCHEME_IDS))
        for sid in SCHEME_IDS:
            want = self.ref["terminal"][sid]
            r = load_recipe(recipe_path(sid)).with_budget(iterations=want["iterations"])
            self.assertEqual((r.optimizer.terminal_iterations, r.optimizer.terminal_seed), (150, 7))
            accents = {k: v1(sid)["palette"][k]["hex"] for k in ACCENT_KEYS}
            n, b, metrics = want["normal"], want["bright"], want["metrics"]
            mine = optimize_terminal(r, accents)
            repaired, repairs = repair_bright_step(n, b, light=False)
            self.assertEqual((mine.normal, mine.bright, mine.repairs), (n, repaired, repairs), sid)
            if not repairs:
                self.assertEqual(mine.metrics, metrics, sid)
            self.assertEqual(anchors_for(accents), want["anchors"], sid)

    def test_repair_is_noop_on_dark_terminals(self) -> None:
        for sid in SCHEME_IDS:
            s = migrated(sid)
            normal = {x: s.ansi(i) for i, x in enumerate(ANSI_NAMES) if 0 < i < 7}
            bright = {x: s.ansi(i + 8) for i, x in enumerate(ANSI_NAMES) if 0 < i < 7}
            self.assertEqual(repair_bright_step(normal, bright, light=False), (bright, {}), sid)


class LightVariantTest(unittest.TestCase):
    def test_bright_darker_and_bounds(self) -> None:
        r = light_recipe().with_budget(iterations=300)
        accents = optimize_editor(r)
        lo, hi = r.editor.lightness_min - 0.08, r.editor.lightness_max + 0.05
        for k, h in accents.items():
            L, C, _ = hex_to_oklch(h)
            self.assertTrue(lo - 0.005 <= L <= hi + 0.005, (k, L))
            self.assertLessEqual(C, r.editor.chroma_max + 0.005, k)
        term = optimize_terminal(r, accents)
        t = r.terminal
        for x in term.normal:
            self.assertGreaterEqual(bright_step(term.normal[x], term.bright[x], light=True), BRIGHT_STEP, x)
            for h in (term.normal[x], term.bright[x]):
                L = hex_to_oklch(h)[0]
                self.assertTrue(t.lightness_min - LIGHT_L_MARGINS[0] - 0.005 <= L
                                <= t.lightness_max + LIGHT_L_MARGINS[1] + 0.005, (x, L))

    def test_repair_fog_light_yellow(self) -> None:
        # pre-repair full-budget result of the fog-light recipe: bright yellow only 0.0294 darker
        normal, bright = {"yellow": "#a16d04"}, {"yellow": "#936700"}
        self.assertLess(bright_step(normal["yellow"], bright["yellow"], light=True), BRIGHT_STEP)
        fixed, repairs = repair_bright_step(normal, bright, light=True)
        self.assertGreaterEqual(bright_step(normal["yellow"], fixed["yellow"], light=True), BRIGHT_STEP)
        self.assertEqual(repairs, {"yellow": ("#936700", fixed["yellow"])})
        self.assertLess(hex_to_oklch(fixed["yellow"])[0], hex_to_oklch(bright["yellow"])[0])

    def test_repair_limit_warns(self) -> None:
        with self.assertWarnsRegex(UserWarning, "repair limit"):
            repair_bright_step({"red": "#000000"}, {"red": "#000000"}, light=True)

    def test_terminal_extremes_are_expressions(self) -> None:
        s = optimize_recipe(light_recipe().with_budget(iterations=20))
        self.assertEqual(s.variant, "light")
        self.assertEqual(s.terminal["normal"]["black"], {"lighten": ["fg", 0.10]})
        self.assertEqual(s.terminal["normal"]["white"], {"darken": ["bg_alt", 0.06]})
        self.assertEqual(s.terminal["bright"]["black"], "comment")
        self.assertEqual(s.terminal["bright"]["white"], "bg_alt")
        self.assertEqual(validate(io.to_dict(s)), [])


class BuildTest(unittest.TestCase):
    def test_same_seed_same_json(self) -> None:
        r = load_recipe(recipe_path("abyss")).with_budget(iterations=30)
        a, b = io.dumps(optimize_recipe(r)), io.dumps(optimize_recipe(r))
        self.assertEqual(a, b)
        self.assertNotEqual(a, io.dumps(optimize_recipe(r.with_budget(seed=2))))
        s = io.loads(a)
        self.assertEqual(validate(io.to_dict(s)), [])
        self.assertEqual(s.terminal["normal"]["black"], EXTREMES["dark"]["normal.black"])
        self.assertEqual(s.terminal["bright"]["white"], EXTREMES["dark"]["bright.white"])
        self.assertEqual(s.designed_for, {"vision": "deutan", "severity": 1.0,
                                          "metric": "CIEDE2000 on simulated colours"})
        self.assertTrue(s.roles["syntax"]["keyword"].get("italic") is None)  # abyss: keyword_italic = false

    def test_dark_bounds(self) -> None:
        r = load_recipe(recipe_path("fog")).with_budget(iterations=200)
        term = optimize_terminal(r, optimize_editor(r))
        for x in term.normal:
            for h in (term.normal[x], term.bright[x]):
                L, C, _ = hex_to_oklch(h)
                self.assertTrue(DARK_L_CLAMP[0] - 0.005 <= L <= DARK_L_CLAMP[1] + 0.005, (x, L))
                self.assertLessEqual(C, r.terminal.chroma_max + 0.005)

    def test_terminal_formulas_keep_dark_output(self) -> None:
        """``assemble_scheme(terminal_formulas=...)`` with the dark extremes changes nothing for dark schemes."""
        formulas = [v for v in EXTREMES["dark"].values() if isinstance(v, dict)]
        for sid in SCHEME_IDS:
            data = v1(sid)
            base = migrated(sid)
            args = ({"id": sid, "name": base.name, "variant": "dark", "family": base.family,
                     "description": base.description, "tags": base.tags, "designed_for": base.designed_for},
                    {k: data["palette"][k]["hex"] for k in UI_ROLES},
                    {k: data["palette"][k]["hex"] for k in ACCENT_KEYS},
                    {"comment_italic": True, "keyword_italic": True, "parameter_italic": True},
                    data["terminal"]["normal"], data["terminal"]["bright"])
            plain = io.dumps(assemble_scheme(*args))
            self.assertEqual(plain, io.dumps(assemble_scheme(*args, terminal_formulas=formulas)), sid)


class CliOptimizeTest(unittest.TestCase):
    def test_optimize_writes_valid_scheme(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recipe = Path(tmp) / "recipe.toml"
            recipe.write_text(LIGHT_RECIPE, encoding="utf-8")
            out_path = Path(tmp) / "out.json"
            out, err = stdio.StringIO(), stdio.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["optimize", str(recipe), "-o", str(out_path), "--iterations", "15", "--seed", "4"])
            self.assertEqual(code, 0, err.getvalue())
            self.assertIn("editor:", out.getvalue())
            self.assertIn("terminal:", out.getvalue())
            s = io.load(out_path)
            self.assertEqual((s.id, s.variant), ("paper", "light"))
            want = io.dumps(optimize_recipe(light_recipe().with_budget(iterations=15, seed=4)))
            self.assertEqual(out_path.read_text(encoding="utf-8"), want)

    def test_optimize_stdout_and_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            recipe = Path(tmp) / "recipe.toml"
            recipe.write_text(LIGHT_RECIPE, encoding="utf-8")
            out, err = stdio.StringIO(), stdio.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(["optimize", str(recipe), "--iterations", "5"])
            self.assertEqual(code, 0)
            self.assertEqual(io.loads(out.getvalue()).id, "paper")
            self.assertIn("editor:", err.getvalue())
            recipe.write_text(LIGHT_RECIPE.replace("[terminal]", "[term]"), encoding="utf-8")
            with contextlib.redirect_stdout(stdio.StringIO()), contextlib.redirect_stderr(err):
                self.assertNotEqual(main(["optimize", str(recipe)]), 0)
            self.assertIn("missing [terminal]", err.getvalue())


if __name__ == "__main__":
    unittest.main()
