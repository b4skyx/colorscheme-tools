"""cstools.color: numeric parity with legacy/cvd.py."""
import random
import unittest

from cstools.color import contrast, difference, ops, spaces
from support import legacy


def sample_hexes(n: int = 300, seed: int = 3) -> list[str]:
    rnd = random.Random(seed)
    fixed = ["#000000", "#ffffff", "#808080", "#ff0000", "#00ff00", "#0000ff", "#2d2f33", "#c0bdb5"]
    return fixed + ["#%06x" % rnd.randrange(0x1000000) for _ in range(n)]


class ColorParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cvd = legacy("cvd")
        cls.hexes = sample_hexes()

    def test_conversions_match_legacy(self) -> None:
        for h in self.hexes:
            lin = spaces.hex_to_linear(h)
            self.assertEqual(lin, self.cvd.hex2lin(h))
            self.assertEqual(spaces.linear_to_hex(lin), h)
            self.assertEqual(spaces.linear_to_lab(lin), self.cvd.lin2lab(lin))
            self.assertEqual(spaces.linear_to_luv(lin), self.cvd.lin2luv(lin))
            self.assertEqual(spaces.linear_to_oklab(lin), self.cvd.lin2oklab(lin))
            self.assertEqual(spaces.hex_to_oklch(h), self.cvd.hex2oklch(h))
            self.assertEqual(spaces.lab_to_linear(*spaces.linear_to_lab(lin)),
                             self.cvd.lab2lin(*self.cvd.lin2lab(lin)))

    def test_oklch_to_hex_matches_legacy(self) -> None:
        rnd = random.Random(5)
        for _ in range(300):
            L, C, h = rnd.uniform(0, 1), rnd.uniform(0, 0.35), rnd.uniform(0, 360)
            self.assertEqual(spaces.oklch_to_hex(L, C, h), self.cvd.oklch2hex(L, C, h))
            self.assertEqual(spaces.oklch_to_hex(L, C, h, gamut_map=False), self.cvd.oklch2hex(L, C, h, False))

    def test_ops_match_legacy(self) -> None:
        rnd = random.Random(9)
        for a, b in zip(self.hexes, reversed(self.hexes)):
            t, dL = rnd.uniform(0, 1), rnd.uniform(-0.2, 0.2)
            self.assertEqual(ops.mix(a, b, t), self.cvd.mix_hex(a, b, t))
            self.assertEqual(ops.shift_lightness(a, dL), self.cvd.shift_l(a, dL))
            self.assertEqual(ops.lighten(a, 0.06), self.cvd.shift_l(a, 0.06))
            self.assertEqual(ops.darken(a, 0.06), self.cvd.shift_l(a, -0.06))
            self.assertEqual(ops.raise_(a, 0.1, light=False), self.cvd.shift_l(a, 0.1))
            self.assertEqual(ops.raise_(a, 0.1, light=True), self.cvd.shift_l(a, -0.1))

    def test_difference_and_contrast_match_legacy(self) -> None:
        for a, b in zip(self.hexes, self.hexes[1:]):
            la, lb = spaces.hex_to_lab(a), spaces.hex_to_lab(b)
            self.assertEqual(difference.ciede2000(la, lb), self.cvd.ciede2000(la, lb))
            self.assertEqual(contrast.wcag_contrast(a, b), self.cvd.contrast(a, b))

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
