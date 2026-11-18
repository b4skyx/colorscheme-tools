"""Migration regression (v1 → v2) and assemble_scheme / build_groups parity with the frozen reference styles."""
import unittest

from cstools.highlights import groups as groups_module
from cstools.highlights.groups import CORE_SECTIONS, build_groups
from cstools.scheme.assemble import ACCENT_KEYS, assemble_scheme
from cstools.scheme.expr import SchemeError
from cstools.scheme.migrate import migrate_v1, read_recipe_metadata
from cstools.scheme.model import ANSI_NAMES, TERMINAL_KEYS
from support import SCHEME_IDS, migrated, recipe_path, reference, v1, v1_highlights


class MigrationRegressionTest(unittest.TestCase):
    def test_highlights_equal_v1_exactly(self) -> None:
        for sid in SCHEME_IDS:
            with self.subTest(sid):
                scheme = migrated(sid)
                got = {g: st.to_dict() for section in CORE_SECTIONS for g, st in section(scheme).items()}
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
        data = v1("haze")
        data["tags"] = list(data["tags"]) + ["favourite"]   # personal label injected at test time
        scheme = migrate_v1(data)
        self.assertNotIn("favourite", scheme.tags)
        self.assertEqual(scheme.family, "haze")

    def test_rejects_non_v1(self) -> None:
        with self.assertRaises(SchemeError):
            migrate_v1({"schema_version": 2})


class ReferenceTemplateParityTest(unittest.TestCase):
    """build_groups(assemble_scheme(style)) must equal the frozen reference groups for every reference style."""

    def test_all_reference_styles_dark_and_light(self) -> None:
        styles_ref = reference("styles")
        self.assertEqual(len(styles_ref), 13)
        self.assertEqual({st["variant"] for st in styles_ref}, {"dark", "light"})
        for st in styles_ref:
            with self.subTest(st["id"]):
                self.assertEqual(tuple(st["accents"]), ACCENT_KEYS)
                term = st["terminal"]
                meta = {"id": st["id"], "name": st["name"], "variant": st["variant"]}
                scheme = assemble_scheme(meta, st["base"], st["accents"], st["styles"],
                                         dict(zip(ANSI_NAMES, term[:8])), dict(zip(ANSI_NAMES, term[8:])))
                # the reference passes input hex through unchanged (one style uses upper case); cstools lowercases
                want = {g: {k: v.lower() if isinstance(v, str) else v for k, v in e.items() if v}
                        for g, e in st["groups"].items()}
                got = {g: s.to_dict() for section in CORE_SECTIONS for g, s in section(scheme).items()}
                self.assertEqual(got, want)
                self.assertEqual([scheme.ansi(i) for i in range(16)], [h.lower() for h in term])

    def test_plugin_sections_are_discovered(self) -> None:
        sections = groups_module.plugin_sections()
        names = {section.__module__.rsplit('.', 1)[-1] for section in sections}
        self.assertEqual(names, {'blink', 'codecompanion', 'copilot_chat', 'diffview', 'editor', 'gitsigns',
                                 'ibl', 'lazy', 'lspsaga', 'mason', 'nvim_tree', 'telescope', 'vimwiki', 'which_key'})
        for sid in SCHEME_IDS:
            scheme = migrated(sid)
            core = {g: style for section in CORE_SECTIONS for g, style in section(scheme).items()}
            full = build_groups(scheme)
            for section in sections:
                self.assertFalse(core.keys() & section(scheme).keys(), section.__module__)
            for name, style in core.items():
                self.assertEqual(full[name], style, f'{sid} {name}')


if __name__ == "__main__":
    unittest.main()
