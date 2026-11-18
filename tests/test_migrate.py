"""Migration regression (v1 → v2) and assemble_scheme / build_groups parity with legacy gen_schemes."""
import unittest

from cstools.highlights import groups as groups_module
from cstools.highlights.groups import build_groups
from cstools.scheme.assemble import ACCENT_KEYS, assemble_scheme
from cstools.scheme.expr import SchemeError
from cstools.scheme.migrate import migrate_v1, read_recipe_metadata
from cstools.scheme.model import ANSI_NAMES, TERMINAL_KEYS
from support import SCHEME_IDS, legacy, migrated, recipe_path, v1, v1_highlights

LEGACY_ACCENTS = dict(zip(ACCENT_KEYS, ("K", "F", "S", "T", "C", "P", "err", "warn", "info", "hint", "add", "change",
                                        "delete")))


class MigrationRegressionTest(unittest.TestCase):
    def test_highlights_equal_v1_exactly(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                got = {g: st.to_dict() for g, st in build_groups(migrated(sid)).items()}
                want = v1_highlights(sid)
                self.assertEqual(list(got), list(want))
                for group in want:
                    self.assertEqual(got[group], want[group], f"{sid} {group}")

    def test_terminal_equals_v1_exactly(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                scheme, term = migrated(sid), v1(sid)["terminal"]
                for key in TERMINAL_KEYS:
                    self.assertEqual(scheme.terminal_color(key), term[key], key)
                for i, slot in enumerate(ANSI_NAMES):
                    self.assertEqual(scheme.ansi(i), term["normal"][slot], slot)
                    self.assertEqual(scheme.ansi(i + 8), term["bright"][slot], "bright " + slot)

    def test_palette_holds_every_hex_once(self) -> None:
        for sid in SCHEME_IDS:
            scheme = migrated(sid)
            hexes = list(scheme.palette.values())
            self.assertEqual(len(hexes), len(set(hexes)), sid)
            self.assertEqual(list(scheme.palette)[:5], ["bg", "bg_alt", "fg", "fg_dim", "comment"])
            t = scheme.terminal
            self.assertEqual(t["normal"]["black"], {"raise": ["bg_alt", 0.06]})
            self.assertEqual(t["bright"]["white"], {"raise": ["fg", 0.07]})
            self.assertEqual(t["selection_background"], "bg_visual")
            self.assertEqual(t["normal"]["white"], "fg")
            self.assertEqual(t["bright"]["black"], "comment")

    def test_abyss_shared_hex_is_deduplicated(self) -> None:
        scheme = migrated("abyss")  # v1 warning == ansi_yellow
        self.assertEqual(scheme.terminal["normal"]["yellow"], scheme.roles["diagnostic"]["warning"])

    def test_metadata_from_recipe_is_neutral(self) -> None:
        for sid in SCHEME_IDS:
            scheme = migrated(sid)
            meta = read_recipe_metadata(recipe_path(sid))
            self.assertEqual((scheme.name, scheme.description, scheme.family, scheme.tags),
                             (meta["name"], meta["description"], meta["family"], meta["tags"]))
            self.assertEqual(scheme.designed_for["vision"], "deutan")
            self.assertEqual(scheme.designed_for["severity"], 1.0)

    def test_without_recipe_drops_personal_tags(self) -> None:
        scheme = migrate_v1(v1("haze"))
        self.assertNotIn("favourite", scheme.tags)
        self.assertEqual(scheme.family, "haze")

    def test_rejects_non_v1(self) -> None:
        with self.assertRaises(SchemeError):
            migrate_v1({"schema_version": 2})


class LegacyTemplateParityTest(unittest.TestCase):
    """build_groups(assemble_scheme(style)) must equal legacy gen_schemes.groups_for for every legacy style."""

    def test_all_legacy_styles_dark_and_light(self) -> None:
        gen = legacy("gen_schemes")
        for st in gen.STYLES:
            with self.subTest(st["id"]):
                acc = {k: st["a"][LEGACY_ACCENTS[k]] for k in ACCENT_KEYS}
                term = gen.terminal_for(st, st["a"])
                meta = {"id": st["id"], "name": st["name"], "variant": "light" if st.get("light") else "dark"}
                base = {"bg": st["bg"], "bg_alt": st["alt"], "fg": st["fg"], "fg_dim": st["dim"],
                        "comment": st["comment"]}
                styles = {f"{k}_italic": v for k, v in st["italic"].items()}
                scheme = assemble_scheme(meta, base, acc, styles, dict(zip(ANSI_NAMES, term[:8])),
                                         dict(zip(ANSI_NAMES, term[8:])))
                # legacy passes input hex through unchanged (one style uses upper case); cstools lowercases
                want = {g: {k: v.lower() if isinstance(v, str) else v for k, v in e.items() if v}
                        for g, e in gen.groups_for(st, st["a"]).items()}
                got = {g: s.to_dict() for g, s in build_groups(scheme).items()}
                self.assertEqual(got, want)
                self.assertEqual([scheme.ansi(i) for i in range(16)], [h.lower() for h in term])

    def test_plugin_sections_are_discovered(self) -> None:
        self.assertEqual(groups_module.plugin_sections(), [])  # empty package for now


if __name__ == "__main__":
    unittest.main()
