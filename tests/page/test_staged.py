"""A stage-elt változás a lapon: külön sor a nem commitolt alatt, a saját fájljaival."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, git_in


class StagedTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        (repo / "main-4-5.txt").write_text("stage-elve\n", encoding="utf-8")
        git_in(repo, "add", "main-4-5.txt")
        (repo / "kovetetlen.txt").write_text("új\n", encoding="utf-8")

    def test_rows(self) -> None:
        """Felül a nem commitolt, alatta a stage-elt sor."""
        subjects = self.page.locator(".row.uncommitted .subject").all_inner_texts()
        self.assertEqual(subjects, ["Nem commitolt változások", "Stage-elt változások"])

    def test_files(self) -> None:
        """Mindkét sor csak a saját oldala fájljait mutatja."""
        for subject, name in (("Nem commitolt", "kovetetlen.txt"), ("Stage-elt", "main-4-5.txt")):
            self.page.locator(f'.row.uncommitted:has-text("{subject}")').click()
            self.settle()
            files = self.page.locator(".details .file").all_inner_texts()
            self.assertEqual(len(files), 1, subject)
            self.assertIn(name, files[0])


if __name__ == "__main__":
    unittest.main()
