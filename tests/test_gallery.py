"""Offline gallery: payloads, legacy dumps, CLI, packaged UI and browser smoke tests."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path

from cstools.cli import main
from cstools.gallery import build_gallery, gallery_data
from cstools.highlights.groups import build_groups
from cstools.project import ProjectError, load_scheme
from cstools.scheme import io as scheme_io
from cstools.score.editor import score_editor
from cstools.score.terminal import score_palette, score_terminal
from cstools.vision.model import VisionModel
from support import migrated, write_repo

THEME_REPO = Path.home() / "colorblind-lab" / "colorschemes"
ASSETS = files("cstools.gallery").joinpath("assets")


def payload(output: Path) -> dict:
    """Parse the external script assignment without executing JavaScript."""
    text = (output / "gallery_data.js").read_text(encoding="utf-8")
    assert text.startswith("window.GALLERY_DATA = ") and text.endswith(";\n")
    return json.loads(text.removeprefix("window.GALLERY_DATA = ").removesuffix(";\n"))


class GalleryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = write_repo(self.root / "repo", [], ("haze", "fog"))
        self.output = self.root / "gallery"
        self.dumps = self.root / "dumps"
        self.dumps.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_dump(self, name: str = "haze", terminal: list | None = None) -> Path:
        scheme = migrated("haze")
        data = {"name": '<Comparison "theme">', "background": "dark",
                "groups": {n: s.to_dict() for n, s in build_groups(scheme).items()}}
        if terminal is not None:
            data["terminal"] = terminal
        path = self.dumps / f"{name}.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_build_uses_resolved_scheme_data_and_scores(self) -> None:
        paths = build_gallery(self.repo, self.output)
        self.assertEqual([p.name for p in paths], ["index.html", "gallery_data.js"])
        self.assertTrue(all(p.is_file() for p in paths))
        data = payload(self.output)
        scheme = load_scheme(self.repo / "haze" / "colorschemes.json")
        entry = data["schemes"][0]
        self.assertEqual(entry["groups"], {n: s.to_dict() for n, s in build_groups(scheme).items()})
        self.assertGreaterEqual(len(entry["groups"]), 700)
        self.assertEqual(entry["terminal"], [scheme.ansi(i) for i in range(16)])
        self.assertEqual(entry["score"], json.loads(json.dumps(score_editor(scheme))))
        self.assertEqual(entry["term_score"], score_terminal(scheme))
        self.assertEqual(entry["roles"]["syntax.function"], scheme.resolve("syntax.function"))
        self.assertEqual(entry["description"], scheme.description)
        self.assertEqual(entry["tags"], scheme.tags)
        self.assertEqual(entry["variant"], scheme.variant)
        self.assertEqual(data["project"], "demo")
        self.assertEqual(data["model"]["type"], "deutan")

    def test_family_counterparts_are_adjacent(self) -> None:
        for sid in ("haze", "fog"):
            scheme = migrated(sid)
            scheme.id += "-light"
            scheme.variant = "light"
            path = self.repo / scheme.id / "colorschemes.json"
            path.parent.mkdir()
            scheme_io.dump(scheme, path)
        config = self.repo / "colorschemes.toml"
        config.write_text(config.read_text().replace('["haze", "fog"]',
                                                     '["fog-light", "haze", "fog", "haze-light"]'))
        data = gallery_data(self.repo)
        self.assertEqual([s["id"] for s in data["schemes"]], ["fog", "fog-light", "haze", "haze-light"])

    def test_extra_dumps_are_scored_namespaced_sorted_and_deterministic(self) -> None:
        terminal = [migrated("haze").ansi(i) for i in range(16)]
        self.write_dump("z-last", terminal)
        self.write_dump("haze", terminal)
        build_gallery(self.repo, self.output, self.dumps)
        data = payload(self.output)
        self.assertEqual([s["id"] for s in data["schemes"]][-2:], ["comparison:haze", "comparison:z-last"])
        comparison = data["schemes"][-1]
        self.assertEqual(comparison["kind"], "comparison")
        self.assertEqual(comparison["terminal"], terminal)
        self.assertFalse(comparison["terminal_inferred"])
        self.assertEqual(comparison["score"], data["schemes"][0]["score"])
        self.assertEqual(comparison["term_score"], data["schemes"][0]["term_score"])
        other = self.root / "other"
        build_gallery(self.repo, other, self.dumps)
        for name in ("index.html", "gallery_data.js"):
            self.assertEqual((self.output / name).read_bytes(), (other / name).read_bytes())

    def test_partial_and_missing_dump_terminal_uses_editor_roles(self) -> None:
        for terminal in (None, [], [None, "#123456"]):
            with self.subTest(terminal=terminal):
                self.write_dump(terminal=terminal)
                comparison = gallery_data(self.repo, self.dumps)["schemes"][-1]
                self.assertEqual(len(comparison["terminal"]), 16)
                self.assertTrue(comparison["terminal_inferred"])
                if terminal:
                    self.assertEqual(comparison["terminal"][1], "#123456")
                expected = score_palette(dict(enumerate(comparison["terminal"])),
                                         comparison["groups"]["Normal"]["bg"],
                                         comparison["groups"]["Normal"]["fg"], VisionModel().matrix)
                self.assertEqual(comparison["term_score"], expected)

    def test_invalid_dumps_and_missing_directory_are_actionable(self) -> None:
        path = self.dumps / "broken.json"
        normal = {"Normal": {"fg": "#dddddd", "bg": "#222222"}}
        invalid = [[], {}, {"groups": {"Normal": []}}, {"groups": {}},
                   {"groups": {"Normal": {"fg": "invalid"}}},
                   {"groups": {"Normal": {**normal["Normal"], "bold": "yes"}}},
                   {"groups": normal, "terminal": ["red"]},
                   {"groups": normal, "terminal": [None] * 17},
                   {"groups": normal, "terminal": "palette"},
                   {"groups": normal, "background": "sepia"},
                   {"groups": normal, "name": 123}]
        for data in invalid:
            with self.subTest(data=data):
                path.write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError, "broken.json"):
                    gallery_data(self.repo, self.dumps)
        with self.assertRaisesRegex(ValueError, "directory not found"):
            gallery_data(self.repo, self.root / "absent")
        with self.assertRaises(ProjectError):
            gallery_data(self.root / "absent")

    def test_cli_model_and_required_output(self) -> None:
        model_path = self.root / "model.json"
        model_path.write_text('{"type": "protan", "severity": 0.6}')
        self.write_dump()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = main(["gallery", str(self.repo), "-o", str(self.output),
                         "--extra-dumps", str(self.dumps), "--model", str(model_path)])
            self.assertEqual(main(["gallery", str(self.repo)]), 2)
        self.assertEqual(code, 0)
        data = payload(self.output)
        model = VisionModel("protan", 0.6)
        self.assertEqual(data["model"], {"type": "protan", "severity": 0.6, "matrix": model.matrix})
        self.assertEqual(data["schemes"][0]["term_score"], score_terminal(migrated("haze"), model))
        self.assertEqual(data["schemes"][0]["score"], json.loads(json.dumps(score_editor(migrated("haze"), model))))
        comparison = data["schemes"][-1]
        self.assertEqual(comparison["score"], data["schemes"][0]["score"])

    def test_assets_are_packaged_neutral_and_keep_prototype_features(self) -> None:
        html = ASSETS.joinpath("gallery.html").read_text(encoding="utf-8")
        self.assertTrue(ASSETS.joinpath("dump.lua").is_file())
        self.assertIn("nvim --headless", ASSETS.joinpath("README.md").read_text(encoding="utf-8"))
        self.assertNotRegex(html.lower(), r"\b(your|favourite|for you)\b")
        for feature in ("☀ Light", "Comparison themes", "localStorage", "renderDiff", "renderTerm",
                        "lex(src, lang)", "renderEditor", "legendHTML", "feColorMatrix", "downloadPicks"):
            self.assertIn(feature, html)
        self.assertNotIn('fetch("gallery_data.json")', html)
        self.assertIn('<script src="gallery_data.js">', html)

    @unittest.skipUnless(shutil.which("node"), "node not installed (JavaScript smoke test)")
    def test_javascript_views_filters_storage_and_offline_export(self) -> None:
        self.write_dump()
        build_gallery(self.repo, self.output, self.dumps)
        harness = r'''
const fs = require("fs"), vm = require("vm"), assert = require("assert");
const html = fs.readFileSync(process.argv[1], "utf8");
const data = fs.readFileSync(process.argv[2], "utf8");
async function check(storageMode) {
  const elements = new Map(), downloads = [], posts = [], writes = [], blobs = [], alerts = [];
  let apiMode = "unavailable";
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML: "", textContent: "", dataset: {}, classList: { toggle() {} },
      querySelectorAll() { return []; }, setAttribute(key, value) { this[key] = value; },
      click() { downloads.push(this.download); }, remove() {}
    });
    return elements.get(id);
  };
  const document = { getElementById: element, querySelectorAll() { return []; },
    createElement: tag => element(tag), body: { append() {}, prepend() {} } };
  const localStorage = { getItem() {
    if (storageMode === "denied") throw new Error("storage denied");
    if (storageMode === "malformed") return "not JSON";
    return '{"haze":{"stars":999,"note":"</textarea><script>unsafe</script>"}}';
  }, setItem(key, value) {
    if (storageMode === "denied") throw new Error("storage denied");
    writes.push(JSON.parse(value));
  } };
  const location = { protocol: "file:", search: "?lang=invalid&mode=bad" };
  class FakeURL extends URL {}
  FakeURL.createObjectURL = blob => { blobs.push(blob); return "blob:test"; };
  FakeURL.revokeObjectURL = () => {};
  const context = vm.createContext({ window: {}, document, localStorage, location, console,
    URLSearchParams, URL: FakeURL, Blob, AbortController, alert(text) { alerts.push(text); },
    setTimeout(fn) { return 1; }, clearTimeout() {},
    async fetch(url) {
      posts.push(url);
      if (apiMode === "reject") throw new Error("network unavailable");
      return { ok: apiMode !== "unavailable", async json() {
        if (apiMode === "invalid") throw new Error("not JSON");
        return { saved: "picks.json" };
      } };
    } });
  vm.runInContext(data, context);
  for (const match of html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)) {
    vm.runInContext(match[1], context);
  }
  const run = code => vm.runInContext(code, context);
  assert(element("view").innerHTML.includes("gcard"));
  if (storageMode === "valid") assert.strictEqual(run('ratings.haze.stars'), 5);
  for (const lang of ["lua", "python", "ts", "rust"]) {
    run(`state.mode = "detail"; state.lang = "${lang}"; state.cmp = "comparison:haze"; state.sim = true; render();`);
    const view = element("view").innerHTML;
    for (const feature of ["panes two", 'class="pm"', 'class="status"', 'class="vt"',
      "Inline diff", "Terminal (ANSI", "Roles", "filter:url(#sim)"]) assert(view.includes(feature), feature);
    assert(!view.includes('<Comparison "theme">'));
    assert(!view.includes("</textarea><script>unsafe"));
  }
  run('state.filter = "light"; render();');
  assert(element("view").innerHTML.includes("No schemes match"));
  run('state.filter = "comparison"; render();');
  assert(element("view").innerHTML.includes("&lt;Comparison &quot;theme&quot;&gt;"));
  run('ratings.haze = { stars: 4, fav: true, note: "note" }; saveLocal(); state.filter = "picked"; render();');
  assert.strictEqual(run('filtered().length'), 1);
  if (storageMode === "denied") assert(element("ratedc").textContent.includes("Local storage unavailable"));
  else assert(writes.length > 0);
  await element("save").onclick();
  assert.deepStrictEqual(downloads, ["gallery-picks.json"]);
  assert.strictEqual(posts.length, 0);
  assert.strictEqual(JSON.parse(await blobs[0].text()).ratings.haze.stars, 4);
  location.protocol = "https:";
  for (apiMode of ["unavailable", "reject", "invalid"]) await element("save").onclick();
  assert(posts.every(url => url === "/api/results"));
  assert.strictEqual(downloads.length, 4);
  apiMode = "success";
  await element("save").onclick();
  assert.strictEqual(downloads.length, 4);
  assert(alerts[0].includes("picks.json"));
}
check("valid").then(() => check("denied")).then(() => check("malformed")).catch(error => { console.error(error); process.exitCode = 1; });
'''
        proc = subprocess.run([shutil.which("node"), "-e", harness,
                               str(self.output / "index.html"), str(self.output / "gallery_data.js")],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    @unittest.skipUnless(shutil.which("nvim"), "nvim not installed")
    def test_packaged_dump_script_with_isolated_neovim(self) -> None:
        out = self.dumps / "default.json"
        env = dict(os.environ, CS="default", OUT=str(out), PRE="",
                   XDG_CONFIG_HOME=str(self.root / "config"), XDG_CACHE_HOME=str(self.root / "cache"),
                   XDG_DATA_HOME=str(self.root / "data"), XDG_STATE_HOME=str(self.root / "state"))
        proc = subprocess.run([shutil.which("nvim"), "--headless", "-u", "NONE", "-l",
                               str(ASSETS.joinpath("dump.lua"))], env=env,
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(out.read_text())["name"], "default")
        self.assertEqual(gallery_data(self.repo, self.dumps)["schemes"][-1]["kind"], "comparison")

    @unittest.skipUnless((THEME_REPO / "colorschemes.toml").is_file(), "theme repository not available")
    def test_real_repository_eight_schemes_and_identical_builds(self) -> None:
        other = self.root / "second"
        build_gallery(THEME_REPO, self.output)
        build_gallery(THEME_REPO, other)
        data = payload(self.output)
        self.assertEqual(len(data["schemes"]), 8)
        self.assertEqual({s["id"] for s in data["schemes"]},
                         {"haze", "fog", "abyss", "dusk", "haze-light", "fog-light", "abyss-light", "dusk-light"})
        for scheme in data["schemes"]:
            self.assertGreaterEqual(len(scheme["groups"]), 700)
            self.assertEqual(len(scheme["terminal"]), 16)
        for name in ("index.html", "gallery_data.js"):
            self.assertTrue((self.output / name).is_file())
            self.assertEqual((self.output / name).read_bytes(), (other / name).read_bytes())

    @unittest.skipUnless(shutil.which("firefox"), "firefox not installed")
    def test_firefox_headless_screenshot_with_throwaway_profile(self) -> None:
        snap_common = Path.home() / "snap" / "firefox" / "common"
        with tempfile.TemporaryDirectory(prefix="cs-gallery-", dir=snap_common if snap_common.is_dir() else None) as tmp:
            root = Path(tmp)
            output = root / "gallery"
            build_gallery(self.repo, output)
            profile = root / "profile"
            profile.mkdir()
            screenshot = root / "gallery.png"
            env = dict(os.environ, MOZ_CRASHREPORTER_DISABLE="1", XDG_CONFIG_HOME=str(root / "config"),
                       XDG_CACHE_HOME=str(root / "cache"), XDG_DATA_HOME=str(root / "data"),
                       XDG_STATE_HOME=str(root / "state"))
            proc = subprocess.run([shutil.which("firefox"), "--headless", "--no-remote", "--profile", str(profile),
                                   "--screenshot", str(screenshot), "--window-size", "1400,1000",
                                   (output / "index.html").as_uri() + "?mode=detail&lang=python&sim=1&cmp=fog"],
                                  env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertGreater(screenshot.stat().st_size, 1000)
            self.assertEqual(screenshot.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
