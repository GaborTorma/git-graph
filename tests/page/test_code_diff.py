"""A kóddiff a CodeMirrorral (#56): egymás alatti és egymás melletti nézet, a nyelvek színezése, a
nagy fájl, a változatlan rés — a commit-panelben."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, commit_versions

# A Python-fájl: a 2. sor cserélődik, a többsoros string belseje színezett.
OLD_PY = 'x = hivas(a)\nSZOVEG = """\nelso sor\nmasodik sor\n"""\n' + "".join(f"s{i} = {i}\n" for i in range(60))
NEW_PY = OLD_PY.replace("x = hivas(a)", "x = hivas(a, b)").replace("s59 = 59", "s59 = 590")


def numbered(n: int, changed: dict) -> str:
    """`n` sor (`sor 1` …), a `changed` sorszámai helyén a megadott szöveg."""
    return "".join(f"{changed.get(i, f'sor {i}')}\n" for i in range(1, n + 1))


# Rés: két változás között 48 változatlan sor — a két szélén 3-3 látszik, 42 csukva.
GAP_OLD = numbered(100, {})
GAP_NEW = numbered(100, {10: "valtozott 10", 59: "valtozott 59"})
# A fájl eleje és vége: az első változás a 30. sorban, utána még 15 sor.
EDGE_OLD = numbered(45, {})
EDGE_NEW = numbered(45, {30: "valtozott 30"})
# Markdown: a két változott bekezdés között 8 változatlan — a szomszédaik látszanak, 6 csukva.
MD_OLD = "".join(f"Bekezdés {i}.\n\n" for i in range(1, 11))
MD_NEW = MD_OLD.replace("Bekezdés 1.", "Bekezdés egy.").replace("Bekezdés 10.", "Bekezdés tíz.")
# két változás között 3 változatlan blokk: a környezetük (1-1) után 1 marad, az nem csukódik; a végén 4 igen
MD_NEAR_NEW = MD_OLD.replace("Bekezdés 1.", "Bekezdés egy.").replace("Bekezdés 5.", "Bekezdés öt.")
# Sok szétszórt változás (a merge alap `scanLimit`-je fölött): a diff csak a valódi változásokat jelöli.
SPREAD_OLD = "".join(f"const ertek_{i} = szamol('{'x' * 40}', {i});\n" for i in range(400))
SPREAD_NEW = "".join((f"const ertek_{i} = szamol('{'y' * 40}', {i}, uj);\n" if i % 20 == 5 else f"const ertek_{i} = szamol('{'x' * 40}', {i});\n")
                     for i in range(400))
CSV_OLD = "".join(f"{i},{'x' * 110}\n" for i in range(12000))
CSV_NEW = CSV_OLD.replace("0,x", "0,y", 1).replace("11999,x", "11999,y")
LANGS = {
    "app.py": ("def f():\n    return 1\n", "def f():\n    return 2\n"),
    "page.tsx": ("const a: number = 1;\n", "const a: number = 2;\n"),
    "config.toml": ('[tool]\nname = "a"\n', '[tool]\nname = "b"\n'),
    "View.swift": ("let a = 1\n", "let a = 2\n"),
    "main.go": ('func main() { s := "a" }\n', 'func main() { s := "b" }\n'),
    "tsconfig.json": ('{\n  // komment\n  "a": 1\n}\n', '{\n  // komment\n  "a": 2\n}\n'),
}

# A sor színezett elemei: a `.cm-line` gyerek-spanjai közül, amelyiknek a színe nem a kód alapszíne.
COLORED = """sel => {
  const base = getComputedStyle(document.querySelector(sel + ' .cm-content')).color;
  return [...document.querySelectorAll(sel + ' .cm-line span')].filter(s => getComputedStyle(s).color !== base)
    .map(s => s.textContent);
}"""


class CodeDiffTest(PageTestCase):
    SUBJECT = "kod"
    WIDTH = 900

    @classmethod
    def prepare(cls, repo: Path) -> None:
        commit_versions(repo, {"kod.py": (OLD_PY, NEW_PY), "res.txt": (GAP_OLD, GAP_NEW), "szel.txt": (EDGE_OLD, EDGE_NEW),
                               "bekezdes.md": (MD_OLD, MD_NEW), "kozel.md": (MD_OLD, MD_NEAR_NEW), "szort.js": (SPREAD_OLD, SPREAD_NEW), "data.csv": (CSV_OLD, CSV_NEW), **LANGS}, cls.SUBJECT)

    def opened(self, name: str) -> str:
        """A fájl lenyitva; vissza a diffje szelektora."""
        self.open_file(name)
        sel = f'#rows .details .file[data-path="{name}"] + .diff'
        self.page.wait_for_selector(f"{sel} .cm-editor")
        self.settle()
        return sel

    def test_stacked(self) -> None:
        """800 px-es panelben a régi sorok nem szerkeszthető blokkként az új sorok fölött, a megváltozott
        rész erősebb háttérrel, a szintaxis a Claude kódszíneivel, a többsoros string belseje is."""
        with self.subTest("Adott egy commit, amely módosítja a kod.py-t"):
            sel = self.opened("kod.py")
        with self.subTest("Akkor a régi sor blokkként az új fölött"):
            self.assertEqual(self.page.locator(f"{sel} .cm-mergeView").count(), 0)
            old = self.page.locator(f"{sel} .cm-deletedChunk").first
            self.assertIn("x = hivas(a)", old.inner_text())
            new_top = self.page.locator(f"{sel} .cm-changedLine").first.bounding_box()["y"]
            self.assertLess(old.bounding_box()["y"], new_top)
            self.assertNotEqual(old.get_attribute("contenteditable"), "true")
        with self.subTest("És a kód az Anthropic Mono betűvel"):
            family = self.page.locator(f"{sel} .cm-line").first.evaluate("e => getComputedStyle(e).fontFamily")
            self.assertTrue(family.startswith('"Anthropic Mono"'), family)
        with self.subTest("És a megváltozott rész erősebb háttérrel"):
            bg = self.page.evaluate(f"""() => {{ const c = document.querySelector('{sel} .cm-changedLine .cm-changedText');
              return [getComputedStyle(c).backgroundColor, getComputedStyle(c.closest('.cm-changedLine')).backgroundColor]; }}""")
            self.assertNotEqual(bg[0], bg[1])
        with self.subTest("És a többsoros string belseje is string-színű"):
            colors = self.page.evaluate(f"""() => {{
              const st = getComputedStyle(document.documentElement).getPropertyValue('--syn-st').trim();
              const line = [...document.querySelectorAll('{sel} .cm-line')].find(l => l.textContent === 'elso sor');
              const probe = Object.assign(document.createElement('span'), {{ style: 'color:' + st }});
              document.body.append(probe);
              const want = getComputedStyle(probe).color; probe.remove();
              return [getComputedStyle(line.querySelector('span') || line).color, want]; }}""")
            self.assertEqual(colors[0], colors[1])

    def test_side_by_side(self) -> None:
        """1200 px-es diffben balra a régi, jobbra az új oldal, két szerkesztőben."""
        self.resize(1300)
        sel = self.opened("kod.py")
        editors = self.page.locator(f"{sel} .cm-mergeView .cm-editor")
        self.assertEqual(editors.count(), 2)
        left, right = editors.nth(0).bounding_box(), editors.nth(1).bounding_box()
        self.assertLess(left["x"], right["x"])
        self.assertIn("x = hivas(a)", editors.nth(0).inner_text())
        self.assertIn("x = hivas(a, b)", editors.nth(1).inner_text())

    def test_languages(self) -> None:
        """A py, tsx, toml Lezerrel, a swift a swift móddal színezett; a go sima szöveg."""
        for name, colored in (("app.py", True), ("page.tsx", True), ("config.toml", True), ("View.swift", True), ("main.go", False)):
            with self.subTest(name):
                sel = self.opened(name)
                spans = self.page.evaluate(f"({COLORED})", sel)
                self.assertEqual(bool(spans), colored, spans)

    def test_json_comment(self) -> None:
        """A kommentes tsconfig.json a JSON-elemzővel színezett (a string is színes)."""
        sel = self.opened("tsconfig.json")
        self.assertIn('"a"', self.page.evaluate(f"({COLORED})", sel))

    def test_many_scattered_changes(self) -> None:
        """20 szétszórt sorcsere egy 400 soros fájlban: pontosan 20 sor változott, nem egy nagy blokk."""
        sel = self.opened("szort.js")
        changed = self.page.evaluate(f"""() => {{
          const v = CM.EditorView.findFromDOM(document.querySelector('{sel} .cm-editor'));
          return CM.getChunks(v.state).chunks.reduce((n, c) => n + v.state.doc.lineAt(c.toB).number - v.state.doc.lineAt(c.fromB).number, 0); }}""")
        self.assertEqual(changed, 20)

    def test_big_file(self) -> None:
        """A 12 000 soros, 1,4 MB-os data.csv teljes egészében, csonkolás nélkül."""
        sel = self.opened("data.csv")
        lines = self.page.evaluate(f"() => CM.EditorView.findFromDOM(document.querySelector('{sel} .cm-editor')).state.doc.lines")
        self.assertEqual(lines, 12001)
        self.assertEqual(self.page.locator(f"{sel} .diff-note").count(), 0)

    def test_gap_between_hunks(self) -> None:
        """A két hunk közti 42 változatlan sor egy kattintásra mind kinyílik; a rés az app diffjének nyilával."""
        sel = self.opened("res.txt")
        gaps = self.page.locator(f"{sel} .cm-collapsedLines")
        self.assertIn("42 változatlan sor", gaps.all_inner_texts())
        mask = self.page.evaluate(f"() => getComputedStyle(document.querySelector('{sel} .cm-collapsedLines'), '::before').maskImage")
        self.assertIn("svg", mask)
        gaps.filter(has_text="42 változatlan sor").click()
        self.settle()
        self.assertNotIn("42 változatlan sor", gaps.all_inner_texts())
        texts = self.page.locator(f"{sel} .cm-line").all_inner_texts()
        self.assertTrue(all(f"sor {i}" in texts for i in range(14, 56)))

    def test_gap_at_edges(self) -> None:
        """Az első változás a 30. sornál, utána 15 sor: a fájl elején és végén is kinyitható rés (a végén a
        záró újsor utáni üres sor is a CodeMirror sora: 15 + 1 − 3)."""
        sel = self.opened("szel.txt")
        self.assertEqual(self.page.locator(f"{sel} .cm-collapsedLines").all_inner_texts(),
                         ["26 változatlan sor", "13 változatlan sor"])

    def test_markdown_gap(self) -> None:
        """A renderelt markdownban a „6 változatlan blokk” egy kattintásra mind kinyílik."""
        self.open_file("bekezdes.md")
        self.page.wait_for_selector(".details .diff .md-doc")
        gap = self.page.locator(".details .diff .diff-uni [data-gap]")
        self.assertEqual(gap.inner_text().strip(), "6 változatlan blokk")
        before = self.page.locator(".details .diff .diff-uni .md-blk").count()
        gap.click()
        self.settle()
        self.assertEqual(self.page.locator(".details .diff .diff-uni .md-blk").count(), before + 6)
        self.assertEqual(self.page.locator(".details .diff [data-gap]").count(), 0)

    def test_markdown_short_gap_open(self) -> None:
        """A 3-nál rövidebb változatlan futam (itt 1 blokk két változás környezete között) nem csukódik össze."""
        self.open_file("kozel.md")
        self.page.wait_for_selector(".details .diff .md-doc")
        gaps = self.page.locator('.details .file[data-path="kozel.md"] + .diff .diff-uni [data-gap]').all_inner_texts()
        self.assertEqual([g.strip() for g in gaps], ["4 változatlan blokk"])


class HostCallsTest(PageTestCase):
    """A host-híd sűrű hívásnál visszafog (#61): a kódnézet egy hívással tölt, és a visszafogást kivárja."""
    SUBJECT = "hivas"
    WIDTH = 900
    # a lap `file_diff` hívásai és az első `n` hívás `rate_limited`
    SPY = """n => { const mcp = GIT_GRAPH.mcp, call = mcp.callTool.bind(mcp); window.calls = [];
      mcp.callTool = (s, tool, args, ...rest) => {
        if (tool !== 'file_diff') return call(s, tool, args, ...rest);
        window.calls.push(args);
        return window.calls.length <= n ? Promise.reject({ code: 'rate_limited', retryAfterMs: 50, message: 'Host tool rate limit exceeded' })
          : call(s, tool, args, ...rest); }; }"""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        commit_versions(repo, {"egy.py": ("a = 1\n", "a = 2\n")}, cls.SUBJECT)

    def opened(self) -> str:
        self.open_file("egy.py")
        sel = '#rows .details .file[data-path="egy.py"] + .diff'
        self.page.wait_for_selector(f"{sel} .cm-editor")
        return sel

    def test_one_call(self) -> None:
        """A kis fájl kódnézete egyetlen file_diff hívással töltődik."""
        self.page.evaluate(self.SPY, 0)
        self.opened()
        self.assertEqual(len(self.page.evaluate("window.calls")), 1)

    def test_rate_limited_retry(self) -> None:
        """Ha a host visszafog, a lap kis várakozás után újrapróbál, hibaüzenet nélkül."""
        self.page.evaluate(self.SPY, 2)
        sel = self.opened()
        self.assertIn("a = 2", self.page.locator(f"{sel} .cm-content").inner_text())
        self.assertEqual(self.page.locator(f"{sel} .diff-note").count(), 0)


if __name__ == "__main__":
    unittest.main()
