"""A lap (`page`): betöltő, élő kód, fájltípus-ikonok."""
from __future__ import annotations

import base64
import json
import shutil

from helpers import ROOT, HomeTestCase


class PageTest(HomeTestCase):
    def test_file_icon(self) -> None:
        """Fájlnév, a leghosszabb kiterjesztés, átnevezés; ismeretlenre az általános ikon."""
        gg = self.load()
        cases = {"page/page.js": "javascript", "README.md": "readme", "app/x.spec.ts": "typescript-test",
                 "src/{a => b}/main.py": "python", "bin/git-graph": "_file", "LICENSE": "license"}
        for path, icon in cases.items():
            self.assertEqual(gg.page.file_icon(path), icon, path)
        svg = gg.page.file_icons()["icons"]["python"]
        self.assertIn("var(--ic-", svg)
        self.assertNotIn("--vscode-ctp", svg)

    def test_attach_icons(self) -> None:
        """Csak a használt ikonok SVG-je megy a lapra."""
        gg = self.load()
        stats = {"x": {"files": [{"path": "a.py"}, {"path": "b.py"}, {"path": "c.md"}]}}
        used = gg.page.attach_icons(stats)
        self.assertEqual(set(used), {"python", "markdown"})
        self.assertEqual([f["icon"] for f in stats["x"]["files"]], ["python", "python", "markdown"])

    def test_loader(self) -> None:
        """A betöltőbe a kontextus és a cím kerül, `</script>`-biztosan."""
        gg = self.load()
        gg.gitio.set_repo(ROOT)
        page = gg.page.build("Git Graph </script>", "x</script>")
        self.assertNotIn("__CTX__", page)
        self.assertNotIn("__TITLE__", page)
        self.assertEqual(page.count("</script>"), 1)
        self.assertIn('"server": "host:git-graph"', page)

    def test_embed(self) -> None:
        gg = self.load()
        raw = gg.page.embed({"s": "</script>  é"})
        self.assertNotIn("</", raw)
        self.assertNotIn(" ", raw)
        self.assertEqual(json.loads(raw), {"s": "</script>  é"})

    def test_page_api(self) -> None:
        """A betöltő szerződése: régebbi lapnál újrapublikálás, újabbnál az app újraindítása."""
        gg = self.load()
        api = gg.page.LOADER_API
        self.assertIsNone(gg.page.page_api_mismatch(api))
        self.assertIn("újrapublikálja", gg.page.page_api_mismatch(api - 1))
        self.assertIn("indítsd újra", gg.page.page_api_mismatch(api + 1))
        self.assertIn("indítsd újra", gg.page.page_api_mismatch(None))
        code = gg.page.page_code()
        self.assertEqual(set(code), {"head", "body", "js"})
        mermaid = gg.page.page_code("mermaid")             # lustán kért darab: csak a JS-e
        self.assertEqual(set(mermaid), {"js"})
        self.assertIn("globalThis.mermaid=", mermaid["js"])
        font = gg.page.page_code("font")                   # a lap betűje: a woff2 base64-ben
        self.assertEqual(set(font), {"woff2"})
        self.assertEqual(base64.b64decode(font["woff2"])[:4], b"wOF2")
        mono = gg.page.page_code("font-mono")
        self.assertEqual(base64.b64decode(mono["woff2"])[:4], b"wOF2")
        with self.assertRaises(ValueError):
            gg.page.page_code("nincs")

    def test_page_modules(self) -> None:
        """A lap moduljai a függőségeik után jönnek, a szakaszokból a forrás áll össze."""
        gg = self.load()
        mods = gg.page.page_modules()
        names = [m[0] for m in mods]
        self.assertEqual(names[-1], "main.js")
        self.assertEqual(sorted(names), sorted(p.name for p in (ROOT / "page" / "js").glob("*.js")))
        for name, parts, deps in mods:
            self.assertEqual(len(parts), len(deps) + 1)
            self.assertTrue(all(names.index(d) < names.index(name) for d in deps), name)
            source = parts[0] + "".join(f"'./{d}'" + p for d, p in zip(deps, parts[1:]))
            self.assertEqual(source, (ROOT / "page" / "js" / name).read_text(encoding="utf-8"))
        self.assertIn('"main.js"', gg.page.page_code()["js"])

    def fake_modules(self, gg, files: dict[str, str]) -> None:
        """A lap moduljai egy eldobható `page/js`-ből."""
        page = self.home / "page"
        shutil.rmtree(page, ignore_errors=True)
        (page / "js").mkdir(parents=True)
        for name, text in files.items():
            (page / "js" / name).write_text(text, encoding="utf-8")
        gg.page.PAGE_DIR = page
        gg.page._PAGE.clear()

    def test_page_module_links(self) -> None:
        """Csak a belépőből elérhető modul kerül a lapra; körkörös és más alakú relatív import hiba."""
        gg = self.load()
        self.fake_modules(gg, {"main.js": "import { a } from './a.js';\nimport './b.js';\n",
                               "a.js": "import {\n  b,\n} from './b.js';\nexport const a = b;\n",
                               "b.js": "export const b = 1;\n", "old.js": "import './gone.js';\n"})
        self.assertEqual([(n, d) for n, _, d in gg.page.page_modules()],
                         [("b.js", []), ("a.js", ["b.js"]), ("main.js", ["a.js", "b.js"])])
        self.fake_modules(gg, {"main.js": "import './a.js';\n", "a.js": "import './main.js';\n"})
        with self.assertRaisesRegex(ValueError, "körkörös"):
            gg.page.page_modules()
        self.fake_modules(gg, {"main.js": "const m = import('./a.js');\n", "a.js": ""})
        with self.assertRaisesRegex(ValueError, "relatív út"):
            gg.page.page_modules()

    def test_install_prunes_modules(self) -> None:
        """A stabil helyre a lap minden modulja kikerül; a forrásból eltűnt modul törlődik."""
        gg = self.load()
        stale = self.state / "page" / "js" / "old.js"
        stale.parent.mkdir(parents=True)
        stale.write_text("", encoding="utf-8")
        gg.install.install_copy(ROOT)
        self.assertFalse(stale.exists())
        self.assertTrue((stale.parent / "main.js").is_file())
