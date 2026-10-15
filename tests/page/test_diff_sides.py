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
OLD_REORDER = "## 1. Alfa szakasz\n\nRégi egy szöveg.\n\n## 2. Béta szakasz\n\nRégi kettő szöveg.\n"
NEW_REORDER = "## 1. Alfa szakasz!\n\nÚj első tartalom.\n\n## 2. Béta szakasz!\n\nÚj második tartalom.\n"
OLD_PARA = "Bevezető mondat.\nFontos rész itt.\n\nElső mondat.\nMásodik mondat.\nHarmadik mondat.\n"
NEW_PARA = "Fontos rész itt, bővítve.\n\nElső mondat.\nHarmadik mondat.\n"
OLD_LAST = "| Lépés | Mit |\n| --- | --- |\n| 1. | első |\n| 2. | verzió, deploy, tag |\n\nKivett bekezdés.\n"
NEW_LAST = "| Lépés | Mit |\n| --- | --- |\n| 1. | másik |\n| 2. | verzió, tag |\n"
OLD_GAP = "Első.\n\nMásodik.\n\nHarmadik.\n\nNegyedik régi szöveg.\n"
NEW_GAP = "Első.\n\nMásodik.\n\nHarmadik.\n\nNegyedik más szöveg.\n"
OLD_WRAP = ("- **Egy**: első pont.\n- **Kivétel**: doksi, config, egyeztetés alatt álló finomítás. Ha\n"
            "  tesztelhető, kimondja.\n\nA runner a stackből, az első teszt a változásra.\n\nKöztes bekezdés.\n\nRégi zárás.\n")
NEW_WRAP = ("- **Egy**: első pont.\n- **Kivétel**: doksi, config, az AI-nak szóló szöveg,\n"
            "  egyeztetés alatt álló finomítás. Új mondat itt. Ha\n  tesztelhető, kimondja.\n\n"
            "A runner a stackből, az első teszt a változásra. Az új runner a check\n"
            "része lesz, különben nem fut.\n\nKöztes bekezdés.\n\nÚj zárás.\n")
OLD_JSON = '[\n  "Bash(git reset --hard*)"\n]\n'
NEW_JSON = '[\n  "Bash(git reset --hard*)",\n  "Bash(git mv *)",\n  "Bash(git rm *)"\n]\n'
OLD_REWRAP = "Első bekezdés sora\nfolytatás itt.\n\nKöztes.\n\nRégi zárás.\n"
NEW_REWRAP = "Első bekezdés sora folytatás itt.\n\nKöztes.\n\nÚj zárás.\n"
TABLE_ROWS = [f"| s{i} | sor {i} szövege |" for i in range(10)]
OLD_TABLE = "| Név | Mi |\n| --- | --- |\n" + "\n".join(TABLE_ROWS) + "\n"
NEW_TABLE = ("| Név | Mi |\n| --- | --- |\n"
             + "\n".join([*TABLE_ROWS[:2], "| s2 | sor |", "| s3 | másik |", *TABLE_ROWS[4:8], "| új | új sor, jóval hosszabb szöveggel, ami egy keskeny oszlopban több sorba is törik, mert a cella szélessége a panel felénél is kisebb, így a magassága nagyobb a helyőrzőénél |", *TABLE_ROWS[8:]]) + "\n")
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
        (repo / "rend.md").write_text(OLD_REORDER, encoding="utf-8")
        (repo / "tabla.md").write_text(OLD_TABLE, encoding="utf-8")
        (repo / "ujratord.md").write_text(OLD_REWRAP, encoding="utf-8")
        (repo / "jog.json").write_text(OLD_JSON, encoding="utf-8")
        (repo / "tordel.md").write_text(OLD_WRAP, encoding="utf-8")
        (repo / "kihagy.md").write_text(OLD_GAP, encoding="utf-8")
        (repo / "utolso.md").write_text(OLD_LAST, encoding="utf-8")
        (repo / "bekezdes.md").write_text(OLD_PARA, encoding="utf-8")
        doc.write_text(OLD, encoding="utf-8")
        code.write_text(OLD_PY, encoding="utf-8")
        git("add", ".")
        git("commit", "-qm", "doksi")
        doc.write_text(NEW, encoding="utf-8")
        code.write_text(NEW_PY, encoding="utf-8")
        (repo / "rend.md").write_text(NEW_REORDER, encoding="utf-8")
        (repo / "tabla.md").write_text(NEW_TABLE, encoding="utf-8")
        (repo / "ujratord.md").write_text(NEW_REWRAP, encoding="utf-8")
        (repo / "jog.json").write_text(NEW_JSON, encoding="utf-8")
        (repo / "tordel.md").write_text(NEW_WRAP, encoding="utf-8")
        (repo / "kihagy.md").write_text(NEW_GAP, encoding="utf-8")
        (repo / "utolso.md").write_text(NEW_LAST, encoding="utf-8")
        (repo / "bekezdes.md").write_text(NEW_PARA, encoding="utf-8")
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
        # a nézetváltó gomb (úszik) mellett sem szűkül az első sor: a két oszlop határa egy vonalban
        widths = self.page.locator(".diff-split .md-row").evaluate_all(
            "rs => [...new Set(rs.map(r => Math.round(r.getBoundingClientRect().width)))]")
        self.assertEqual(len(widths), 1, widths)
        self.assertEqual(rows[2:], [               # előtte a címsor és a környezet
            ["", "add only"],                       # csak beszúrás: a régi oldal változatlan
            ["del only", ""],
            ["del", "add"],
            ["", "add only"],
            ["del only", ""],
            ["", "add only"],
        ])

    def test_md_new_block_in_place(self) -> None:
        """Átrendezett szövegben a pár nélküli új bekezdés a helyén (nem a törölt rész végén), a két pár
        közti pár nélküli törölt bekezdés mellett."""
        self.resize(1400)
        self.open_file("rend.md")
        self.page.wait_for_selector(".diff-split .md-row")
        rows = self.page.locator(".diff-split .md-row").evaluate_all(
            "rs => rs.map(r => [...r.children].map(c => c.textContent.trim()))")
        self.assertEqual(rows, [
            ["1. Alfa szakasz", "1. Alfa szakasz!"],
            ["Régi egy szöveg.", "Új első tartalom."],     # a pár nélküliek egymás mellett, a helyükön
            ["2. Béta szakasz", "2. Béta szakasz!"],
            ["Régi kettő szöveg.", "Új második tartalom."],
        ])

    def test_md_table_rows_aligned(self) -> None:
        """A táblázat két oldalán ugyanazok a sorok állnak egymás mellett (a hiányzó helyén helyőrző)."""
        self.resize(1400)
        self.open_file("tabla.md")
        self.page.wait_for_selector(".diff-split .md-row table")
        sides = self.page.locator(".diff-split .md-row").first.evaluate(
            "r => [...r.children].map(c => [...c.querySelectorAll('tr')].map(t => t.cells[0].textContent.trim()))")
        # a párban álló sorok egyforma magasak (a jobb oldali új sor helyőrzője is)
        heights = self.page.locator(".diff-split .md-row").first.evaluate(
            "r => [...r.children].map(c => [...c.querySelectorAll('tr')].map(t => t.getBoundingClientRect().height))")
        self.assertEqual(heights[0], heights[1])
        self.resize(1100)                          # keskenyebben más a tördelés: újra egyforma
        heights = self.page.locator(".diff-split .md-row").first.evaluate(
            "r => [...r.children].map(c => [...c.querySelectorAll('tr')].map(t => t.getBoundingClientRect().height))")
        self.assertEqual(heights[0], heights[1])
        self.assertEqual(sides, [
            ["Név", "···", "s1", "s2", "s3", "s4", "···", "s7", "", "s8", "···"],
            ["Név", "···", "s1", "s2", "s3", "s4", "···", "s7", "új", "s8", "···"],
        ])

    def test_md_table_row_one_sided(self) -> None:
        """Táblázatban a csak törlésű sor egyoldalú akkor is, ha a szomszéd sora (egy futamban) cserélődött."""
        self.resize(1400)
        self.open_file("tabla.md")
        self.page.wait_for_selector(".diff-split .md-row table")
        kinds = self.page.locator(".diff-split .md-row").first.evaluate(
            "r => [...r.children].map(c => Object.fromEntries([...c.querySelectorAll('tr')]"
            ".filter(t => /^s[23]$/.test(t.cells[0].textContent.trim()))"
            ".map(t => [t.cells[0].textContent.trim(), t.className])))")
        self.assertEqual(kinds, [{"s2": "del only", "s3": "del"}, {"s2": "", "s3": "add"}])
        uni = self.page.locator(".diff-uni .md-table tr").evaluate_all(
            "ts => ts.filter(t => /^s[23]$/.test(t.cells[0].textContent.trim()))"
            ".map(t => [t.cells[0].textContent.trim(), t.className])")
        self.assertEqual(uni, [["s2", "del only"], ["s3", "del"], ["s3", "add"]])

    def test_md_paragraph_as_unit(self) -> None:
        """A bekezdés egy egység: a bővített bekezdés két változata egy sorban, a törölt sor kiemelt."""
        self.resize(1400)
        self.open_file("bekezdes.md")
        self.page.wait_for_selector(".diff-split .md-row")
        blk = "b => b ? [b.className.replace('md-blk', '').trim(), b.textContent, [...b.querySelectorAll('mark')].map(m => m.textContent)] : null"
        rows = self.page.locator(".diff-split .md-row").evaluate_all(
            f"rs => rs.map(r => [...r.children].map(c => ({blk})(c.querySelector('.md-blk:not(.md-none)'))))")
        self.assertEqual(rows, [
            [["del", "Bevezető mondat.\nFontos rész itt.", ["Bevezető mondat."]],
             ["add", "Fontos rész itt, bővítve.", [", bővítve"]]],
            [["del only", "Első mondat.\nMásodik mondat.\nHarmadik mondat.", ["Második mondat."]],
             ["", "Első mondat.\nHarmadik mondat.", []]],
        ])
        uni = self.page.locator(".diff-uni .md-blk").evaluate_all(f"bs => bs.map({blk})")
        self.assertEqual(uni[2], ["del only", "Első mondat.\nMásodik mondat.\nHarmadik mondat.", ["Második mondat."]])

    def test_raw_unpaired_side_by_side(self) -> None:
        """Nyers side-by-side: a két pár közti pár nélküli törölt és új sor egy sorban."""
        self.resize(1400)
        self.open_file("rend.md")
        self.page.locator("[data-md-mode]").first.click()          # nyers diff
        self.page.wait_for_selector(".diff-split .split-row")
        rows = self.page.locator(".diff-split .split-row").evaluate_all(
            "rs => rs.map(r => [...r.querySelectorAll('.half')].map(h => h.querySelector('.tx')?.textContent ?? null))")
        self.assertIn(["Régi egy szöveg.", "Új első tartalom."], rows)
        self.assertIn(["Régi kettő szöveg.", "Új második tartalom."], rows)
        self.page.locator("[data-md-mode]").first.click()          # vissza (a lap megjegyzi)

    def test_md_table_last_row(self) -> None:
        """A táblázat utolsó sorának új változata a régi mellé kerül, akkor is, ha utána egy bekezdés kimaradt."""
        self.resize(1400)
        self.open_file("utolso.md")
        self.page.wait_for_selector(".diff-split .md-row")
        rows = self.page.locator(".diff-split .md-row").evaluate_all(
            "rs => rs.map(r => [...r.children].map(c => [...c.querySelectorAll('tr, .md-blk')]"
            ".map(e => e.tagName === 'TR' ? [e.cells[0].tagName, e.cells[0].textContent.trim(), e.className]"
            " : ['P', e.textContent.trim(), e.className.replace('md-blk', '').trim()])))")
        self.assertEqual(rows, [
            [[["TH", "Lépés", ""], ["TD", "1.", "del"], ["TD", "2.", "del only"]],
             [["TH", "Lépés", ""], ["TD", "1.", "add"], ["TD", "2.", ""]]],
            [[["P", "Kivett bekezdés.", "del"]], [["P", "", "md-none"]]],
        ])

    def test_md_toggle_floats(self) -> None:
        """A nézetváltó lebegő gomb: nem foglal helyet, a tartalom a diff tetején kezdődik, mindkét nézetben."""
        self.open_file("kihagy.md")
        for width, view in ((1400, ".diff-split"), (900, ".diff-uni")):
            self.resize(width)
            box, first = self.page.evaluate(
                f"[document.querySelector('.diff:has(.md-mode)'), document.querySelector('{view}').firstElementChild]"
                ".map(e => e.getBoundingClientRect().top)")
            self.assertLess(first - box, 10, view)        # csak a doboz belső margója, nincs üres sor
        self.assertEqual(self.page.locator(".md-mode").evaluate("b => getComputedStyle(b).position"), "absolute")

    def test_raw_one_sided_run(self) -> None:
        """Nyers side-by-side, csak beszúrásos futam: a sorok felülről egymás mellett (nincs lyuk), és az
        egészében új sor teljes zöld (nem semleges)."""
        self.resize(1400)
        self.open_file("tordel.md")
        self.page.locator("[data-md-mode]").first.click()          # nyers diff
        self.page.wait_for_selector(".diff-split .split-row")
        rows = self.page.locator(".diff-split .split-row").evaluate_all(
            "rs => rs.map(r => [...r.querySelectorAll('.half')].map(h => h.querySelector('.tx')"
            " ? [h.className.replace('half', '').trim(), h.querySelector('.tx').textContent,"
            " [...h.querySelectorAll('mark')].map(m => m.textContent).join('|')] : null))")
        self.page.locator("[data-md-mode]").first.click()          # vissza (a lap megjegyzi)
        texts = [[c and c[1] for c in r] for r in rows]
        at = texts.index(["- **Egy**: első pont.", "- **Egy**: első pont."])
        self.assertEqual(texts[at + 1][0], "- **Kivétel**: doksi, config, egyeztetés alatt álló finomítás. Ha")
        self.assertEqual(texts[at + 1][1], "- **Kivétel**: doksi, config, az AI-nak szóló szöveg,")
        whole = next(r[1] for r in rows if r[1] and r[1][1] == "része lesz, különben nem fut.")
        self.assertEqual(whole, ["add", "része lesz, különben nem fut.", ""])     # egészében új: teljes zöld

    def test_whole_new_line_stays_green(self) -> None:
        """Csak beszúrásos futamban az egészében új sor teljes zöld, csak a szavas változás semleges."""
        self.open_file("jog.json")
        self.page.wait_for_selector(".diff .diff-line")
        lines = self.page.locator(".diff .diff-line").evaluate_all(
            "ls => ls.filter(l => /add|del/.test(l.className)).map(l => [l.className.replace(/diff-line|mono/g, '').trim(),"
            " l.querySelector('.tx').textContent.trim(), [...l.querySelectorAll('mark')].map(m => m.textContent)])")
        self.assertEqual(lines, [
            ["add only", '"Bash(git reset --hard*)",', [","]],
            ["add", '"Bash(git mv *)",', []],
            ["add", '"Bash(git rm *)"', []],
        ])

    def test_raw_rewrap_unchanged(self) -> None:
        """Tiszta újratördelés a nyers diffben: változatlan sorként, jel és szín nélkül, mindkét nézetben."""
        self.resize(1400)
        self.open_file("ujratord.md")
        self.page.locator("[data-md-mode]").first.click()          # nyers diff
        self.page.wait_for_selector(".diff-split .split-row")
        half = ("h => h.querySelector('.tx') ? [h.className.replace('half', '').trim(), h.querySelector('.sg').textContent,"
                " h.querySelector('.tx').textContent] : null")
        rows = self.page.locator(".diff-split .split-row").evaluate_all(
            f"rs => rs.map(r => [...r.querySelectorAll('.half')].map({half}))")
        self.assertEqual(rows[:2], [
            [["", "", "Első bekezdés sora"], ["", "", "Első bekezdés sora folytatás itt."]],
            [["", "", "folytatás itt."], None],
        ])
        uni = self.page.locator(".diff-uni .diff-line").evaluate_all(
            "ls => ls.map(l => [l.className.replace(/diff-line|mono/g, '').trim(), l.querySelector('.tx').textContent])")
        self.page.locator("[data-md-mode]").first.click()          # vissza (a lap megjegyzi)
        self.assertEqual(uni[0], ["", "Első bekezdés sora folytatás itt."])

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
