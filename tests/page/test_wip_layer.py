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


class WipRejectTest(WipCase):
    """Az elvetés a lemezre ír: saját repó, hogy a többi teszt lemezállapota ne változzon."""

    def test_reject_only_wip(self) -> None:
        """A WIP-blokk elvetése a HEAD-beli változatra áll vissza és ment; a commit-blokkon nincs elvetés."""
        self.open_app()
        self.assertEqual(self.page.locator(f"{SEL} .cm-deletedChunk .cm-reject").count(), 0)
        block = self.page.locator(f"{SEL} .cm-wipDeleted", has_text="s35 = 35")
        block.locator(".cm-reject").click()
        self.page.wait_for_timeout(1500)
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


class WipSplitTest(WipCase):
    """Egymás mellett (széles panel) is csukott a változatlan rész: csak a WIP-eltérést tartalmazó rés nyílik ki,
    a két oldalon együtt."""
    WIDTH = 1400

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

    def test_selection_above_lines(self) -> None:
        self.open_app()
        z = self.page.evaluate(f"getComputedStyle(document.querySelector('{SEL} .cm-selectionLayer')).zIndex")
        self.assertEqual(z, "1")


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
