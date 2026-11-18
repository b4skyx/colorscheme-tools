"""cstools.color: numeric parity with the frozen reference outputs in fixtures/parity/color.json."""
import unittest

from cstools.color import contrast, difference, ops, spaces
from support import reference


class ColorParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ref = reference("color")

    def test_conversions_match_reference(self) -> None:
        self.assertEqual(len(self.ref["hexes"]), 308)
        for h, want in zip(self.ref["hexes"], self.ref["conversions"], strict=True):
            lin = spaces.hex_to_linear(h)
            self.assertEqual(lin, want["linear"])
            self.assertEqual(spaces.linear_to_hex(lin), h)
            self.assertEqual(spaces.linear_to_lab(lin), tuple(want["lab"]))
            self.assertEqual(spaces.linear_to_luv(lin), tuple(want["luv"]))
            self.assertEqual(spaces.linear_to_oklab(lin), tuple(want["oklab"]))
            self.assertEqual(spaces.hex_to_oklch(h), tuple(want["oklch"]))
            self.assertEqual(spaces.lab_to_linear(*spaces.linear_to_lab(lin)), want["lab_to_linear"])

    def test_oklch_to_hex_matches_reference(self) -> None:
        self.assertEqual(len(self.ref["oklch_to_hex"]), 300)
        for L, C, h, mapped, unmapped in self.ref["oklch_to_hex"]:
            self.assertEqual(spaces.oklch_to_hex(L, C, h), mapped)
            self.assertEqual(spaces.oklch_to_hex(L, C, h, gamut_map=False), unmapped)

    def test_ops_match_reference(self) -> None:
        self.assertEqual(len(self.ref["ops"]), 308)
        for case in self.ref["ops"]:
            a, b = case["a"], case["b"]
            self.assertEqual(ops.mix(a, b, case["t"]), case["mix"])
            self.assertEqual(ops.shift_lightness(a, case["dL"]), case["shift"])
            self.assertEqual(ops.lighten(a, 0.06), case["plus_06"])
            self.assertEqual(ops.darken(a, 0.06), case["minus_06"])
            self.assertEqual(ops.raise_(a, 0.1, light=False), case["plus_10"])
            self.assertEqual(ops.raise_(a, 0.1, light=True), case["minus_10"])

    def test_difference_and_contrast_match_reference(self) -> None:
        self.assertEqual(len(self.ref["pairs"]), 307)
        for case in self.ref["pairs"]:
            a, b = case["a"], case["b"]
            la, lb = spaces.hex_to_lab(a), spaces.hex_to_lab(b)
            self.assertEqual(difference.ciede2000(la, lb), case["ciede2000"])
            self.assertEqual(contrast.wcag_contrast(a, b), case["contrast"])

    def test_with_chroma_sets_chroma(self) -> None:
        out = ops.with_chroma("#7b81b9", 0.0)
        self.assertLess(spaces.hex_to_oklch(out)[1], 0.003)
        self.assertAlmostEqual(spaces.hex_to_oklch(out)[0], spaces.hex_to_oklch("#7b81b9")[0], places=2)

    def test_is_hex(self) -> None:
        self.assertTrue(spaces.is_hex("#A0b1c2"))
        for bad in ("a0b1c2", "#abc", "#gggggg", 3, None):
            self.assertFalse(spaces.is_hex(bad))


if __name__ == "__main__":
    unittest.main()
