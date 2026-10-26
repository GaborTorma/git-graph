"""A diff (a `.md` renderelt és a kódfájl nyers diffje): a csak beszúrt vagy csak törölt szavú
sornál egy változat látszik."""
from __future__ import annotations

import unittest
from contextlib import contextmanager
from pathlib import Path

from harness import PageTestCase, commit_versions

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
OLD_SHORT = "- **Kivétel**: rule vagy skill szövege (`RULE.md`,\n  command), és bármi egy plugin repóban.\n  Ezt a Fejlesztő átolvassa.\n"
NEW_SHORT = "- **Kivétel**: rule vagy skill szövege (`RULE.md`,\n  command). Ezt a Fejlesztő átolvassa.\n"
OLD_CODEWRAP = ("Bevezető.\n\n```\nfix(auth): keep users signed in\n\nA lejárt token után kiléptette,\n"
                "pedig a refresh még érvényes.\n```\n\nKöztes egy.\n\nKöztes kettő.\n\nRégi zárás.\n")
NEW_CODEWRAP = ("Bevezető.\n\n```\nfix(auth): keep users signed in\n\nA lejárt token után kiléptette, "
                "pedig a refresh még érvényes.\n```\n\nKöztes egy.\n\nKöztes kettő.\n\nÚj zárás.\n")
TABLE_ROWS = [f"| s{i} | sor {i} szövege |" for i in range(10)]
OLD_TABLE = "| Név | Mi |\n| --- | --- |\n" + "\n".join(TABLE_ROWS) + "\n"
NEW_TABLE = ("| Név | Mi |\n| --- | --- |\n"
             + "\n".join([*TABLE_ROWS[:2], "| s2 | sor |", "| s3 | másik |", *TABLE_ROWS[4:8], "| új | új sor, jóval hosszabb szöveggel, ami egy keskeny oszlopban több sorba is törik, mert a cella szélessége a panel felénél is kisebb, így a magassága nagyobb a helyőrzőénél |", *TABLE_ROWS[8:]]) + "\n")
OLD_PY = "x = hivas(a)\ny = 1\nz = masik(a, b, c)\nw = 2\nv = csere(a)\n"
NEW_PY = "x = hivas(a, b)\ny = 1\nz = masik(a)\nw = 2\nv = mas(a)\n"


# lista: a régi két elem közé hosszú új elem (al-elemekkel) kerül — a bekezdésként nem párosodik
OLD_LIST = (
    "- **`## STOP`** — hiba: ha egy sora teljesül, mutasd, amit a nyíl után ír, és **állj meg**.\n"
    "- **`## SKIP`** — nincs dolga, nem hiba: ha egy sora teljesül, **állj meg**; önállóan futva\n"
    "  mutasd, amit a nyíl után ír, láncban nincs válasza. A `## STOP` után áll, és utána is\n"
    "  értékelődik. Menet közben kiderülő kihagyás: `→ SKIP` (a szöveg, ha van, utána).\n"
    "- **Felsorolásban** az első illeszkedő sor dönt.\n")
NEW_LIST = (
    "- **`## STOP`** — hiba: ha egy sora teljesül, mutasd, amit a nyíl után ír, és **STOP**: a futás véget ér.\n"
    "- **`## ASK`** — hiányzó előfeltétel, a *Fejlesztő* dönt: ha egy sora teljesül, kérdezz\n"
    "  `AskUserQuestion`-nel (a nyíl utáni helyzet a kérdés, az alatta álló számozott sorok az\n"
    "  opciók, az első az ajánlott), és a válasz szerint folytasd. A teljesülő sorok egy hívásban,\n"
    "  soronként egy kérdés; ha több sor ugyanazt az előző lépést ajánlja, csak az első kérdez. A\n"
    "  `## STOP` után áll, a `## SKIP` előtt: az előző lépés új munkát hozhat.\n"
    "  - **Opció**: egy előző lépés commandja — lefut, utána a command folytatódik; „<valami>\n"
    "    nélküle” — továbbmegy; `STOP` — mint a `## STOP`. Az utolsó opció mindig `STOP`.\n"
    "  - **Előző lépés után** a konstansok elavultak: amire a további feltételek épülnek, annak a\n"
    "    parancsát futtasd újra.\n"
    "  - **Ajánlott út egyszer**: ha a *Fejlesztő* az ajánlott opcióval egy előző lépést hívat, a\n"
    "    hívott lépés ASK-jai ugyanebben a futásban kérdés nélkül az ajánlottal mennek — de csak\n"
    "    azok a sorok, amelyek ajánlott opciója is egy előző lépés; a „nélküle” vagy `STOP`\n"
    "    ajánlású sor ilyenkor is kérdez.\n"
    "  - **Előre jóváhagyva**: ha a hívó ezt írja (gomb, command, amelynek a hívása maga a\n"
    "    jóváhagyás), az ASK-ok ugyanígy mennek.\n"
    "  - Menet közben kiderülő kérdés: `→ ASK` (a helyzet és az opciók utána).\n"
    "- **`## SKIP`** — nincs dolga, nem hiba: ha egy sora teljesül, **STOP**; önállóan futva\n"
    "  mutasd, amit a nyíl után ír, láncban nincs válasza. A `## STOP` és a `## ASK` után áll,\n"
    "  és utánuk is értékelődik. Menet közben kiderülő kihagyás: `→ SKIP` (a szöveg, ha van, utána).\n"
    "- **Felsorolásban** az első illeszkedő sor dönt.\n")
# a lista végi elem al-elemmé válik: a párja a felső szintű régi elem
OLD_NEST = ("- **Hova**:\n  - Egy.\n- **Projektfüggetlen tudás** (más repóban is érvényes) nem memória, hanem rule vagy skill\n"
            "  (→ `/learn:capture`).\n")
OLD_ICON = ("- 🟣 · A-1 · **Alfa** régi\n  - 🌱 első al\n- 🟣 · B-2 · **Béta** régi\n  - ⚙️ második al\n\n"
            "Vegyes lista:\n\n- 🟣 vegyes régi\n- sima régi\n")
NEW_ICON = OLD_ICON.replace("régi", "új")
NEW_NEST = "- **Hova**:\n  - Egy.\n  - **Rule vagy skill** — ami más repóban is érvényes, `/learn:capture`-rel.\n"

FILES = {
    "doksi.md": (OLD, NEW), "kod.py": (OLD_PY, NEW_PY), "rend.md": (OLD_REORDER, NEW_REORDER),
    "tabla.md": (OLD_TABLE, NEW_TABLE), "kodtord.md": (OLD_CODEWRAP, NEW_CODEWRAP), "rovid.md": (OLD_SHORT, NEW_SHORT),
    "ujratord.md": (OLD_REWRAP, NEW_REWRAP), "jog.json": (OLD_JSON, NEW_JSON), "tordel.md": (OLD_WRAP, NEW_WRAP),
    "kihagy.md": (OLD_GAP, NEW_GAP), "utolso.md": (OLD_LAST, NEW_LAST), "bekezdes.md": (OLD_PARA, NEW_PARA),
    "lista.md": (OLD_LIST, NEW_LIST), "szint.md": (OLD_NEST, NEW_NEST),
    "ikon.md": (OLD_ICON, NEW_ICON),
}

# JS-részletek a lap elemeinek kiolvasásához: `e` osztálya a `base` nélkül, a kiemelt szövegei
CLS = "e.className.replace(/{}/g, '').trim()"
MARKS = "[...e.querySelectorAll('mark')].map(m => m.textContent)"
LINE = f"e => [{CLS.format('diff-line|mono')}, e.querySelector('.tx').textContent, {MARKS}]"   # nyers sor


class MdDiffTest(PageTestCase):
    SUBJECT = "doksi"

    @classmethod
    def prepare(cls, repo: Path) -> None:
        commit_versions(repo, FILES, cls.SUBJECT)

    @contextmanager
    def raw_view(self):
        """A markdown nyers diffje; a végén vissza (a lap megjegyzi), hiba esetén is."""
        self.page.locator("[data-md-mode]").first.click()
        try:
            yield
        finally:
            self.page.locator("[data-md-mode]").first.click()

    def test_one_sided_paragraph(self) -> None:
        self.open_file("doksi.md")
        self.page.wait_for_selector(".md-doc")
        blocks = self.page.locator(".diff-uni .md-blk").evaluate_all(
            f"bs => bs.map(e => [{CLS.format('md-blk')}, e.textContent, {MARKS}])")
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
            f"ls => ls.map(e => [{CLS.format('md-cl')}, e.textContent, {MARKS}])")
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
            f"rs => rs.map(r => [...r.children].map(c => {{ const e = c.querySelector('.md-blk');"
            f" return e ? {CLS.format('md-blk')} : '-'; }}))")
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
        heights = lambda: self.page.locator(".diff-split .md-row").first.evaluate(   # noqa: E731
            "r => [...r.children].map(c => [...c.querySelectorAll('tr')].map(t => t.getBoundingClientRect().height))")
        a, b = heights()           # a párban álló sorok egyforma magasak (a jobb oldali új sor helyőrzője is)
        self.assertEqual(a, b)
        self.resize(1100)          # keskenyebben más a tördelés: újra egyforma
        a, b = heights()
        self.assertEqual(a, b)
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
        blk = f"e => e ? [{CLS.format('md-blk')}, e.textContent, {MARKS}] : null"
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

    def test_md_new_list_item_in_place(self) -> None:
        """Két párosodott listaelem közé szúrt új elem a helyén marad, nem a lista végére csúszik."""
        self.open_file("lista.md")
        self.page.wait_for_selector(".md-doc")
        blocks = self.page.locator(".diff-uni .md-blk").evaluate_all(
            f"bs => bs.map(e => [{CLS.format('md-blk')}, e.textContent.slice(1, 12)])")
        self.assertEqual(blocks, [
            ["del", "## STOP — h"], ["add", "## STOP — h"],
            ["add", "## ASK — hi"], ["add", "Opció: egy "], ["add", "Előző lépés"],
            ["add", "Ajánlott út"], ["add", "Előre jóváh"], ["add", "Menet közbe"],
            ["del", "## SKIP — n"], ["add", "## SKIP — n"],
            ["", "Felsorolásb"],
        ])

    def test_md_list_item_keeps_level(self) -> None:
        """Az al-elemmé vált listaelem a saját szintjén látszik, nem a felső szintű párja blokkjában."""
        self.open_file("szint.md")
        self.page.wait_for_selector(".md-doc")
        blocks = self.page.locator(".diff-uni .md-blk").evaluate_all(
            f"bs => bs.map(e => [{CLS.format('md-blk')}, e.textContent.slice(1, 12),"
            " e.querySelector('.md-li')?.style.getPropertyValue('--md-ind')])")
        self.assertEqual(blocks[-2:], [["del", "Projektfügg", "0"], ["add", "Rule vagy s", "2"]])

    def test_md_icon_bullets(self) -> None:
        """Ha a lista egy szintjén minden elem ikonnal kezdődik, a felsorolásjel az ikon; ha nem mind,
        marad a pont. Az ikonos alszint közelebb van a szülőjéhez, mint a következő főelemhez."""
        self.open_file("ikon.md")
        self.page.wait_for_selector(".md-doc")
        items = self.page.locator(".diff-uni .md-li").evaluate_all(
            "ls => ls.map(e => [e.querySelector('.md-mk').textContent, e.lastElementChild.textContent])")
        self.assertEqual(items, [
            ["🟣", "· A-1 · Alfa régi"], ["🟣", "· A-1 · Alfa új"], ["🌱", "első al"],
            ["🟣", "· B-2 · Béta régi"], ["🟣", "· B-2 · Béta új"], ["⚙️", "második al"],
            ["•", "🟣 vegyes régi"], ["•", "🟣 vegyes új"], ["•", "sima régi"], ["•", "sima új"],
        ])
        tops = self.page.locator(".diff-uni .md-li").evaluate_all(
            "ls => ls.slice(1, 4).map(e => [e.getBoundingClientRect().top, e.getBoundingClientRect().bottom])")
        to_sub, to_next = tops[1][0] - tops[0][1], tops[2][0] - tops[1][1]
        self.assertLess(to_sub, to_next)

    def test_raw_unpaired_side_by_side(self) -> None:
        """Nyers side-by-side: a két pár közti pár nélküli törölt és új sor egy sorban."""
        self.resize(1400)
        self.open_file("rend.md")
        with self.raw_view():
            self.page.wait_for_selector(".diff-split .split-row")
            rows = self.page.locator(".diff-split .split-row").evaluate_all(
                "rs => rs.map(r => [...r.querySelectorAll('.half')].map(h => h.querySelector('.tx')?.textContent ?? null))")
        self.assertIn(["Régi egy szöveg.", "Új első tartalom."], rows)
        self.assertIn(["Régi kettő szöveg.", "Új második tartalom."], rows)

    def test_md_table_last_row(self) -> None:
        """A táblázat utolsó sorának új változata a régi mellé kerül, akkor is, ha utána egy bekezdés kimaradt."""
        self.resize(1400)
        self.open_file("utolso.md")
        self.page.wait_for_selector(".diff-split .md-row")
        rows = self.page.locator(".diff-split .md-row").evaluate_all(
            "rs => rs.map(r => [...r.children].map(c => [...c.querySelectorAll('tr, .md-blk')]"
            f".map(e => e.tagName === 'TR' ? [e.cells[0].tagName, e.cells[0].textContent.trim(), e.className]"
            f" : ['P', e.textContent.trim(), {CLS.format('md-blk')}])))")
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
        with self.raw_view():
            self.page.wait_for_selector(".diff-split .split-row")
            rows = self.page.locator(".diff-split .split-row").evaluate_all(
                "rs => rs.map(r => [...r.querySelectorAll('.half')].map(e => e.querySelector('.tx')"
                f" ? [{CLS.format('half')}, e.querySelector('.tx').textContent, {MARKS}.join('|')] : null))")
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
            f"ls => ls.filter(e => /add|del/.test(e.className)).map({LINE})")
        self.assertEqual(lines, [
            ["add only", '  "Bash(git reset --hard*)",', [","]],
            ["add", '  "Bash(git mv *)",', []],
            ["add", '  "Bash(git rm *)"', []],
        ])

    def test_raw_rewrap_unchanged(self) -> None:
        """Tiszta újratördelés a nyers diffben: változatlan sorként, jel és szín nélkül, mindkét nézetben."""
        self.resize(1400)
        self.open_file("ujratord.md")
        with self.raw_view():
            self.page.wait_for_selector(".diff-split .split-row")
            half = (f"e => e.querySelector('.tx') ? [{CLS.format('half')}, e.querySelector('.sg').textContent,"
                    " e.querySelector('.tx').textContent] : null")
            rows = self.page.locator(".diff-split .split-row").evaluate_all(
                f"rs => rs.map(r => [...r.querySelectorAll('.half')].map({half}))")
            uni = self.page.locator(".diff-uni .diff-line").evaluate_all(f"ls => ls.map({LINE})")
        self.assertEqual(rows[:2], [
            [["", "", "Első bekezdés sora"], ["", "", "Első bekezdés sora folytatás itt."]],
            [["", "", "folytatás itt."], None],
        ])
        self.assertEqual(uni[0], ["", "Első bekezdés sora folytatás itt.", []])

    def test_raw_deletion_rewrapped_line(self) -> None:
        """Csak törlésnél a régi oldal szó nélkül változott (átkerült) sora változatlanként, jel nélkül."""
        self.open_file("rovid.md")
        with self.raw_view():
            self.page.wait_for_selector(".diff .diff-line")
            lines = self.page.locator(".diff .diff-line").evaluate_all(
                f"ls => ls.map(e => [{CLS.format('diff-line|mono')}, e.querySelector('.sg').textContent,"
                " e.querySelector('.tx').textContent.trim()])")
        self.assertEqual(lines[1:], [
            ["del only", "−", "command), és bármi egy plugin repóban."],
            ["", "", "Ezt a Fejlesztő átolvassa."],
        ])

    def test_md_rewrap_hidden(self) -> None:
        """A markdown-nézetben a csak újratördelt kódblokk nem változás: nem látszik, csak a valódi csere."""
        self.open_file("kodtord.md")
        for width, view in ((1400, ".diff-split"), (900, ".diff-uni")):
            self.resize(width)
            text = self.page.locator(f".diff {view}").inner_text()
            self.assertNotIn("kiléptette", text, view)
            self.assertIn("zárás", text, view)

    def test_one_sided_code_line(self) -> None:
        self.open_file("kod.py")
        self.page.wait_for_selector(".diff-uni .diff-line")
        lines = self.page.locator(".diff-uni .diff-line").evaluate_all(f"ls => ls.map({LINE})")
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
            f"rs => rs.map(r => [...r.querySelectorAll('.half')].map(e => {CLS.format('half')}"
            " + ':' + e.querySelector('.sg').textContent))")
        self.assertEqual(rows, [
            [":", "add only:+"],
            [":", ":"],
            ["del only:−", ":"],
            [":", ":"],
            ["del:−", "add:+"],
        ])


if __name__ == "__main__":
    unittest.main()
