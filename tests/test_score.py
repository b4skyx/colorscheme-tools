"""cstools.score: parity with legacy editor_score.score and score_themes.score."""
import unittest

from cstools.highlights.groups import build_groups
from cstools.score.editor import score_editor, score_groups
from cstools.score.terminal import score_palette, score_terminal
from cstools.vision.model import VisionModel
from support import SCHEME_IDS, legacy, migrated, v1, v1_highlights


class ScoreParityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cvd, cls.editor, cls.term = legacy("cvd"), legacy("editor_score"), legacy("score_themes")

    def test_editor_matches_legacy(self) -> None:
        for model in (VisionModel(), VisionModel("protan", 0.7)):
            for sid in SCHEME_IDS:
                with self.subTest(sid=sid, model=model):
                    want, _ = self.editor.score({"groups": v1_highlights(sid)}, model.matrix)
                    self.assertEqual(score_editor(migrated(sid), model), want)
                    self.assertEqual(score_groups(build_groups(migrated(sid)), model.matrix)[0], want)

    def test_terminal_matches_legacy(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                t = v1(sid)["terminal"]
                order = ["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]
                pal = {i: (t["normal"] if i < 8 else t["bright"])[order[i % 8]] for i in range(16)}
                m = VisionModel().matrix
                want = self.term.score({"pal": pal, "background": t["background"], "foreground": t["foreground"]}, m)
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
