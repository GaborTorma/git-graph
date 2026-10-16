"""A stash a lapon: egyetlen sor a saját chipjével (ikonnal), a segédcommitjai nélkül."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, git_in

class StashTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "main-4-5.txt").write_text("módosítva\n", encoding="utf-8")
        (repo / "kovetetlen.txt").write_text("új\n", encoding="utf-8")
        git_in(repo, "stash", "push", "-q", "-u", "-m", "félretéve")

    def test_one_row(self) -> None:
        subjects = self.page.locator("#rows .row .subject").all_inner_texts()
        self.assertEqual([s for s in subjects if "on main" in s.lower()], ["On main: félretéve"])   # index / untracked nincs
        chip = self.page.locator("#rows .badge.ref-stash")
        self.assertEqual(chip.all_inner_texts(), ["stash@{0}"])
        self.assertEqual(chip.locator("svg.ic").count(), 1)                         # a doboz-ikon

    def test_files_against_base(self) -> None:
        self.page.locator("#rows .row:has(.ref-stash)").click()
        self.settle()
        # a bázishoz képest, és a követetlen fájl (`^3`) is
        self.assertEqual(self.page.locator("#rows .details .file").count(), 2)

    def pick_branch(self, name: str) -> None:
        self.page.locator("#branchBtn").click()
        self.page.locator(f'#branchPop .option[data-key="{name}"]').click()
        self.settle()

    def test_branch_filter(self) -> None:
        """Ágszűrésnél a stash a saját ágával marad (`On main: …`), más ágnál nem látszik."""
        self.pick_branch("main")
        self.assertEqual(self.page.locator("#rows .row:has(.ref-stash)").count(), 1)
        self.pick_branch("feature/egy-nagyon-hosszu-ag-nev-a-badge-ekhez")
        self.assertEqual(self.page.locator("#rows .row:has(.ref-stash)").count(), 0)


if __name__ == "__main__":
    unittest.main()
