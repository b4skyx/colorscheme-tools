"""Palette renaming keeps every resolved colour and follows the naming ladder."""
import re
import unittest
from pathlib import Path

from cstools.color.spaces import oklch_to_hex
from cstools.highlights.groups import build_groups
from cstools.scheme import io
from cstools.scheme.expr import SchemeError
from cstools.scheme.naming import LADDERS, name_colors
from cstools.scheme.rename import auto_names, rename_palette
from cstools.scheme.validate import validate

THEME_REPO = Path.home() / "colorblind-lab" / "colorschemes"
IDS = ("haze", "fog", "abyss", "dusk", "haze-light", "fog-light", "abyss-light", "dusk-light")


def _schemes():
    for sid in IDS:
        path = THEME_REPO / sid / "colorschemes.json"
        if path.exists():
            yield sid, io.load(path)


class LadderTest(unittest.TestCase):
    def test_four_blues_get_words_not_numbers(self):
        blues = [oklch_to_hex(L, 0.10, 248) for L in (0.35, 0.50, 0.65, 0.80)]
        names = name_colors(blues)
        self.assertEqual(sorted(names.values()), ["blue_dark", "blue_deep", "blue_light", "blue_pale"])

    def test_ladders_are_unique_and_ordered(self):
        for n, ladder in LADDERS.items():
            self.assertEqual(len(ladder), n)
            self.assertEqual(len(set(ladder)), n)


@unittest.skipUnless(THEME_REPO.exists(), "theme repo not present")
class RenameTest(unittest.TestCase):
    def test_resolved_colours_unchanged(self):
        for sid, scheme in _schemes():
            with self.subTest(sid=sid):
                renamed = rename_palette(scheme)
                self.assertEqual(validate(io.to_dict(renamed)), [])
                self.assertEqual([renamed.ansi(i) for i in range(16)], [scheme.ansi(i) for i in range(16)])
                self.assertEqual(build_groups(renamed), build_groups(scheme))

    def test_no_numbered_names_for_small_buckets(self):
        for sid, scheme in _schemes():
            with self.subTest(sid=sid):
                names = rename_palette(scheme).palette
                self.assertFalse([n for n in names if re.search(r"_\\d+$", n)], names)

    def test_ui_names_fixed_and_idempotent(self):
        for sid, scheme in _schemes():
            with self.subTest(sid=sid):
                renamed = rename_palette(scheme)
                for ui in ("bg", "bg_alt", "fg", "fg_dim", "comment"):
                    self.assertIn(ui, renamed.palette)
                self.assertEqual({k: v for k, v in auto_names(renamed).items() if k != v}, {})

    def test_merge_is_rejected(self):
        _, scheme = next(_schemes())
        a, b = [k for k in scheme.palette if k not in ("bg", "bg_alt", "fg", "fg_dim", "comment")][:2]
        with self.assertRaises(SchemeError):
            rename_palette(scheme, {a: "same", b: "same"})


if __name__ == "__main__":
    unittest.main()
