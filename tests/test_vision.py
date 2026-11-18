"""cstools.vision: Machado matrices and VisionModel."""
import unittest

from cstools.vision import cvd
from cstools.vision.model import DEFAULT, VisionModel
from support import legacy


class VisionTest(unittest.TestCase):
    def test_cvd_matrix_matches_legacy(self) -> None:
        old = legacy("cvd")
        for kwargs in ({"deutan": 1.0}, {"protan": 0.6}, {"protan": 0.3, "deutan": 0.8},
                       {"protan": 0.5, "deutan": 0.9, "mix": 0.25}):
            self.assertEqual(cvd.cvd_matrix(**kwargs), old.cvd_matrix(**kwargs))
        self.assertEqual(cvd.de_seen("#a47c63", "#f4da9b", cvd.cvd_matrix(deutan=1.0)),
                         old.de_seen("#a47c63", "#f4da9b", old.cvd_matrix(deutan=1.0)))

    def test_vision_model(self) -> None:
        self.assertEqual(DEFAULT, VisionModel("deutan", 1.0))
        self.assertEqual(VisionModel().matrix, cvd.cvd_matrix(deutan=1.0))
        self.assertEqual(VisionModel("protan", 0.5).matrix, cvd.cvd_matrix(protan=0.5))
        self.assertEqual(VisionModel("tritan", 1.0).matrix, cvd.M_TRITAN)
        self.assertEqual(VisionModel("normal").matrix, cvd.IDENTITY)
        self.assertEqual(VisionModel.from_dict({"type": "protan", "severity": 0.8}), VisionModel("protan", 0.8))
        with self.assertRaises(ValueError):
            VisionModel("bogus")
        with self.assertRaises(ValueError):
            VisionModel("deutan", 1.5)

    def test_simulate_identity(self) -> None:
        self.assertEqual(cvd.simulate("#7b81b9", cvd.IDENTITY), "#7b81b9")


if __name__ == "__main__":
    unittest.main()
