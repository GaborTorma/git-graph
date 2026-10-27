"""A commit és a WIP sor teljes nézete (#56): nyitás, visszalépés, a fájlfa, a kereső, a fa szélessége."""
from __future__ import annotations

import base64
import unittest
from pathlib import Path

from harness import PageTestCase, git_in

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")
BASE = {
    "page/js/diff.js": "".join(f"const sor{i} = {i};\n" for i in range(1, 201)),
    "page/js/egyeb.js": "export const egyeb = 1;\n",
    "page/page.css": "body { margin: 0; }\n",
    "git_graph/diff.py": 'DIFF_MAX_LINES = 3000\n"""A diff."""\nx = 1\n',
    "git_graph/__init__.py": "",
    "hooks/register.ts": "export const register = 1;\n",
    "hooks/register.test.ts": "import { register } from './register';\n",
    "hooks/hooks.json": "{}\n",
    "docs/README.md": "# Doksi\n",
    "README.md": "# Repó\n",
    "tools/util.py": "def segit():\n    return 'segit'\n",
}
CHANGED = {   # a módosító commit: a diff.js 100–140. sora ötösével (a 120. körül nincs csukott rés), és a diff.py
    "page/js/diff.js": "".join(f"const sor{i} = {i * 10 if i % 5 == 0 and 100 <= i <= 140 else i};\n" for i in range(1, 201)),
    "git_graph/diff.py": 'DIFF_MAX_LINES = 3000\n"""A diff."""\nx = 2\n',
}
SUBJECT = "nezet: két fájl módosítva"
BODY = "A teljes nézet fixture-commitja.\n\nMásodik bekezdés."


def write(repo: Path, files: dict) -> None:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")


# A CodeMirror-nézet (a `sel` doboza) első látszó sora a `top` px-es y alatt.
TOP_LINE = """([sel, top]) => {
  const view = CM.EditorView.findFromDOM(document.querySelector(sel + ' .cm-editor'));
  return view.state.doc.lineAt(view.lineBlockAtHeight(top - view.documentTop).from).number;
}"""


class FullViewTest(PageTestCase):
    WIDTH, HEIGHT = 1100, 760

    @classmethod
    def prepare(cls, repo: Path) -> None:
        write(repo, {**BASE, "docs/img/graph.png": PNG})
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "nezet: alap")
        write(repo, CHANGED)
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", f"{SUBJECT}\n\n{BODY}")

    def open_commit(self) -> None:
        self.page.locator("#rows .row", has_text=SUBJECT).click()
        self.settle()

    def open_full(self) -> None:
        self.page.locator("#fullBtn").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()

    def fv_top_line(self) -> int:
        top = self.page.evaluate("document.querySelector('.fv-path').getBoundingClientRect().bottom")
        return self.page.evaluate(f"({TOP_LINE})", [".fv-box", top + 1])

    def tree(self) -> list[str]:
        return [t.strip() for t in self.page.locator(".fv-list .fv-row .name").all_inner_texts()]

    def test_open_from_open_file(self) -> None:
        """A lenyitott diff.js 120. soránál nyitva a teljes nézet a keretet tölti ki: fent a subject és a
        body, középen a diff.js a 120. sornál, jobbra a fa, benne a diff.js kijelölve."""
        self.open_commit()
        self.page.locator('.details .file[data-path="page/js/diff.js"]').click()
        sel = '.details .file[data-path="page/js/diff.js"] + .diff'
        self.page.wait_for_selector(f"{sel} .cm-editor")
        self.settle()
        self.page.evaluate(f"""() => {{
          const view = CM.EditorView.findFromDOM(document.querySelector('{sel} .cm-editor'));
          const sc = document.querySelector('.scroll'), block = view.lineBlockAt(view.state.doc.line(120).from);
          sc.scrollTop += view.documentTop + block.top - sc.getBoundingClientRect().top; }}""")
        self.settle()
        self.open_full()
        box = self.page.locator(".fv").bounding_box()
        self.assertEqual((box["x"], box["y"], box["width"], box["height"]), (0, 0, self.WIDTH, self.HEIGHT))
        self.assertEqual(self.page.locator(".fv-subject").inner_text(), SUBJECT)
        self.assertIn("Második bekezdés.", self.page.locator(".fv-body").inner_text())
        self.assertIn("page/js/diff.js", self.page.locator(".fv-path").inner_text())
        self.assertLessEqual(abs(self.fv_top_line() - 120), 1)
        self.assertEqual(self.page.locator(".fv-row.sel .name").inner_text(), "diff.js")
        self.assertLess(self.page.locator(".fv-center").bounding_box()["x"], self.page.locator(".fv-tree").bounding_box()["x"])

    def test_button_only_with_open_commit(self) -> None:
        """A teljes nézet gombja az eszközsorban csak nyitott commitnál látszik."""
        self.assertFalse(self.page.locator("#fullBtn").is_visible())
        self.open_commit()
        self.assertTrue(self.page.locator("#fullBtn").is_visible())
        self.page.keyboard.press("Escape")
        self.settle()
        self.assertFalse(self.page.locator("#fullBtn").is_visible())

    def test_open_without_open_file(self) -> None:
        """Lenyitott fájl nélkül az első módosult fájl (a git_graph/diff.py) diffje, az első változásnál."""
        self.open_commit()
        self.open_full()
        self.assertIn("git_graph/diff.py", self.page.locator(".fv-path").inner_text())
        self.assertLessEqual(self.fv_top_line(), 3)

    def test_escape_back(self) -> None:
        """Esc-re a teljes nézet bezárul, a panelben a kijelölt git_graph/diff.py lenyitva, a lap odagörget."""
        self.open_commit()
        self.page.locator('.details .file[data-path="page/js/diff.js"]').click()
        self.settle()
        self.open_full()
        self.page.locator(".fv-row.fv-file", has_text="diff.py").click()
        self.page.wait_for_selector(".fv-path:has-text('git_graph/diff.py')")
        self.page.keyboard.press("Escape")
        self.settle()
        self.assertEqual(self.page.locator(".fv").count(), 0)
        file = self.page.locator('.details .file[data-path="git_graph/diff.py"]')
        self.assertEqual(file.get_attribute("aria-expanded"), "true")
        sc = self.page.locator(".scroll").bounding_box()
        fb = file.bounding_box()
        self.assertTrue(sc["y"] <= fb["y"] < sc["y"] + sc["height"], (sc, fb))

    def test_tree_default(self) -> None:
        """Alapnézetben a fában csak a két módosult fájl, a mappáikkal (a page/js egy sor), +N −N-nel, a
        commit-panel ikonjaival."""
        self.open_commit()
        icons = {p: self.page.locator(f'.details .file[data-path="{p}"] .fic').evaluate("e => e.outerHTML")
                 for p in ("page/js/diff.js", "git_graph/diff.py")}
        self.open_full()
        self.assertEqual(self.tree(), ["git_graph", "diff.py", "page/js", "diff.js"])
        self.assertIn("+1", self.page.locator('.fv-file[data-path="git_graph/diff.py"]').inner_text())
        self.assertIn("−9", self.page.locator('.fv-file[data-path="page/js/diff.js"]').inner_text())
        for p, html in icons.items():
            self.assertEqual(self.page.locator(f'.fv-file[data-path="{p}"] .fic').evaluate("e => e.outerHTML"), html)

    def test_all_files(self) -> None:
        """A kapcsolóval a commit állapotának minden fájlja; a nem módosult fájl tartalma színezve, diffjel nélkül."""
        self.open_commit()
        self.open_full()
        self.page.locator(".fv-all").click()
        self.page.wait_for_selector('.fv-row[data-dir="hooks"]')
        self.assertIn("README.md", self.tree())
        self.page.locator('.fv-row[data-dir="tools"]').click()
        self.page.locator('.fv-file[data-path="tools/util.py"]').click()
        self.page.wait_for_selector(".fv-path:has-text('tools/util.py')")
        self.page.wait_for_selector(".fv-box .cm-editor")
        self.settle()
        self.assertEqual(self.page.locator(".fv-box .cm-changedLine, .fv-box .cm-deletedChunk").count(), 0)
        self.assertIn("segit", self.page.locator(".fv-box .cm-content").inner_text())
        colored = self.page.evaluate("""() => { const base = getComputedStyle(document.querySelector('.fv-box .cm-content')).color;
          return [...document.querySelectorAll('.fv-box .cm-line span')].some(s => getComputedStyle(s).color !== base); }""")
        self.assertTrue(colored)

    def test_selection_in_collapsed_folder(self) -> None:
        """A kijelölt docs/img/graph.png csukott docs/img mappájánál a docs alatti img sor sötétebb háttérrel
        jelölt, az egér alatti sor a hover-színt kapja."""
        self.open_commit()
        self.open_full()
        self.page.locator(".fv-all").click()
        self.page.wait_for_selector('.fv-row[data-dir="docs"]')
        self.page.locator('.fv-row[data-dir="docs"]').click()
        self.page.locator('.fv-row[data-dir="docs/img"]').click()
        self.page.locator('.fv-file[data-path="docs/img/graph.png"]').click()
        self.page.locator('.fv-row[data-dir="docs/img"]').click()
        img = self.page.locator('.fv-row[data-dir="docs/img"]')
        self.page.mouse.move(0, 0)
        bg = lambda loc: loc.evaluate("e => getComputedStyle(e).backgroundColor")  # noqa: E731
        self.assertIn("sel-in", img.get_attribute("class"))
        plain = self.page.locator('.fv-row[data-dir="hooks"]')
        self.assertNotEqual(bg(img), bg(plain))
        plain.hover()
        self.assertNotIn(bg(plain), ("rgba(0, 0, 0, 0)",))

    def test_tree_width(self) -> None:
        """A fa 280 px-ről indul; 360 px-re húzva újratöltés után is annyi; 150 px-re húzva 200 px marad."""
        self.open_commit()
        self.open_full()
        tree = self.page.locator(".fv-tree")
        self.assertEqual(tree.bounding_box()["width"], 280)
        handle = self.page.locator(".fv-resize").bounding_box()
        x, y = handle["x"] + handle["width"] / 2, handle["y"] + 100

        def drag(width: int) -> None:
            start = self.page.locator(".fv-resize").bounding_box()["x"] + handle["width"] / 2
            current = tree.bounding_box()["width"]
            self.page.mouse.move(start, y)
            self.page.mouse.down()
            self.page.mouse.move(start - (width - current), y, steps=5)
            self.page.mouse.up()

        drag(360)
        self.assertEqual(round(tree.bounding_box()["width"]), 360)
        self.page.reload()
        self.page.wait_for_selector("#rows .row")
        self.settle()
        self.open_commit()
        self.open_full()
        self.assertEqual(round(tree.bounding_box()["width"]), 360)
        drag(150)
        self.assertEqual(round(tree.bounding_box()["width"]), 200)
        del x

    def test_name_filter(self) -> None:
        """A „register” szűrés: csak a hooks/register.ts és a hooks/register.test.ts, a mappájukkal."""
        self.open_commit()
        self.open_full()
        self.page.locator(".fv-all").click()
        self.page.wait_for_selector('.fv-row[data-dir="hooks"]')
        self.page.locator(".fv-search input").fill("register")
        self.settle()
        self.assertEqual(self.tree(), ["hooks", "register.test.ts", "register.ts"])

    def test_content_search(self) -> None:
        """A „?DIFF_MAX_LINES” keresés a kijelölt commit azon fájljait adja, amelyekben szerepel."""
        self.open_commit()
        self.open_full()
        self.page.locator(".fv-search input").fill("?DIFF_MAX_LINES")
        self.page.wait_for_function("document.querySelectorAll('.fv-list .fv-file').length === 1")
        self.assertEqual(self.tree(), ["git_graph", "diff.py"])


class AllFilesTest(PageTestCase):
    """A minden fájl nézet színei: a módosult fájlok mappája a változás színét kapja, vegyesnél a
    „módosult”-at; a törölt fájl áthúzva, pirosan a helyén."""
    WIDTH, HEIGHT = 1100, 760

    @classmethod
    def prepare(cls, repo: Path) -> None:
        write(repo, {"vegyes/regi.py": "x = 1\n", "vegyes/marad.py": "y = 1\n", "csend/a.txt": "a\n"})
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "szinek: alap")
        (repo / "vegyes" / "regi.py").unlink()
        write(repo, {"vegyes/marad.py": "y = 2\n", "uj/a.txt": "új\n"})
        git_in(repo, "add", "-A")
        git_in(repo, "commit", "-qm", "szinek: vegyes")

    def test_colors(self) -> None:
        self.page.locator("#rows .row", has_text="szinek: vegyes").click()
        self.settle()
        self.page.locator("#fullBtn").click()
        self.page.wait_for_selector(".fv")
        self.page.locator(".fv-all").click()
        self.page.wait_for_selector('.fv-row[data-dir="csend"]')
        cls = lambda d: self.page.locator(f'.fv-row[data-dir="{d}"]').get_attribute("class")  # noqa: E731
        self.assertIn("modified", cls("vegyes"))
        self.assertIn("added", cls("uj"))
        self.assertNotIn("modified", cls("csend"))
        gone = self.page.locator('.fv-file[data-path="vegyes/regi.py"] .name')
        self.assertEqual(gone.evaluate("e => getComputedStyle(e).textDecorationLine"), "line-through")
        red = self.page.evaluate("""() => { const p = Object.assign(document.createElement('span'), { style: 'color: var(--del)' });
          document.body.append(p); const c = getComputedStyle(p).color; p.remove(); return c; }""")
        self.assertEqual(gone.evaluate("e => getComputedStyle(e).color"), red)


class WipFullViewTest(PageTestCase):
    """A WIP sor teljes nézete a munkakönyvtár mostani állapotát mutatja."""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "main-4-5.txt").write_text("a munkakönyvtár mostani állapota\n", encoding="utf-8")

    def test_open_wip(self) -> None:
        self.page.locator(".row.uncommitted", has_text="Nem commitolt").click()
        self.settle()
        self.page.locator("#fullBtn").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.assertIn("main-4-5.txt", self.page.locator(".fv-path").inner_text())
        self.assertIn("a munkakönyvtár mostani állapota", self.page.locator(".fv-box .cm-content").inner_text())


if __name__ == "__main__":
    unittest.main()
