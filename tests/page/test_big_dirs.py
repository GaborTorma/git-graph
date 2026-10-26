"""Nagy fájllista a lapon: az összevont követetlen mappa egy sor, a `.gitignore`
szerint kizárt, de commitolt fájl rejtve — a lap a darabszámukat mutatja."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, git_in

DIR_FILES = 150   # több, mint a `DIR_COLLAPSE`


class BigDirsTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "vendor").mkdir()
        (repo / "vendor" / "lib.js").write_text("x\n", encoding="utf-8")
        git_in(repo, "add", "vendor")
        git_in(repo, "commit", "-qm", "vendor is")
        (repo / ".gitignore").write_text("vendor/\n", encoding="utf-8")
        (repo / "node_modules" / "pkg").mkdir(parents=True)
        for i in range(DIR_FILES):
            (repo / "node_modules" / "pkg" / f"f{i}.js").write_text("x\n", encoding="utf-8")

    def test_collapsed_dir(self) -> None:
        """Adott egy 150 fájlos követetlen mappa; ha a WIP-sor nyílik, akkor a mappa egy sor a fájlszámával."""
        self.page.locator('.row.uncommitted:has-text("Nem commitolt")').click()
        self.settle()
        self.assertEqual(self.page.locator(".details .file-dir").inner_text().split(),
                         ["node_modules/", str(DIR_FILES), "fájl"])
        self.assertEqual(self.page.locator(".details .files-head .n").inner_text(), str(DIR_FILES + 1))
        self.assertEqual(self.page.locator(".details .file").all_inner_texts()[0].split()[0], ".gitignore")

    def test_ignored_hidden(self) -> None:
        """Adott egy commitolt, de már ignorált fájl; ha a commitja nyílik, akkor nem látszik, csak a száma."""
        self.page.locator('.row:has-text("vendor is")').click()
        self.settle()
        self.assertEqual(self.page.locator(".details .file").count(), 0)
        self.assertEqual(self.page.locator(".details .files-note").inner_text(), "1 fájl rejtve (.gitignore)")


if __name__ == "__main__":
    unittest.main()
