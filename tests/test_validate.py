"""cstools.scheme.validate, io round-trip and the JSON Schema file."""
import copy
import json
import unittest

from cstools.scheme import io
from cstools.scheme.validate import validate
from support import ROOT, SCHEME_IDS, migrated


class ValidateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = io.to_dict(migrated("haze"))

    def errors_after(self, mutate) -> list[str]:
        data = copy.deepcopy(self.data)
        mutate(data)
        return validate(data)

    def test_migrated_fixtures_are_valid(self) -> None:
        for sid in SCHEME_IDS:
            self.assertEqual(validate(io.to_dict(migrated(sid))), [], sid)

    def test_duplicate_palette_hex(self) -> None:
        errs = self.errors_after(lambda d: d["palette"].__setitem__("copy", d["palette"]["bg"].upper()))
        self.assertTrue(any("duplicate" in e for e in errs), errs)

    def test_unresolvable_reference(self) -> None:
        errs = self.errors_after(lambda d: d["roles"]["git"].__setitem__("add", "missing_colour"))
        self.assertTrue(any("roles.git.add" in e and "unknown" in e for e in errs), errs)

    def test_cycle(self) -> None:
        def mutate(d):
            d["derived"] = {"a": {"raise": ["b", 0.1]}, "b": {"raise": ["a", 0.1]}}
        errs = self.errors_after(mutate)
        self.assertTrue(any("cycle" in e for e in errs), errs)

    def test_literals_outside_palette(self) -> None:
        errs = self.errors_after(lambda d: d["terminal"]["normal"].__setitem__("red", "#ff0000"))
        self.assertTrue(any("terminal.normal.red" in e and "palette" in e for e in errs), errs)
        errs = self.errors_after(lambda d: d["roles"]["syntax"]["string"].__setitem__("fg", {"mix": ["bg", "#000000", 1]}))
        self.assertTrue(any("roles.syntax.string.fg" in e for e in errs), errs)

    def test_structure(self) -> None:
        self.assertTrue(self.errors_after(lambda d: d.pop("terminal")))
        self.assertTrue(self.errors_after(lambda d: d.__setitem__("variant", "dim")))
        self.assertTrue(self.errors_after(lambda d: d.__setitem__("schema_version", 1)))
        self.assertTrue(self.errors_after(lambda d: d["roles"]["syntax"].pop("keyword")))
        self.assertTrue(self.errors_after(lambda d: d["roles"]["syntax"]["keyword"].__setitem__("italic", "yes")))
        self.assertTrue(self.errors_after(lambda d: d["terminal"]["bright"].pop("cyan")))
        self.assertTrue(self.errors_after(lambda d: d["palette"].__setitem__("Bad-Name", "#010203")))
        self.assertTrue(self.errors_after(lambda d: d.__setitem__("scores", {})))
        self.assertEqual(validate([]), ["scheme must be a JSON object"])

    def test_io_round_trip_and_key_order(self) -> None:
        scheme = migrated("abyss")
        text = io.dumps(scheme)
        self.assertEqual(io.dumps(io.loads(text)), text)
        keys = list(json.loads(text))
        self.assertEqual(keys, ["schema_version", "id", "name", "variant", "family", "description", "tags",
                                "designed_for", "palette", "roles", "terminal"])
        scheme.extra["$schema"] = "../schema/colorscheme.schema.json"
        self.assertEqual(list(json.loads(io.dumps(scheme)))[0], "$schema")

    def test_schema_file_is_json(self) -> None:
        schema = json.loads((ROOT / "schema" / "colorscheme.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(set(schema["required"]), {"schema_version", "id", "name", "variant", "palette", "roles",
                                                   "terminal"})


if __name__ == "__main__":
    unittest.main()
