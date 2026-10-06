"""A lap (`page`): betöltő, élő kód, fájltípus-ikonok."""
from __future__ import annotations

import json

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
