"""A diff (a `.md` renderelt és a kódfájl nyers diffje): a csak beszúrt vagy csak törölt szavú
sornál egy változat látszik."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from harness import PageTestCase

OLD = """---
leiras: régi
eszkozok: egy, ketto, harom
---

# Cím

Az első bekezdés marad, ahogy volt.

Ide szavak kerülnek be.

Innen szavak tűnnek el, nagyon.

Itt egy szó cserélődik.

- Egy listaelem bővül.
- Egy listaelem rövidül, nagyon.

## Régi címsor
"""
NEW = """---
leiras: régi
eszkozok: egy, harom
---

# Cím

Az első bekezdés marad, ahogy volt.

Ide új szavak kerülnek be, a végére is.

Innen szavak tűnnek el.

Itt egy kifejezés cserélődik.

- Egy listaelem bővül, két sorba
  törve.
- Egy listaelem rövidül.

## Régi címsor, kiegészítve
"""
OLD_PY = "x = hivas(a)\ny = 1\nz = masik(a, b, c)\nw = 2\nv = csere(a)\n"
NEW_PY = "x = hivas(a, b)\ny = 1\nz = masik(a)\nw = 2\nv = mas(a)\n"


class MdDiffTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        def git(*args: str) -> None:
            subprocess.run(["git", "-c", "user.name=Teszt Elek", "-c", "user.email=teszt@x.hu",
                            "-C", str(repo), *args], check=True, capture_output=True)
        doc = repo / "doksi.md"
        code = repo / "kod.py"
        doc.write_text(OLD, encoding="utf-8")
        code.write_text(OLD_PY, encoding="utf-8")
        git("add", ".")
        git("commit", "-qm", "doksi")
        doc.write_text(NEW, encoding="utf-8")
        code.write_text(NEW_PY, encoding="utf-8")
        git("commit", "-qam", "doksi: módosítva")

    def open_file(self, name: str) -> None:
        self.page.locator("#rows .row", has_text="doksi: módosítva").click()
        self.settle()
        self.page.locator("#rows .details .file", has_text=name).click()

    def test_one_sided_paragraph(self) -> None:
        self.open_file("doksi.md")
        self.page.wait_for_selector(".md-doc")
        blocks = self.page.locator(".diff-uni .md-blk").evaluate_all(
            "bs => bs.map(b => [b.className.replace('md-blk', '').trim(), b.textContent,"
            " [...b.querySelectorAll('mark')].map(m => m.textContent)])")
        self.assertEqual(blocks[2:], [            # előtte a címsor és a környezet
            ["add only", "Ide új szavak kerülnek be, a végére is.", [" új", ", a végére is"]],
            ["del only", "Innen szavak tűnnek el, nagyon.", [", nagyon"]],
            ["del", "Itt egy szó cserélődik.", ["szó"]],
            ["add", "Itt egy kifejezés cserélődik.", ["kifejezés"]],
            ["add only", "•Egy listaelem bővül, két sorba\ntörve.", [", két sorba", "törve"]],
            ["del only", "•Egy listaelem rövidül, nagyon.", [", nagyon"]],
            ["add only", "Régi címsor, kiegészítve", [", kiegészítve"]],
        ])
        # a front matter (kódblokk): csak a törölt sor, a kiemelt szóval
        lines = self.page.locator(".diff-uni .md-cl").evaluate_all(
            "ls => ls.map(l => [l.className.replace('md-cl', '').trim(), l.textContent,"
            " [...l.querySelectorAll('mark')].map(m => m.textContent)])")
        self.assertEqual(lines, [["", "leiras: régi", []], ["del only", "eszkozok: egy, ketto, harom", ["ketto, "]]])
        # az `only` sor háttere semleges, a szó kiemelése ugyanaz, mint a vegyes sorban
        bg = self.page.locator(".diff-uni .md-blk.del.only").first.evaluate(
            "b => [getComputedStyle(b).backgroundColor, getComputedStyle(b.querySelector('mark')).backgroundColor,"
            " getComputedStyle(document.querySelector('.md-blk.del:not(.only) mark')).backgroundColor]")
        self.assertEqual(bg[0], "rgba(0, 0, 0, 0)")
        self.assertEqual(bg[1], bg[2])

    def test_md_split(self) -> None:
        """Széles nézetben a markdown is side-by-side: blokkonként egy sor, balra a régi, jobbra az új."""
        self.resize(1400)
        self.open_file("doksi.md")
        self.page.wait_for_selector(".diff-split .md-row")
        rows = self.page.locator(".diff-split .md-row:has(.md-blk)").evaluate_all(
            "rs => rs.map(r => [...r.children].map(c => { const b = c.querySelector('.md-blk');"
            " return b ? b.className.replace(/md-blk/, '').trim() : '-'; }))")
        self.assertEqual(rows[2:], [               # előtte a címsor és a környezet
            ["", "add only"],                       # csak beszúrás: a régi oldal változatlan
            ["del only", ""],
            ["del", "add"],
            ["", "add only"],
            ["del only", ""],
            ["", "add only"],
        ])

    def test_one_sided_code_line(self) -> None:
        self.open_file("kod.py")
        self.page.wait_for_selector(".diff-uni .diff-line")
        lines = self.page.locator(".diff-uni .diff-line").evaluate_all(
            "ls => ls.map(l => [l.className.replace(/diff-line|mono/g, '').trim(), l.querySelector('.tx').textContent,"
            " [...l.querySelectorAll('mark')].map(m => m.textContent)])")
        self.assertEqual(lines, [
            ["add only", "x = hivas(a, b)", [", b"]],
            ["", "y = 1", []],
            ["del only", "z = masik(a, b, c)", [", b, c"]],
            ["", "w = 2", []],
            ["del", "v = csere(a)", ["csere"]],
            ["add", "v = mas(a)", ["mas"]],
        ])

    def test_one_sided_split(self) -> None:
        """Side-by-side: az érintetlen oldal változatlan sorként, a másik `only`."""
        self.resize(1400)
        self.open_file("kod.py")
        self.page.wait_for_selector(".diff-split .split-row")
        rows = self.page.locator(".diff-split .split-row").evaluate_all(
            "rs => rs.map(r => [...r.querySelectorAll('.half')].map(h => h.className.replace('half', '').trim()"
            " + ':' + h.querySelector('.sg').textContent))")
        self.assertEqual(rows, [
            [":", "add only:+"],
            [":", ":"],
            ["del only:−", ":"],
            [":", ":"],
            ["del:−", "add:+"],
        ])


if __name__ == "__main__":
    unittest.main()
