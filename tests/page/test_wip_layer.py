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
VIEW = "CM.EditorView.findFromDOM(document.querySelector(sel + ' .cm-content').closest('.cm-editor'))"
SEL = '.details .file[data-path="app.py"] + .diff'


class WipCase(PageTestCase):
    """A fixture: a HEAD-commit az app.py 10. és 60. sorát módosítja, a lemezen a 35. és a 60. sor is, és egy új sor."""
    WIDTH, HEIGHT = 900, 900

    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "app.py").write_text(text(BASE), encoding="utf-8")
        git_in(repo, "add", "app.py")
        git_in(repo, "commit", "-qm", "wip: alap")
        (repo / "app.py").write_text(text(HEAD), encoding="utf-8")
        git_in(repo, "commit", "-qam", "wip: a commit")
        (repo / "app.py").write_text(text(DISK), encoding="utf-8")

    def open_app(self, subject: str = "wip: a commit") -> None:
        self.page.locator("#rows .row", has_text=subject).click()
        self.settle()
        self.page.locator('.details .file[data-path="app.py"]').click()
        self.page.wait_for_selector(f"{SEL} .cm-editor")
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

    def test_older_commit_no_layer(self) -> None:
        """Régebbi commitban nincs WIP-réteg."""
        self.open_app("wip: alap")
        self.assertEqual(self.page.locator(f"{SEL} .cm-wipLine, {SEL} .cm-wipDeleted").count(), 0)



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

if __name__ == "__main__":
    unittest.main()
