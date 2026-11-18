"""cstools.scheme.naming: deterministic hue-bucket names."""
import unittest

from cstools.scheme.naming import hue_bucket, name_colors


class NamingTest(unittest.TestCase):
    def test_buckets(self) -> None:
        self.assertEqual(hue_bucket("#808080"), "grey")
        self.assertEqual(hue_bucket("#ff0000"), "red")       # OKLCH hue ≈ 29°
        self.assertEqual(hue_bucket("#0000ff"), "indigo")    # ≈ 264°
        self.assertEqual(hue_bucket("#00ff00"), "green")     # ≈ 142°
        self.assertEqual(hue_bucket("#ff00ff"), "magenta")   # ≈ 328°
        self.assertEqual(hue_bucket("#ffff00"), "lime")      # ≈ 110°
        self.assertEqual(hue_bucket("#d1597d"), "rose")      # ≈ 4°, bucket wraps around 0°

    def test_suffixes_by_lightness(self) -> None:
        names = name_colors(["#ff0000", "#800000"])
        self.assertEqual(names, {"#800000": "red_dark", "#ff0000": "red_light"})
        names = name_colors(["#ff0000", "#800000", "#c00000"])
        self.assertEqual(names["#c00000"], "red")
        names = name_colors(["#ff0000", "#800000", "#c00000", "#400000"])
        self.assertEqual(sorted(names.values()), ["red_dark", "red_deep", "red_light", "red_pale"])
        self.assertEqual(names["#400000"], "red_deep")

    def test_deterministic_and_order_independent(self) -> None:
        hexes = ["#7b81b9", "#9ECFFF", "#e2c88a", "#739b69", "#bb8cab", "#6686b9", "#6f99c9"]
        a = name_colors(hexes)
        self.assertEqual(a, name_colors(list(reversed(hexes))))
        self.assertEqual(len(set(a.values())), len(a))
        self.assertIn("#9ecfff", a)


if __name__ == "__main__":
    unittest.main()
