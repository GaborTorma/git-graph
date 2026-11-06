"""A saját worktree HEAD-commitjának kóddiffje a lemez szövegével (#56): a commit változása zöld / piros, a
WIP eltérései (HEAD → lemez) kék / narancs rétegben; elvetés csak a WIP-blokkon, a számai a fejlécen, a
változatlan rés mindkét diffhez igazodik."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, git_in

BASE = [f"s{i} = {i}" for i in range(1, 101)]


def text(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def changed(lines: list[str], **at: str) -> list[str]:
    return [at.get(f"s{i}", line) for i, line in enumerate(lines, 1)]


HEAD = changed(BASE, s10="s10 = 'commit'", s60="s60 = 'commit'")
DISK = changed(HEAD, s35="s35 = 'wip'", s60="s60 = 'wip'")
DISK = DISK[:80] + ["uj = 1"] + DISK[80:]          # egy új sor a 81. helyen
INDENTED = "class A:\n    def f(self):\n        self.a = 1\n        self.b = 2\n        self.c = 3\n"
VIEW = "CM.EditorView.findFromDOM(document.querySelector(sel + ' .cm-content').closest('.cm-editor'))"
SEL = '.details .file[data-path="app.py"] + .diff'


class WipCase(PageTestCase):
    """A fixture: a HEAD-commit az app.py 10. és 60. sorát módosítja, a lemezen a 35. és a 60. sor is, és egy új sor."""
    WIDTH, HEIGHT = 900, 900

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "app.py").write_text(text(BASE), encoding="utf-8")
        (repo / "masik.py").write_text(text(BASE[:20]), encoding="utf-8")    # a HEAD nem módosítja
        git_in(repo, "add", "app.py", "masik.py")
        git_in(repo, "commit", "-qm", "wip: alap")
        (repo / "app.py").write_text(text(HEAD), encoding="utf-8")
        (repo / "beh.py").write_text(INDENTED, encoding="utf-8")       # behúzott sorok, a lemezen változatlan
        git_in(repo, "add", "beh.py")
        git_in(repo, "commit", "-qam", "wip: a commit")
        (repo / "app.py").write_text(text(DISK), encoding="utf-8")
        (repo / "masik.py").write_text(text(changed(BASE[:20], s5="s5 = 'lemez'")), encoding="utf-8")

    def open_app(self, subject: str = "wip: a commit", name: str = "app.py") -> None:
        self.page.locator("#rows .row", has_text=subject).click()
        self.settle()
        self.page.locator(f'.details .file[data-path="{name}"]').click()
        self.page.wait_for_selector(f'.details .file[data-path="{name}"] + .diff .cm-editor')
        self.settle()

    def line(self, txt: str):
        return self.page.locator(f"{SEL} .cm-line", has_text=txt)




class WipCrlfTest(PageTestCase):
    """CRLF sorvégű fájl a HEAD-commitban: a sorvég nem WIP-eltérés."""
    WIDTH, HEIGHT = 900, 900

    @classmethod
    def prepare(cls, repo: Path) -> None:
        crlf = lambda lines: "\r\n".join(lines) + "\r\n"     # noqa: E731
        (repo / "win.py").write_bytes(crlf(BASE[:30]).encode())
        git_in(repo, "add", "win.py")
        git_in(repo, "commit", "-qm", "crlf: alap")
        (repo / "win.py").write_bytes(crlf(changed(BASE[:30], s5="s5 = 'commit'")).encode())
        git_in(repo, "commit", "-qam", "crlf: a commit")
        (repo / "win.py").write_bytes(crlf(changed(BASE[:30], s5="s5 = 'commit'", s20="s20 = 'wip'")).encode())

    def test_crlf_only_changed_line(self) -> None:
        """Csak a lemezen átírt sor kék, egy narancs blokkal; a többi sor nem WIP-eltérés."""
        self.page.locator("#rows .row", has_text="crlf: a commit").click()
        self.settle()
        self.page.locator('.details .file[data-path="win.py"]').click()
        sel = '.details .file[data-path="win.py"] + .diff'
        self.page.wait_for_selector(f"{sel} .cm-editor")
        self.settle()
        self.assertEqual(self.page.locator(f"{sel} .cm-wipLine").all_inner_texts(), ["s20 = 'wip'"])
        self.assertEqual([t.strip() for t in self.page.locator(f"{sel} .cm-wipDeleted").all_inner_texts()], ["s20 = 20"])

class WipLayerTest(WipCase):
    def test_layers(self) -> None:
        """A commit sora zöld, a WIP sorai kékek, a HEAD-beli változatuk narancs blokk; átfedésnél a WIP nyer."""
        self.open_app()
        commit = self.line("s10 = 'commit'").get_attribute("class")
        self.assertIn("cm-changedLine", commit)
        self.assertNotIn("cm-wipLine", commit)
        for wip in ("s35 = 'wip'", "s60 = 'wip'", "uj = 1"):
            with self.subTest(wip):
                self.assertIn("cm-wipLine", self.line(wip).get_attribute("class"))
        self.assertNotIn("cm-wipLine", self.line("s36 = 36").get_attribute("class"))   # csak a változott sor
        old = [t.strip() for t in self.page.locator(f"{SEL} .cm-wipDeleted").all_inner_texts()]
        self.assertIn("s35 = 35", old)                     # egy sor, üres sor nélkül
        self.assertIn("s60 = 'commit'", old)
        # a csak a WIP által változott sornak nincs piros (commit) blokkja; az átfedésnek van (a szülőé)
        red = [t.strip() for t in self.page.locator(f"{SEL} .cm-deletedChunk").all_inner_texts()]
        self.assertEqual(red, ["s10 = 10", "s60 = 60"])

    def test_typing_marks_wip(self) -> None:
        """Szerkesztés közben a változatlan sorba írt szó a sort kékre váltja."""
        self.open_app()
        self.page.evaluate(f"""sel => {{ const v = {VIEW}; const l = v.state.doc.line(12);
          v.dispatch({{ changes: {{ from: l.from, insert: 'szo ' }} }}); }}""", SEL)
        self.assertIn("cm-wipLine", self.line("szo s12 = 12").get_attribute("class"))
        self.page.wait_for_timeout(400)                    # a merge alapja is követi: nincs piros blokk a sorra
        red = [t.strip() for t in self.page.locator(f"{SEL} .cm-deletedChunk").all_inner_texts()]
        self.assertNotIn("s12 = 12", red)

    def test_typing_no_commit_colors(self) -> None:
        """Gépelés közben (a merge alapjának késleltetett frissítése előtt) sincs piros / zöld a gépelt soron."""
        self.open_app()
        state = self.page.evaluate(f"""async sel => {{ const v = {VIEW}; const l = v.state.doc.line(12);
          v.dispatch({{ changes: {{ from: l.from, insert: 'szo ' }} }});
          await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
          const line = [...document.querySelectorAll(sel + ' .cm-line')].find(x => x.textContent === 'szo s12 = 12');
          return [line.className, [...document.querySelectorAll(sel + ' .cm-deletedChunk')].map(x => x.textContent.trim())]; }}""", SEL)
        self.assertIn("cm-wipLine", state[0])
        self.assertNotIn("cm-changedLine", state[0])
        self.assertNotIn("s12 = 12", state[1])

    def test_enter_adds_one_line(self) -> None:
        """Enter egy behúzott sor végén: csak az új üres sor kék, a következő sor nem lesz narancs és kék is."""
        self.open_app(name="beh.py")
        sel = '.details .file[data-path="beh.py"] + .diff'
        self.page.evaluate(f"""sel => {{ const v = {VIEW}; const l = v.state.doc.line(3);
          v.dispatch({{ changes: {{ from: l.to, insert: '\\n        ' }} }}); }}""", sel)
        self.page.wait_for_timeout(300)
        self.assertEqual(self.page.locator(f"{sel} .cm-wipDeleted").all_inner_texts(), [""])   # csak az elvetés gombja
        blue = [t for t in self.page.locator(f"{sel} .cm-wipLine").all_inner_texts()]
        self.assertEqual([t.strip() for t in blue], [""])

    def test_older_commit_unchanged_since(self) -> None:
        """Régebbi commitban, ha a fájl azóta nem változott (masik.py), a lemez szövege kék réteggel, és
        szerkeszthető."""
        self.open_app("wip: alap", "masik.py")
        sel = '.details .file[data-path="masik.py"] + .diff'
        line = self.page.locator(f"{sel} .cm-line", has_text="s5 = 'lemez'")
        self.assertIn("cm-wipLine", line.get_attribute("class"))
        self.assertIn("s5 = 5", self.page.locator(f"{sel} .cm-wipDeleted").first.inner_text())
        line.dblclick()
        self.page.wait_for_function(f"document.querySelector('{sel} .cm-content').contentEditable === 'true'")

    def test_older_commit_no_layer(self) -> None:
        """Régebbi commitban, ha a fájl azóta változott (app.py), nincs WIP-réteg."""
        self.open_app("wip: alap")
        self.assertEqual(self.page.locator(f"{SEL} .cm-wipLine, {SEL} .cm-wipDeleted").count(), 0)

    def test_cursor_shows_editable(self) -> None:
        """A nem szerkeszthető kódnézeten nyíl a kurzor, a szerkeszthetőn I-gerenda."""
        cursor = f"getComputedStyle(document.querySelector('{SEL} .cm-content')).cursor"
        self.open_app("wip: alap")
        self.assertEqual(self.page.evaluate(cursor), "default")
        self.page.locator('.details .file[data-path="app.py"]').click()       # becsukva
        self.open_app()
        self.assertEqual(self.page.evaluate(cursor), "text")

    def test_header_counts(self) -> None:
        """A fejlécen a commit +2 −2 mellett a WIP +3 −2, kék és narancs színnel."""
        self.page.locator("#rows .row", has_text="wip: a commit").click()
        self.settle()
        file = self.page.locator('.details .file[data-path="app.py"]')
        self.assertEqual(file.locator(".churn .wa").inner_text(), "+3")
        self.assertEqual(file.locator(".churn .wd").inner_text(), "−2")

    def test_gap_split_by_wip(self) -> None:
        """A commit két változása közti résben a WIP-eltérés (35. sor) látszik, a rés két részre oszlik."""
        self.open_app()
        self.assertTrue(self.line("s35 = 'wip'").is_visible())
        self.assertTrue(self.line("s32 = 32").is_visible())
        self.assertFalse(self.line("s20 = 20").is_visible())
        self.assertFalse(self.line("s50 = 50").is_visible())


class WipSelectionTest(WipCase):
    def test_selection_over_block(self) -> None:
        """A narancs blokkon átnyúló kijelölés a blokk alatti sort a saját magasságában jelöli, nem a blokk tetejétől."""
        # Adott a 34. sor közepétől a 35. (a narancs blokk alatti, kék) sor végéig tartó kijelölés
        self.open_app()
        self.page.evaluate(f"""sel => {{ const v = {VIEW}; v.focus();
          v.dispatch({{ selection: {{ anchor: v.state.doc.line(34).from + 3, head: v.state.doc.line(35).to }} }}); }}""", SEL)
        self.page.wait_for_timeout(100)
        # Akkor a narancs blokkra eső kijelölés nem látszik: a blokk van felül, a 35. sor szövegén a kijelölés
        block = self.page.locator(f"{SEL} .cm-wipDeleted", has_text="s35 = 35").bounding_box()
        line = self.line("s35 = 'wip'").bounding_box()
        top = self.page.evaluate("""([x1, y1, x2, y2]) => {
          document.querySelectorAll('.cm-selectionLayer').forEach(l => { l.style.pointerEvents = 'auto'; });
          const at = (x, y) => document.elementFromPoint(x, y).closest('.cm-wipDeleted, .cm-selectionBackground')?.className;
          return [at(x1, y1), at(x2, y2)]; }""", [block["x"] + 20, block["y"] + block["height"] / 2, line["x"] + 20, line["y"] + line["height"] / 2])
        self.assertEqual(top, ["cm-wipDeleted", "cm-selectionBackground"])


class WipEmptyLineTest(PageTestCase):
    """A HEAD-commit üres sorát a lemezen szöveg váltja."""
    WIDTH, HEIGHT = 900, 600

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "e.py").write_text("a = 1\n\nb = 2\n", encoding="utf-8")
        git_in(repo, "add", "e.py")
        git_in(repo, "commit", "-qm", "ures: a commit")
        (repo / "e.py").write_text("a = 1\nTESZT\nb = 2\n", encoding="utf-8")

    def open_e(self, row: str) -> str:
        self.page.locator(row).click()
        self.settle()
        self.page.locator('.details .file[data-path="e.py"]').click()
        sel = '.details .file[data-path="e.py"] + .diff'
        self.page.wait_for_selector(f"{sel} .cm-editor")
        self.settle()
        return sel

    def covered(self, sel: str, block: str) -> list:
        """Az 1. sor közepétől a 2. sor végéig kijelölve: mi van felül a blokk és a 2. sor közepén."""
        self.page.evaluate(f"""sel => {{ const v = {VIEW}; v.focus();
          v.dispatch({{ selection: {{ anchor: v.state.doc.line(1).from + 2, head: v.state.doc.line(2).to }} }}); }}""", sel)
        self.page.wait_for_timeout(100)
        b = self.page.locator(f"{sel} {block}").bounding_box()
        line = self.page.locator(f"{sel} .cm-line", has_text="TESZT").bounding_box()
        return self.page.evaluate("""([block, x1, y1, x2, y2]) => {
          document.querySelectorAll('.cm-selectionLayer').forEach(l => { l.style.pointerEvents = 'auto'; });
          const at = (x, y) => document.elementFromPoint(x, y).closest(block + ', .cm-selectionBackground')?.className;
          return [at(x1, y1), at(x2, y2)]; }""", [block, b["x"] + 20, b["y"] + b["height"] / 2, line["x"] + 20, line["y"] + line["height"] / 2])

    def test_empty_old_line_shown(self) -> None:
        """Az üres régi sor a narancs blokkban üres sorként látszik; a rá eső kijelölést a blokk takarja."""
        sel = self.open_e('#rows .row:has-text("ures: a commit")')
        self.assertIn("cm-wipLine", self.page.locator(f"{sel} .cm-line", has_text="TESZT").get_attribute("class"))
        self.assertEqual(self.page.locator(f"{sel} .cm-wipDeleted > div").count(), 1)
        self.assertGreater(self.page.locator(f"{sel} .cm-wipDeleted").bounding_box()["height"], 15)
        self.assertEqual(self.covered(sel, ".cm-wipDeleted"), ["cm-wipDeleted", "cm-selectionBackground"])

    def test_wip_row_empty_line(self) -> None:
        """A WIP soron a törölt üres sor is látszik; a rá eső kijelölést a törölt blokk takarja."""
        sel = self.open_e(".row.uncommitted")
        self.assertEqual([e.is_visible() for e in self.page.locator(f"{sel} .cm-deletedChunk .cm-deletedLine").all()], [True])
        self.assertEqual(self.covered(sel, ".cm-deletedChunk"), ["cm-deletedChunk", "cm-selectionBackground"])


class WipSameTextTest(WipEmptyLineTest):
    """A lemezre a nézet nem mentett szövegével azonos tartalom kerül (saját repó: ír)."""

    def test_same_text_no_conflict(self) -> None:
        """Ha a lemez szövege megegyezik a nem mentett szöveggel, az nem ütközés: nincs ütközés-doboz."""
        sel = self.open_e('#rows .row:has-text("ures: a commit")')
        self.page.locator(f"{sel} .cm-line", has_text="TESZT").dblclick()
        self.page.keyboard.press("End")
        self.page.keyboard.type("x")
        (self.repo / "e.py").write_text("a = 1\nTESZTx\nb = 2\n", encoding="utf-8")
        self.poke()
        self.page.wait_for_timeout(1500)
        self.assertEqual(self.page.locator(f"{sel} .cm-conflict").count(), 0)
        self.assertEqual((self.repo / "e.py").read_text(encoding="utf-8"), "a = 1\nTESZTx\nb = 2\n")

    test_empty_old_line_shown = test_wip_row_empty_line = None


class WipRejectTest(WipCase):
    """Az elvetés a lemezre ír: saját repó, hogy a többi teszt lemezállapota ne változzon."""

    def test_reject_only_wip(self) -> None:
        """A WIP-blokk elvetése a HEAD-beli változatra áll vissza és ment; a commit-blokkon nincs elvetés."""
        self.open_app()
        self.assertEqual(self.page.locator(f"{SEL} .cm-deletedChunk .cm-reject").count(), 0)
        block = self.page.locator(f"{SEL} .cm-wipDeleted", has_text="s35 = 35")
        block.locator(".cm-reject").click()
        self.until(lambda: (self.repo / "app.py").read_text(encoding="utf-8").splitlines()[34:36] == ["s35 = 35", "s36 = 36"], "az elvetés a lemezen")
        disk = (self.repo / "app.py").read_text(encoding="utf-8").splitlines()
        self.assertEqual(disk[34:36], ["s35 = 35", "s36 = 36"])      # a következő sor ép marad
        self.assertEqual(disk[59], "s60 = 'wip'")



class WipReopenTest(WipCase):
    """A lemez változása után visszanyitott HEAD-commit fájl a friss lemezt mutatja (saját repó: ír)."""

    def test_reopen_after_disk_change(self) -> None:
        """A fájl becsukva, a lemezen új sor; a WIP sor frissülése után újra lenyitva az új sor kék, és látszik."""
        self.open_app()
        self.page.locator('.details .file[data-path="app.py"]').click()     # becsukva
        self.settle()
        lines = (self.repo / "app.py").read_text(encoding="utf-8").splitlines()
        lines[19] = "s20 = 'kivul'"
        (self.repo / "app.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.poke()
        self.settle()
        self.page.locator('.details .file[data-path="app.py"]').click()     # újra lenyitva
        self.page.wait_for_selector(f"{SEL} .cm-editor")
        self.settle()
        line = self.line("s20 = 'kivul'")
        self.assertTrue(line.is_visible())
        self.assertIn("cm-wipLine", line.get_attribute("class"))


class WipSwitchTest(WipCase):
    """Teljes képernyőn a HEAD-commit és a WIP sor közti váltás a nyitott fájlt helyben frissíti (saját repó: ír)."""
    WIDTH, HEIGHT = 900, 760

    def test_switch_keeps_view(self) -> None:
        """A nézet nem töltődik újra: a nem mentett szöveg, a szerkesztő mód és a kinyitott rés megmarad."""
        # Adott a HEAD-commit app.py-ja teljes képernyőn, szerkesztés közben, nem mentett szóval, kinyitott réssel
        self.open_app()
        self.page.locator('.details .file[data-path="app.py"] [data-full]').click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()
        box = ".fv .fv-box"
        self.page.locator(f"{box} .cm-collapsedLines").first.click()
        self.page.locator(f"{box} .cm-line", has_text="s37 = 37").dblclick()
        self.page.keyboard.press("Home")
        self.page.keyboard.type("szo ")
        self.page.evaluate("""() => { window.reloaded = false; document.querySelector('.fv .fv-box .cm-diff').dataset.mark = '1';
          new MutationObserver(ms => { if (document.querySelector('.fv .fv-box .loading')) window.reloaded = true; })
            .observe(document.querySelector('.fv .fv-box'), { childList: true, subtree: true }); }""")
        # Ha a Fejlesztő a WIP sorra vált
        self.page.locator(".fv-commits .fv-commit").first.click()
        self.page.wait_for_function("document.querySelector('.fv-commit.sel') === document.querySelector('.fv-commit')")
        self.settle()
        # Akkor ugyanaz a nézet él tovább, a szöveg, a szerkesztés és a kinyitott rés marad
        self.assertFalse(self.page.evaluate("window.reloaded"))
        self.assertEqual(self.page.locator(f"{box} .cm-diff[data-mark]").count(), 1)
        self.assertTrue(self.page.locator(f"{box} .cm-line", has_text="szo s37 = 37").is_visible())
        self.assertTrue(self.page.locator(f"{box} .cm-line", has_text="s3 = 3").is_visible())
        self.assertEqual(self.page.locator(f"{box} .cm-diff.editing").count(), 1)
        # és a szerkesztés a WIP sor fájljába ment
        self.page.keyboard.type("x")
        self.until(lambda: 'szo xs37 = 37' in (self.repo / "app.py").read_text(encoding="utf-8"), "szo xs37 = 37 a lemezen")
        self.assertIn("szo xs37 = 37", (self.repo / "app.py").read_text(encoding="utf-8"))


class WipSwitchReadOnlyTest(WipCase):
    """Teljes képernyőn a szerkesztett HEAD-commitról egy régebbi (nem szerkeszthető) commitra váltva (saját repó: ír)."""
    WIDTH, HEIGHT = 900, 760

    def test_switch_saves_first(self) -> None:
        """A nézet helyben frissül; a szerkesztés véget ér, a nem mentett szöveg előbb a lemezre megy."""
        # Adott a HEAD-commit app.py-ja teljes képernyőn, szerkesztés közben, nem mentett szóval
        self.open_app()
        self.page.locator('.details .file[data-path="app.py"] [data-full]').click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()
        box = ".fv .fv-box"
        self.page.locator(f"{box} .cm-line", has_text="s37 = 37").dblclick()
        self.page.keyboard.press("Home")
        self.page.keyboard.type("szo ")
        self.page.evaluate("document.querySelector('.fv .fv-box .cm-diff').dataset.mark = '1'")
        # Ha a Fejlesztő a régebbi commitra vált
        self.page.locator(".fv-commit", has_text="wip: alap").click()
        self.page.wait_for_function("document.querySelector('.fv-commit.sel')?.textContent.includes('wip: alap')")
        self.settle()
        # Akkor ugyanaz a nézet a régebbi commit szövegével, szerkesztés nélkül; a szó a lemezen
        self.assertEqual(self.page.locator(f"{box} .cm-diff[data-mark]").count(), 1)
        self.assertEqual(self.page.locator(f"{box} .cm-diff.editing").count(), 0)
        self.assertEqual(self.page.locator(f"{box} .cm-line", has_text="szo s37").count(), 0)
        self.until(lambda: 'szo s37 = 37' in (self.repo / "app.py").read_text(encoding="utf-8"), "szo s37 = 37 a lemezen")
        self.assertIn("szo s37 = 37", (self.repo / "app.py").read_text(encoding="utf-8"))


class WipSplitTest(WipCase):
    """Egymás mellett (széles panel) is csukott a változatlan rész: csak a WIP-eltérést tartalmazó rés nyílik ki,
    a két oldalon együtt."""
    WIDTH = 1400

    def test_rests(self) -> None:
        """A nyitott nézet nyugalomban nem mér újra: a saját rés magassága egyezik a CodeMirror
        becslésével, különben a MergeView igazítása minden képkockában újrarajzolna (#63). A hurok
        nem minden betöltéskor alakult ki: három friss betöltés."""
        for _ in range(3):
            # Adott a WIP-réteges diff egymás mellett, a saját réseivel
            self.page.reload()
            self.page.wait_for_selector("#rows .row")
            self.open_app()
            self.assertGreater(self.page.locator(f"{SEL} .cm-merge-a .cm-collapsedLines").count(), 0)
            # Ha a lap megnyugodott, és fél másodpercig figyeljük
            changes = self.page.evaluate("""() => new Promise(done => {
              let n = 0;
              const obs = new MutationObserver(ms => { n += ms.length; });
              obs.observe(document.querySelector('.cm-mergeView'), { subtree: true, childList: true, attributes: true });
              setTimeout(() => { obs.disconnect(); done(n); }, 500);
            })""")
            # Akkor a nézetben semmi sem változik
            self.assertEqual(changes, 0)

    def test_split_gaps(self) -> None:
        self.open_app()
        self.assertEqual(self.page.locator(f"{SEL} .cm-mergeView .cm-editor").count(), 2)
        right = f"{SEL} .cm-merge-b .cm-line"
        self.assertTrue(self.page.locator(right, has_text="s35 = 'wip'").is_visible())
        self.assertFalse(self.page.locator(right, has_text="s5 = 5").is_visible())
        self.assertFalse(self.page.locator(right, has_text="s90 = 90").is_visible())
        # a két oldal egy magasságban: a 35. sor bal és jobb oldali változata egy vonalban
        left = self.page.locator(f"{SEL} .cm-merge-a .cm-line", has_text="s36 = 36").bounding_box()
        right = self.page.locator(f"{SEL} .cm-merge-b .cm-line", has_text="s36 = 36").bounding_box()
        self.assertLessEqual(abs(left["y"] - right["y"]), 2)

    def test_left_is_parent(self) -> None:
        """A bal oldal a szülő: a WIP sora nincs rajta, a WIP által törölt sora narancs, szókiemeléssel és sávjellel."""
        self.open_app()
        left = f"{SEL} .cm-merge-a"
        self.assertEqual(self.page.locator(f"{left} .cm-line", has_text="s35 = 'wip'").count(), 0)
        self.assertEqual(self.page.locator(f"{left} .cm-line", has_text="uj = 1").count(), 0)
        old = self.page.locator(f"{left} .cm-line", has_text="s35 = 35")
        self.assertIn("cm-wipDelLine", old.get_attribute("class"))
        self.assertEqual(old.locator(".cm-wipDelText").inner_text(), "35")
        self.assertGreater(self.page.locator(f"{left} .cm-changeGutter .cm-wipDelGutter").count(), 0)
        # a jobb oldalon a narancs blokk csak a szülőben nem meglévő (a commit hozta) sor; az üres a tiszta
        # hozzáadás elvetése
        blocks = [t.strip() for t in self.page.locator(f"{SEL} .cm-merge-b .cm-wipDeleted").all_inner_texts() if t.strip()]
        self.assertEqual(blocks, ["s60 = 'commit'"])
        # a 36. sor a két oldalon egy vonalban (a térközök a betű betöltése után is igazodnak)
        self.page.wait_for_function("""sel => { const y = side => [...document.querySelectorAll(sel + ' .cm-merge-' + side + ' .cm-line')]
          .find(l => l.textContent === 's36 = 36').getBoundingClientRect().y;
          return Math.abs(y('a') - y('b')) <= 2; }""", arg=SEL, timeout=3000)

    def test_reject_from_left(self) -> None:
        """A bal oldal narancs során az elvetés a HEAD-beli változatra állítja vissza a sort."""
        self.open_app()
        self.page.locator(f"{SEL} .cm-merge-a .cm-wipDelLine", has_text="s35 = 35").locator(".cm-reject").click()
        self.page.wait_for_timeout(300)
        self.assertEqual(self.page.locator(f"{SEL} .cm-merge-b .cm-line", has_text="s35 = 'wip'").count(), 0)
        self.assertEqual(self.page.locator(f"{SEL} .cm-merge-a .cm-wipDelLine", has_text="s35 = 35").count(), 0)


class WipMarksTest(WipCase):
    """Egymás alatt a kék és a narancs sor szókiemelést és sávjelet kap; a kijelölés a színezett sor fölött látszik."""

    def test_marks(self) -> None:
        self.open_app()
        self.assertEqual(self.line("s35 = 'wip'").locator(".cm-wipText").inner_text(), "'wip'")
        marks = self.page.locator(f"{SEL} .cm-wipDeleted .cm-wipDelText").all_inner_texts()
        self.assertIn("35", marks)
        self.assertGreater(self.page.locator(f"{SEL} .cm-changeGutter .cm-wipAddGutter").count(), 0)
        self.assertGreater(self.page.locator(f"{SEL} .cm-changeGutter .cm-wipDelGutter").count(), 0)
        # a sávjel a saját, élénkebb árnyalata (nem a szám színe)
        bars = self.page.evaluate(f"""(() => {{ const c = s => getComputedStyle(document.querySelector('{SEL} ' + s)).backgroundColor;
          const probe = v => {{ const e = Object.assign(document.createElement('span'), {{ style: 'background: var(' + v + ')' }});
            document.body.append(e); const r = getComputedStyle(e).backgroundColor; e.remove(); return r; }};
          return [c('.cm-changeGutter .cm-wipAddGutter'), probe('--wip-add-bar'), c('.cm-changeGutter .cm-wipDelGutter'), probe('--wip-del-bar')]; }})()""")
        self.assertEqual(bars[0], bars[1])
        self.assertEqual(bars[2], bars[3])

    def test_selection_above_lines(self) -> None:
        self.open_app()
        z = self.page.evaluate(f"getComputedStyle(document.querySelector('{SEL} .cm-selectionLayer')).zIndex")
        self.assertEqual(z, "1")
        # a kijelölés az app highlight-árnyalata, világos témában 50%-kal
        self.page.evaluate(f"""sel => {{ const v = {VIEW}; const l = v.state.doc.line(36); v.focus();
          v.dispatch({{ selection: {{ anchor: l.from, head: l.to }} }}); }}""", SEL)
        self.page.wait_for_selector(f"{SEL} .cm-selectionBackground", state="attached")
        bg = self.page.evaluate(f"getComputedStyle(document.querySelector('{SEL} .cm-selectionBackground')).backgroundColor")
        self.assertEqual(bg, "rgba(250, 178, 25, 0.5)")


class WipToneTest(WipCase):
    """A WIP sor kék / narancs (a commit zöld / piros helyett); a fa a fájlok mellett a WIP számait is mutatja."""

    def test_wip_row_tone(self) -> None:
        self.page.locator(".row.uncommitted").first.click()
        self.settle()
        colors = self.page.evaluate("""(() => { const d = document.querySelector('.details');
          const c = s => getComputedStyle(d.querySelector(s)).color;
          const probe = Object.assign(document.createElement('span'), { style: 'color: var(--wip-add-fg)' });
          d.append(probe); const want = getComputedStyle(probe).color; probe.remove();
          return [d.classList.contains('wip-tone'), c('.files-head .a'), want]; })()""")
        self.assertTrue(colors[0])
        self.assertEqual(colors[1], colors[2])

    def test_wip_row_sum_tone(self) -> None:
        """A WIP sor végén a +/− szám kék / narancs, a commit során zöld / piros."""
        colors = self.page.evaluate("""(() => {
          const probe = v => { const e = Object.assign(document.createElement('span'), { style: `color: var(${v})` });
            document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; };
          const col = s => getComputedStyle(document.querySelector(s)).color;
          return [col('.row.uncommitted .sum .a'), probe('--wip-add-fg'), col('.row.uncommitted .sum .d'), probe('--wip-del-fg'),
                  col('#rows .row:not(.uncommitted) .sum .a'), probe('--add')]; })()""")
        self.assertEqual(colors[0], colors[1])
        self.assertEqual(colors[2], colors[3])
        self.assertEqual(colors[4], colors[5])

    def test_selected_stays_with_wip(self) -> None:
        """WIP sorral a kijelölt commitra kattintva a kijelölés marad."""
        self.open_app()
        self.page.locator('.details .file[data-path="app.py"]').locator("[data-full]").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.page.locator(".fv-commit.sel").click()
        self.page.wait_for_timeout(300)
        self.assertEqual(self.page.locator(".fv-commit.sel .subj").inner_text(), "wip: a commit")

    def test_tree_wip_counts(self) -> None:
        self.open_app()
        self.page.locator('.details .file[data-path="app.py"]').locator("[data-full]").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        row = self.page.locator('.fv-list .fv-file[data-path="app.py"]')
        self.assertEqual(row.locator(".churn .a").inner_text(), "+2")
        self.assertEqual(row.locator(".churn .wa").inner_text(), "+3")
        self.assertEqual(row.locator(".churn .wd").inner_text(), "−2")
        # a fejlécben a fájl neve után ugyanezek
        head = self.page.locator(".fv-head .fv-path .churn")
        self.assertEqual([head.locator(c).inner_text() for c in (".a", ".d", ".wa", ".wd")], ["+2", "−2", "+3", "−2"])
        self.assertEqual(self.page.locator(".fv-path .fic").bounding_box()["width"], 20)

    def test_commit_list_wip_on_top(self) -> None:
        """A commitlistán a saját worktree WIP sora mindig felül, a rejtett commitok száma alatta."""
        self.page.locator(".row", has_text="wip: alap").first.click()
        self.settle()
        self.page.locator('.details .file[data-path="app.py"]').locator("[data-full]").click()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        first = self.page.locator(".fv-commits > div").first
        self.assertEqual(first.locator(".subj").inner_text(), "Nem commitolt változások")
        self.assertEqual(self.page.locator(".fv-commit.sel .subj").inner_text(), "wip: alap")


if __name__ == "__main__":
    unittest.main()
