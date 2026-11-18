"""cstools.score: parity with the frozen reference editor and terminal scores (fixtures/parity/score.json)."""
import unittest

from cstools.highlights.groups import build_groups
from cstools.score.editor import score_editor, score_groups
from cstools.score.terminal import score_palette, score_terminal
from cstools.vision.model import VisionModel
from support import SCHEME_IDS, migrated, reference, v1


class ScoreParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ref = reference("score")

    def test_editor_matches_reference(self) -> None:
        cases = self.ref["editor"]
        self.assertEqual([(c["vision"], c["severity"], c["scheme"]) for c in cases],
                         [(m, s, sid) for m, s in (("deutan", 1.0), ("protan", 0.7)) for sid in SCHEME_IDS])
        for case in cases:
            sid, model = case["scheme"], VisionModel(case["vision"], case["severity"])
            with self.subTest(sid=sid, model=model):
                want = dict(case["score"], core_worst=tuple(case["score"]["core_worst"]))
                self.assertEqual(score_editor(migrated(sid), model), want)
                self.assertEqual(score_groups(build_groups(migrated(sid)), model.matrix)[0], want)

    def test_terminal_matches_reference(self) -> None:
        self.assertEqual(list(self.ref["terminal"]), list(SCHEME_IDS))
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                t = v1(sid)["terminal"]
                order = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
                pal = {i: (t["normal"] if i < 8 else t["bright"])[order[i % 8]] for i in range(16)}
                m = VisionModel().matrix
                want = self.ref["terminal"][sid]
                self.assertEqual(score_palette(pal, t["background"], t["foreground"], m), want)
                self.assertEqual(score_terminal(migrated(sid)), want)

    def test_v1_stored_scores_reproduce(self) -> None:
        stored = v1("haze")["scores"]["editor"]
        got = score_editor(migrated("haze"))
        for key, value in stored.items():
            want = list(value) if isinstance(value, list) else value
            self.assertEqual(list(got[key]) if isinstance(got[key], tuple) else got[key], want, key)


if __name__ == "__main__":
    unittest.main()
