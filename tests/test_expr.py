"""cstools.scheme.expr and Scheme reference resolution."""
import unittest

from cstools.color import ops
from cstools.scheme.expr import SchemeError, check_shape, references
from cstools.scheme.model import ResolvedStyle
from support import migrated


class ExpressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.s = migrated("haze")

    def test_names_role_paths_and_defaults(self) -> None:
        s = self.s
        self.assertEqual(s.resolve("bg"), "#2d2f33")
        self.assertEqual(s.resolve("ui.bg"), "#2d2f33")
        self.assertEqual(s.resolve("syntax.number"), s.resolve("syntax.constant"))
        self.assertEqual(s.resolve("diagnostic.ok"), s.resolve("git.add"))
        self.assertEqual(s.resolve("bg_cursorline"), ops.raise_("#2d2f33", 0.035, light=False))

    def test_operations(self) -> None:
        s = self.s
        bg, fg = s.resolve("bg"), s.resolve("fg")
        self.assertEqual(s.resolve({"mix": ["bg", "fg", 0.25]}), ops.mix(bg, fg, 0.25))
        self.assertEqual(s.resolve({"lighten": ["bg", 0.1]}), ops.lighten(bg, 0.1))
        self.assertEqual(s.resolve({"darken": ["fg", 0.1]}), ops.darken(fg, 0.1))
        self.assertEqual(s.resolve({"raise": ["bg", 0.1]}), ops.lighten(bg, 0.1))
        self.assertEqual(s.resolve({"chroma": ["fg", 0.05]}), ops.with_chroma(fg, 0.05))
        nested = {"mix": [{"raise": ["bg", 0.10]}, "syntax.type", 0.12]}
        self.assertEqual(s.resolve(nested), s.resolve("bg_visual"))

    def test_raise_is_variant_aware(self) -> None:
        s = self.s
        s.variant = "light"
        self.assertTrue(s.is_light)
        self.assertEqual(s.resolve({"raise": ["bg", 0.1]}), ops.darken(s.resolve("bg"), 0.1))

    def test_scheme_derived_overrides_defaults(self) -> None:
        s = self.s
        s.derived["bg_visual"] = {"mix": ["bg", "fg", 0.5]}
        self.assertEqual(s.resolve("bg_visual"), ops.mix(s.resolve("bg"), s.resolve("fg"), 0.5))

    def test_cycles_are_detected(self) -> None:
        s = self.s
        s.derived["a"] = {"lighten": ["b", 0.1]}
        s.derived["b"] = {"mix": ["bg", "a", 0.5]}
        with self.assertRaisesRegex(SchemeError, "cycle"):
            s.resolve("a")
        s.roles["syntax"]["constant"] = {"fg": "syntax.number"}
        with self.assertRaisesRegex(SchemeError, "cycle"):
            s.resolve("syntax.number")

    def test_literals_only_in_palette(self) -> None:
        with self.assertRaisesRegex(SchemeError, "only allowed in palette"):
            self.s.resolve("#123456")
        self.s.derived["x"] = {"mix": ["bg", "#ffffff", 0.5]}
        with self.assertRaisesRegex(SchemeError, "only allowed in palette"):
            self.s.resolve("x")

    def test_bad_shapes(self) -> None:
        for bad in ({"mix": ["bg", 0.5]}, {"spin": ["bg", 1]}, {"mix": ["a", "b", 0.1], "raise": ["a", 1]},
                    {"raise": ["bg", "x"]}, {"raise": ["bg", True]}, "", 5):
            with self.assertRaises(SchemeError, msg=repr(bad)):
                check_shape(bad)
        with self.assertRaisesRegex(SchemeError, "unknown"):
            self.s.resolve("nope")
        with self.assertRaisesRegex(SchemeError, "unknown role"):
            self.s.resolve("syntax.nope")

    def test_references(self) -> None:
        self.assertEqual(list(references({"mix": [{"raise": ["bg", 0.1]}, "syntax.type", 0.12]})),
                         ["bg", "syntax.type"])

    def test_style_and_ansi(self) -> None:
        s = self.s
        kw = s.style("syntax.keyword")
        self.assertEqual(kw, ResolvedStyle(fg=s.resolve("syntax.keyword"), italic=True))
        todo = s.style("syntax.todo")
        self.assertEqual(todo.to_dict(), {"fg": s.resolve("bg"), "bg": s.resolve("diagnostic.warning"), "bold": True})
        self.assertEqual(s.style("diagnostic.error"), ResolvedStyle(fg=s.resolve("diagnostic.error")))
        self.assertEqual(s.ansi(7), s.resolve("fg"))
        self.assertEqual(s.ansi(8), s.resolve("comment"))
        with self.assertRaises(SchemeError):
            s.ansi(16)

    def test_palette_dependencies_and_usage(self) -> None:
        s = self.s
        type_name = s.roles["syntax"]["type"]["fg"]
        self.assertEqual(s.palette_dependencies("bg_visual"), {"bg", type_name})
        usage = s.palette_usage()
        self.assertIn("syntax.module", usage[type_name])
        self.assertIn("terminal.normal.black", usage["bg_alt"])


if __name__ == "__main__":
    unittest.main()
