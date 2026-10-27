"""A lap elrendezése böngészőben: a gráf pöttyei a sorokhoz, a sorok töréspontjai, a görgetés."""
from __future__ import annotations

import unittest

from harness import PageTestCase

# Minden listasor közepe és a hozzá legközelebbi commit-pötty (r 4: commit, r 5:
# merge / ál-sor) közepe, a képernyőn mérve. A `drawGraph` a sorok `offsetTop`-jából
# rajzol: ha a sor és a gráf koordinátái elcsúsznak, a kettő eltér.
DOT_OFFSETS = """() => {
  const dots = [...document.querySelectorAll('#lanes circle')]
    .filter(c => ['4', '5'].includes(c.getAttribute('r')))
    .map(c => { const r = c.getBoundingClientRect(); return r.top + r.height / 2; });
  return [...document.querySelectorAll('#rows .row')].map(row => {
    const r = row.getBoundingClientRect(), mid = r.top + r.height / 2;
    return Math.min(...dots.map(y => Math.abs(y - mid)));
  });
}"""

# Az első sor, amelyik a lista teteje alatt kezdődik: a sorszáma, a teteje a lista
# tetejétől, és a felül ragadó napfejléc alja.
TOP_ROW = """() => {
  const s = document.querySelector('.scroll').getBoundingClientRect().top;
  const rows = [...document.querySelectorAll('#rows .row')];
  const i = rows.findIndex(r => r.getBoundingClientRect().top >= s + 1);
  const day = [...document.querySelectorAll('.day.stuck:not(.gone)')].at(-1);
  return { i, top: rows[i].getBoundingClientRect().top - s,
           dayBottom: day ? day.getBoundingClientRect().bottom - s : null };
}"""


class GraphTest(PageTestCase):
    def assert_dots_on_rows(self) -> None:
        offsets = self.page.evaluate(DOT_OFFSETS)
        self.assertTrue(offsets)
        self.assertLess(max(offsets), 1, "a pötty nem a sora közepén van")

    def test_dots_follow_rows(self) -> None:
        self.assertGreater(self.page.locator("#rows .day").count(), 1)   # napfejlécek a sorok közt
        self.assert_dots_on_rows()

    def test_dots_after_open_panel(self) -> None:
        self.page.locator("#rows .row").nth(3).click()
        self.settle()
        self.assertEqual(self.page.locator("#rows .details").count(), 1)
        self.assert_dots_on_rows()

    def test_dots_after_resize(self) -> None:
        self.resize(420)                           # kétsoros sorok: magasabbak
        self.assert_dots_on_rows()


class FitRowsTest(PageTestCase):
    WIDTH = 1300                                   # a HEAD sorának badge-ei is egy sorban férnek el (CDS-méretben)
    def row_width(self) -> float:
        return self.page.evaluate("document.querySelector('#rows .row-in').clientWidth")

    def classes(self, cls: str) -> int:
        return self.page.locator(f"#rows .row.{cls}").count()

    def test_wide_one_line(self) -> None:
        self.assertGreaterEqual(self.row_width(), 480)
        self.assertEqual(self.classes("two"), 0)
        self.assertEqual(self.classes("three"), 0)

    def test_narrow_two_lines(self) -> None:
        self.resize(500)
        self.assertLess(self.row_width(), 480)
        plain = self.page.locator("#rows .row:not(:has(.refs))").count()
        self.assertEqual(self.classes("two"), plain)              # minden badge nélküli sor
        self.assertEqual(self.page.locator("#rows .row.two:has(.refs)").count(), 0)

    def test_min_width(self) -> None:
        self.resize(300)
        narrow = self.row_width()
        self.resize(200)
        self.assertEqual(self.row_width(), narrow)               # 320 alá nem szűkül
        self.assertEqual(narrow, 320)

    def test_crowded_refs_three_lines(self) -> None:
        head = self.page.locator("#rows .row").first             # a HEAD: két ág, két tag
        self.assertFalse(self.has_class(head, "three"))
        self.resize(360)
        self.assertTrue(self.has_class(head, "three"))

    def has_class(self, loc, cls: str) -> bool:
        return loc.evaluate("(el, cls) => el.classList.contains(cls)", cls)


class StepRowsTest(PageTestCase):
    HEIGHT = 400

    def test_one_notch_one_commit(self) -> None:
        box = self.page.locator(".scroll").bounding_box()
        self.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        # Az első lépés az első sort igazítja a napfejléc alá, a többi egy-egy commitot lép.
        for step in range(9):
            self.page.mouse.wheel(0, 100)
            self.page.wait_for_timeout(150)                       # ne lecsengésnek lássa
            row = self.page.evaluate(TOP_ROW)
            self.assertEqual(row["i"], step, "egy kattanás nem egy commitot lépett")
            self.assertAlmostEqual(row["top"], 20, delta=1)        # STEP_TOP: a napfejléc alatt
            if row["dayBottom"] is not None:
                self.assertLessEqual(row["dayBottom"], row["top"] + 0.5, "a napfejléc takarja a sort")
        for step in range(1, 4):
            self.page.mouse.wheel(0, -100)
            self.page.wait_for_timeout(150)
            self.assertEqual(self.page.evaluate(TOP_ROW)["i"], 8 - step)


if __name__ == "__main__":
    unittest.main()
