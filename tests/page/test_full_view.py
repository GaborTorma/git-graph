"""A commit és a WIP sor teljes nézete (#56): nyitás, visszalépés, a fájlfa, a kereső, a fa szélessége."""
from __future__ import annotations

import base64
import json
import time
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

    def open_full(self, name: str = "git_graph/diff.py") -> None:
        """A lenyitott commit `name` fájlja teljes képernyőn (a fejléce ikonjával; ha csukva, előbb lenyitva)."""
        file = self.page.locator(f'.details .file[data-path="{name}"]')
        if file.get_attribute("aria-expanded") != "true":
            file.click()
            self.page.wait_for_selector(f'.details .file[data-path="{name}"] + .diff .cm-editor')
            self.settle()
        file.locator("[data-full]").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()

    def open_side(self) -> None:
        self.page.locator("#sideBtn").click()
        self.page.wait_for_selector(".side .fv-list .fv-row")
        self.settle()

    def side_tree(self) -> list[str]:
        return [t.strip() for t in self.page.locator(".side .fv-list .fv-row .name").all_inner_texts()]

    def fv_top_line(self) -> int:
        top = self.page.evaluate("document.querySelector('.fv-scroll').getBoundingClientRect().top")
        return self.page.evaluate(f"({TOP_LINE})", [".fv-box", top + 1])

    def tree(self) -> list[str]:
        return [t.strip() for t in self.page.locator(".fv-list .fv-row .name").all_inner_texts()]

    def test_open_from_open_file(self) -> None:
        """A diff.js fejlécének ikonjával: a lap tetejétől a láblécig; középen a fejlécben a repó neve, a HEAD-chip,
        a fájl útja, jobbra a fájlban kereső és az X (a subject nélkül); alatta, a fejléc alatt görgetve a diff.js
        az első változásánál (100. sor), keret nélkül; jobbra teljes magasságban a fa, benne a diff.js kijelölve;
        a fa keresője és gombja a fejléc keresőjének magasságával."""
        self.open_commit()
        self.open_full("page/js/diff.js")
        box, foot = self.page.locator(".fv").bounding_box(), self.page.locator("#foot").bounding_box()
        self.assertEqual((box["x"], box["y"], box["width"], box["y"] + box["height"]), (0, 0, self.WIDTH, foot["y"]))
        tree = self.page.locator(".fv-tree").bounding_box()
        self.assertEqual((tree["y"], tree["y"] + tree["height"]), (0, foot["y"]))
        head = self.page.locator(".fv-head")
        self.assertEqual(head.locator(".repo-name").inner_text(), self.page.locator("#repoName").inner_text())
        self.assertTrue(head.locator(".fv-find input").is_visible())
        self.assertEqual(head.locator(".fv-close").get_attribute("aria-label"), "Kilépés a teljes képernyőből (Esc)")
        self.assertEqual(head.locator(".head-chip").inner_text().strip(), self.page.locator("#headChip").inner_text().strip())
        self.assertNotIn(SUBJECT, head.inner_text())
        self.assertIn("page/js/diff.js", head.locator(".fv-path").inner_text())
        def x(sel: str) -> float:
            return self.page.locator(sel).bounding_box()["x"]

        self.assertLess(x(".fv-head .head-chip"), x(".fv-head .fv-path"))
        self.assertLess(x(".fv-head .fv-path"), x(".fv-head .fv-find"))
        self.assertLess(x(".fv-head .fv-find"), x(".fv-head .fv-close"))
        scroll, hbox = self.page.locator(".fv-scroll").bounding_box(), head.bounding_box()
        self.assertEqual(scroll["y"], hbox["y"] + hbox["height"])
        def h(sel: str) -> float:
            return self.page.locator(sel).bounding_box()["height"]

        self.assertEqual(h(".fv .fv-search"), h(".fv-find"))
        self.assertEqual(h(".fv .fv-diff"), h(".fv-find"))
        self.assertLessEqual(abs(self.fv_top_line() - 100), 1)
        self.assertEqual(self.page.locator(".fv-row.sel .name").inner_text(), "diff.js")
        self.assertLess(self.page.locator(".fv-center").bounding_box()["x"], self.page.locator(".fv-tree").bounding_box()["x"])
        diff = self.page.evaluate("(() => { const s = getComputedStyle(document.querySelector('.fv-box'));"
                                  " return [s.borderTopWidth, s.borderRadius]; })()")
        self.assertEqual(diff, ["0px", "0px"])
        # a kódnézet kitölti a magasságot, és a saját görgetője görget (a kereten belül), nem a doboz
        fill = self.page.evaluate("""(() => { const sc = document.querySelector('.fv-scroll'), cm = sc.querySelector('.cm-diff');
          const ed = cm.querySelector('.cm-scroller'), a = sc.getBoundingClientRect(), b = cm.getBoundingClientRect();
          return [sc.scrollHeight - sc.clientHeight, Math.round(b.top - a.top), Math.round(a.bottom - b.bottom),
                  ed.scrollHeight > ed.clientHeight]; })()""")
        self.assertEqual(fill, [0, 0, 0, True])
        center = self.page.locator(".fv-scroll").bounding_box()
        self.assertEqual(self.page.locator(".fv-box").bounding_box()["width"], center["width"])

    def test_find_in_file(self) -> None:
        """A fejléc keresője a nyitott fájlban: a találatok kiemelve, Enter a következőre lép, Esc törli."""
        self.open_commit()
        self.open_full("page/js/diff.js")
        find = self.page.locator(".fv-find input")
        find.fill("sor150")
        self.page.wait_for_selector(".fv-box .cm-searchMatch")
        sel = ("(() => { const v = CM.EditorView.findFromDOM(document.querySelector('.fv-box .cm-editor'));"
               " const r = v.state.selection.main; return v.state.sliceDoc(r.from, r.to); })()")
        self.assertEqual(self.page.evaluate(sel), "sor150")
        self.assertFalse(self.page.locator(".fv-box .cm-panels-top").is_visible())
        find.fill("const sor1")
        first = self.page.evaluate("CM.EditorView.findFromDOM(document.querySelector('.fv-box .cm-editor')).state.selection.main.from")
        find.press("Enter")
        second = self.page.evaluate("CM.EditorView.findFromDOM(document.querySelector('.fv-box .cm-editor')).state.selection.main.from")
        self.assertGreater(second, first)
        self.assertTrue(find.evaluate("e => e === document.activeElement"))
        find.press("Escape")
        self.assertEqual(find.input_value(), "")
        self.assertEqual(self.page.locator(".fv-box .cm-searchMatch").count(), 0)
        self.assertTrue(self.page.locator(".fv").is_visible())

    def test_commit_list(self) -> None:
        """A fa alatt a commitlista: a HEAD ágának commitjai közül a commit kijelölve, mellette a szomszédai
        (összesen 5), alatta a többi száma, a súgó a teljes commit message; a másik commitra kattintva a nézet
        arra vált."""
        self.open_commit()
        self.open_full("page/js/diff.js")
        items = self.page.locator(".fv-commits .fv-commit")
        self.assertEqual(items.count(), 5)
        self.assertEqual(self.page.locator(".fv-commit.sel .subj").inner_text(), SUBJECT)
        self.assertRegex(self.page.locator(".fv-commits .fv-more").inner_text(), r"^még \d+ commit$")
        tip = self.page.locator(".fv-commit.sel").get_attribute("data-tip")
        self.assertEqual(tip, f"{SUBJECT}\nA teljes nézet fixture-commitja.\nMásodik bekezdés.")

        self.page.locator(".fv-commit", has_text="nezet: alap").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()
        self.assertEqual(self.page.locator(".fv-commit.sel .subj").inner_text(), "nezet: alap")
        self.assertEqual(self.page.locator(".fv-commits .fv-commit").first.inner_text().split("\n")[0], SUBJECT)
        self.assertIn("page/js/diff.js", self.page.locator(".fv-path").inner_text())
        self.assertIn("diff.js", self.tree())    # az alap commit minden fájlja új: a diff.js is

    def test_grep_follows_diff_filter(self) -> None:
        """A tartalomkeresés a diff-szűrővel csak a változott fájlok találatait mutatja, kikapcsolva mindet."""
        self.open_commit()
        self.open_full()
        self.page.locator(".fv-search input").fill("?segit")
        self.page.wait_for_timeout(600)
        self.assertEqual(self.page.locator(".fv-list .fv-file").count(), 0)
        self.page.locator(".fv .fv-diff").click()
        self.page.wait_for_selector('.fv-list .fv-file[data-path="tools/util.py"]')

    def test_full_icon_on_closed_file(self) -> None:
        """A teljes képernyő ikonja a csukott fájl fejlécén is ott van, és a fájlt teljes képernyőn nyitja."""
        self.open_commit()
        file = self.page.locator('.details .file[data-path="git_graph/diff.py"]')
        self.assertEqual(file.get_attribute("aria-expanded"), "false")
        file.locator("[data-full]").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.assertIn("git_graph/diff.py", self.page.locator(".fv-path").inner_text())

    def test_sidebar_without_commit(self) -> None:
        """Lenyitott commit nélkül a sidebar a worktree állapotát mutatja minden fájllal, színezés nélkül, a
        diff-szűrő aktív, de nincs lenyomva; a gráf mellette keskenyebb, az eszközsor a megszokott."""
        # Adott: egy commit sincs lenyitva
        # Ha a Fejlesztő a sidebar gombjára kattint
        self.page.locator("#sideBtn").click()
        self.page.wait_for_selector('.side .fv-row[data-dir="hooks"]')
        # Akkor minden fájl, színezés és számok nélkül; a diff-szűrő aktív, nincs lenyomva
        diff = self.page.locator(".side .fv-diff")
        self.assertFalse(diff.is_disabled())
        self.assertEqual(diff.get_attribute("aria-pressed"), "false")
        self.assertIn("README.md", self.side_tree())
        self.page.locator('.side .fv-row[data-dir="git_graph"]').click()
        self.assertEqual(self.page.locator(".side .fv-row:is(.added, .modified, .deleted)").count(), 0)
        self.assertEqual(self.page.locator(".side .fv-row .churn").count(), 0)
        # És a gráf a sidebar mellett, az eszközsor a megszokott
        side = self.page.locator(".side").bounding_box()
        sc = self.page.locator(".scroll").bounding_box()
        self.assertLessEqual(sc["x"] + sc["width"], side["x"] + 1)
        self.assertTrue(self.page.locator("#branchBtn").is_visible())
        self.assertTrue(self.page.locator("#search").is_visible())

    def test_sidebar_diff_selects_head(self) -> None:
        """Commit nélkül a diff-szűrő a HEAD-commitot nyitja le: a fa a változott fájljait mutatja, színezve."""
        self.open_side()
        self.page.locator(".side .fv-diff").click()
        self.page.wait_for_selector("#rows .row[aria-expanded='true']")
        self.assertIn(SUBJECT, self.page.locator("#rows .row[aria-expanded='true']").inner_text())
        self.page.wait_for_function("!document.querySelector('.side .fv-file[data-path=\"README.md\"]')")
        self.assertEqual(self.side_tree(), ["git_graph", "diff.py", "page/js", "diff.js"])
        self.assertEqual(self.page.locator(".side .fv-diff").get_attribute("aria-pressed"), "true")

    def test_clean_head_full_diff_disabled(self) -> None:
        """A tiszta HEAD fájlja a sidebarból teljes képernyőn: a diff-szűrő letiltva, hover nélkül."""
        self.open_side()
        self.page.locator('.side .fv-file[data-path="README.md"]').click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        diff = self.page.locator(".fv .fv-diff")
        self.assertTrue(diff.is_disabled())
        look = "e => { const s = getComputedStyle(e); return [s.backgroundColor, s.boxShadow, s.color]; }"
        before = diff.evaluate(look)
        diff.hover(force=True)
        self.assertEqual(diff.evaluate(look), before)

    def test_sidebar_follows_commit(self) -> None:
        """A sidebar a lenyitott commitot követi: csak a változott fájljai, színezve; becsukva újra a worktree."""
        self.open_side()
        self.open_commit()
        self.page.wait_for_function("!document.querySelector('.side .fv-file[data-path=\"README.md\"]')")
        self.assertEqual(self.side_tree(), ["git_graph", "diff.py", "page/js", "diff.js"])
        self.assertIn("modified", self.page.locator('.side .fv-file[data-path="git_graph/diff.py"]').get_attribute("class"))
        self.assertEqual(self.page.locator(".side .fv-diff").get_attribute("aria-pressed"), "true")
        self.page.keyboard.press("Escape")
        self.page.wait_for_selector('.side .fv-row[data-dir="hooks"]')

    def test_sidebar_file_opens_in_panel(self) -> None:
        """A sidebarban a lenyitott commit fájljára kattintva a fájl a panelben nyílik le, a nézetben."""
        self.open_commit()
        self.open_side()
        self.page.locator('.side .fv-file[data-path="page/js/diff.js"]').click()
        file = self.page.locator('.details .file[data-path="page/js/diff.js"]')
        self.page.wait_for_selector('.details .file[data-path="page/js/diff.js"] + .diff .cm-editor')
        self.settle()
        self.assertEqual(file.get_attribute("aria-expanded"), "true")
        self.assertEqual(self.page.locator(".fv").count(), 0)
        sc, fb = self.page.locator(".scroll").bounding_box(), file.bounding_box()
        self.assertTrue(sc["y"] <= fb["y"] < sc["y"] + sc["height"], (sc, fb))

    def test_diff_button_like_side_button(self) -> None:
        """A fa diff-gombja olyan, mint az eszközsor sidebar-gombja: azonos méret, 20 px-es (`md`) ikon."""
        self.open_side()
        box = lambda sel: self.page.locator(sel).bounding_box()  # noqa: E731
        for sel in ("#sideBtn", ".side .fv-diff"):
            with self.subTest(sel):
                self.assertEqual((box(sel)["width"], box(sel)["height"]), (32, 32))
                self.assertEqual(box(f"{sel} svg")["width"], 20)
        self.assertIn("select", self.page.locator(".side .fv-diff").get_attribute("class"))

    def test_settings_in_footer(self) -> None:
        """A beállítások gombja a láblécben, a téma mellett jobbra."""
        foot = self.page.locator("#foot").bounding_box()
        btn, theme = self.page.locator("#settingsBtn").bounding_box(), self.page.locator("#themeBtn").bounding_box()
        self.assertTrue(foot["y"] <= btn["y"] < foot["y"] + foot["height"])
        self.assertGreater(btn["x"], theme["x"])

    def test_footer(self) -> None:
        """A lábléc 28 px magas, a teljes nézetben is látszik, és a commitszám helyén a nézett fájl útja áll."""
        with self.subTest("Adott a lábléc a commitszámmal"):
            self.assertEqual(self.page.locator("#foot").bounding_box()["height"], 28)
            self.assertTrue(self.page.locator("#counter").is_visible())
        with self.subTest("Ha a teljes nézetben a page/js/diff.js látszik"):
            self.open_commit()
            self.open_full()
            self.page.locator('.fv-file[data-path="page/js/diff.js"]').click()
            self.settle()
        with self.subTest("Akkor a lábléc látszik, a commitszám helyén az út"):
            self.assertTrue(self.page.locator("#foot").is_visible())
            self.assertFalse(self.page.locator("#counter").is_visible())
            self.assertEqual(self.page.locator("#footPath").inner_text(), "page/js/diff.js")
            foot = self.page.locator("#foot").bounding_box()
            self.assertEqual(foot["y"] + foot["height"], self.HEIGHT)
        with self.subTest("És bezárva újra a commitszám"):
            self.page.keyboard.press("Escape")
            self.settle()
            self.assertTrue(self.page.locator("#counter").is_visible())
            self.assertFalse(self.page.locator("#footPath").is_visible())

    def test_diff_filter(self) -> None:
        """A diff-szűrő a commitból nyitva bekapcsolva: csak a változott fájlok; kikapcsolva minden fájl."""
        self.open_commit()
        self.open_full()
        diff = self.page.locator(".fv-diff")
        self.assertEqual(diff.get_attribute("aria-pressed"), "true")
        gray = self.page.evaluate("""() => { const p = Object.assign(document.createElement('span'), { style: 'background: var(--bg-3)' });
          document.body.append(p); const c = getComputedStyle(p).backgroundColor; p.remove(); return c; }""")
        self.assertEqual(diff.evaluate("e => getComputedStyle(e).backgroundColor"), gray)   # mint az app: szürke, nem kék
        self.assertNotIn("README.md", self.tree())
        diff.click()
        self.page.wait_for_selector('.fv-row[data-dir="hooks"]')
        self.assertEqual(diff.get_attribute("aria-pressed"), "false")
        self.assertIn("README.md", self.tree())

    def test_tree_error(self) -> None:
        """Ha a fájllista nem jön (az app nem kínálja a file_tree-t), a hiba pirosan a fában áll."""
        # Adott: a file_tree hívás elbukik
        self.page.evaluate("""() => { const mcp = GIT_GRAPH.mcp, call = mcp.callTool.bind(mcp);
          mcp.callTool = (s, tool, ...rest) => tool === 'file_tree'
            ? Promise.reject({ code: 'not_in_manifest', message: 'nincs file_tree' }) : call(s, tool, ...rest); }""")
        # Ha a Fejlesztő minden fájlt kér
        self.open_commit()
        self.open_full()
        self.page.locator(".fv-diff").click()
        # Akkor a hiba a fában, piros színnel
        err = self.page.locator(".fv-list .fv-error")
        self.assertIn("A fájllista nem tölthető be: nincs file_tree", err.inner_text())
        red = self.page.evaluate("""() => { const p = Object.assign(document.createElement('span'), { style: 'color: var(--critical)' });
          document.body.append(p); const c = getComputedStyle(p).color; p.remove(); return c; }""")
        self.assertEqual(err.evaluate("e => getComputedStyle(e).color"), red)

    def test_escape_back(self) -> None:
        """Esc-re a teljes nézet bezárul, a panelben a kijelölt git_graph/diff.py lenyitva, a lap odagörget."""
        self.open_commit()
        self.page.locator('.details .file[data-path="page/js/diff.js"]').click()
        self.settle()
        self.open_full("page/js/diff.js")
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
        self.page.locator(".fv-diff").click()
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
        self.page.locator(".fv-diff").click()
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
        self.page.locator(".fv-diff").click()
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
        self.page.locator("#sideBtn").click()
        self.page.locator(".side .fv-diff").click()
        self.page.wait_for_selector('.side .fv-row[data-dir="csend"]')
        cls = lambda d: self.page.locator(f'.fv-row[data-dir="{d}"]').get_attribute("class")  # noqa: E731
        self.assertIn("modified", cls("vegyes"))
        self.assertIn("added", cls("uj"))
        self.assertNotIn("modified", cls("csend"))
        gone = self.page.locator('.fv-file[data-path="vegyes/regi.py"] .name')
        self.assertEqual(gone.evaluate("e => getComputedStyle(e).textDecorationLine"), "line-through")
        red = self.page.evaluate("""() => { const p = Object.assign(document.createElement('span'), { style: 'color: var(--del)' });
          document.body.append(p); const c = getComputedStyle(p).color; p.remove(); return c; }""")
        self.assertEqual(gone.evaluate("e => getComputedStyle(e).color"), red)


LONG = "page/vendor/egy/nagyon/hosszu/mappa/lanc/ami/nem/fer/ki/a/panelben/sehogy/fajl_hosszu_nevvel.py"


class FileHeadTest(PageTestCase):
    """A fájlfejléc: a GitHub-ikon a fájlnév után, a teljes képernyőé a jobb szélen; a nézetváltó a diff saját
    felső sávjában. A pusholt állapotot egy kézzel írt `origin/main` adja (hálózat nélkül)."""
    WIDTH, HEIGHT = 1100, 760

    @classmethod
    def prepare(cls, repo: Path) -> None:
        write(repo, {"doc.md": "# Cím\n\nElső.\n", "app.py": "a = 1\n", LONG: "x = 1\n"})
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "fej: alap")
        # a szerző képe friss „nincs” a gyorstárban: a pusholt commit ne indítson GitHub-hívást
        (repo.parent / ".git-graph" / "avatars.json").write_text(
            json.dumps({"teszt@x.hu": {"img": None, "at": time.time()}}), encoding="utf-8")
        git_in(repo, "remote", "add", "origin", "https://github.com/o/r.git")
        git_in(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        write(repo, {"doc.md": "# Cím\n\nMásodik.\n", "app.py": "a = 2\n"})
        git_in(repo, "commit", "-qam", "fej: nem pusholt")

    def row(self, subject: str, name: str):
        self.page.locator("#rows .row", has_text=subject).click()
        self.settle()
        return self.page.locator(f'.details .file[data-path="{name}"]')

    def test_github_after_name(self) -> None:
        """Pusholt commitnál a GitHub-ikon közvetlenül a fájlnév után, a teljes képernyőé a sor jobb szélén."""
        file = self.row("fej: alap", "app.py")
        name, gh = file.locator(".path").bounding_box(), file.locator("a[href]").bounding_box()
        full, box = file.locator("[data-full]").bounding_box(), file.bounding_box()
        self.assertLessEqual(abs(gh["x"] - (name["x"] + name["width"])), 6)
        self.assertLessEqual(box["x"] + box["width"] - (full["x"] + full["width"]), 6)

    def test_long_path_cut(self) -> None:
        """A hosszú út vágódik, a GitHub-ikon a soron belül, a +N −N előtt marad."""
        self.resize(700)
        file = self.row("fej: alap", LONG)
        path = file.locator(".path")
        self.assertGreater(path.evaluate("e => e.scrollWidth - e.clientWidth"), 0)
        gh, churn = file.locator("a[href]").bounding_box(), file.locator(".churn").bounding_box()
        self.assertLessEqual(gh["x"] + gh["width"], churn["x"] + 1)

    def test_unpushed_same_place(self) -> None:
        """Nem pusholt commitnál nincs GitHub-ikon, a teljes képernyőé ugyanúgy a jobb szélen."""
        file = self.row("fej: nem pusholt", "app.py")
        self.assertEqual(file.locator("a[href]").count(), 0)
        full, box = file.locator("[data-full]").bounding_box(), file.bounding_box()
        self.assertLessEqual(box["x"] + box["width"] - (full["x"] + full["width"]), 6)

    def test_mode_switch_in_own_bar(self) -> None:
        """A markdown nézetváltója a diff saját felső sávjában: a tartalom alatta kezdődik, nem lóg rá."""
        file = self.row("fej: nem pusholt", "doc.md")
        file.click()
        self.page.wait_for_selector('.details .file[data-path="doc.md"] + .diff .md-doc:visible')
        self.settle()
        seg = self.page.locator('.details .file[data-path="doc.md"] + .diff .md-seg').bounding_box()
        doc = self.page.locator('.details .file[data-path="doc.md"] + .diff .md-doc:visible').first.bounding_box()
        self.assertLessEqual(seg["y"] + seg["height"], doc["y"] + 1)
        self.assertGreaterEqual(seg["y"], file.bounding_box()["y"] + file.bounding_box()["height"] - 1)


class WipFullViewTest(PageTestCase):
    """A WIP sor teljes nézete a munkakönyvtár mostani állapotát mutatja."""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "main-4-5.txt").write_text("a munkakönyvtár mostani állapota\n", encoding="utf-8")

    def test_open_wip(self) -> None:
        self.page.locator(".row.uncommitted", has_text="Nem commitolt").click()
        self.settle()
        self.page.locator('.details .file[data-path="main-4-5.txt"]').click()
        self.settle()
        self.page.locator('.details .file[data-path="main-4-5.txt"] [data-full]').click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.assertIn("main-4-5.txt", self.page.locator(".fv-path").inner_text())
        self.assertIn("a munkakönyvtár mostani állapota", self.page.locator(".fv-box .cm-content").inner_text())

    def test_open_own_with_wip(self) -> None:
        """A sidebar nyitott commit nélkül, WIP sorral: minden fájl, a diff-szűrő kikapcsolva, de használható."""
        self.page.locator("#sideBtn").click()
        self.page.wait_for_selector(".side .fv-row")
        diff = self.page.locator(".side .fv-diff")
        self.assertFalse(diff.is_disabled())
        self.assertEqual(diff.get_attribute("aria-pressed"), "false")


if __name__ == "__main__":
    unittest.main()
