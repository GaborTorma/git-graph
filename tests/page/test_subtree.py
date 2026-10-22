"""Egy `git subtree split` / `push` remote-ja a lapon: a `widgets` remote története a `main`
két commitjának tükre — ugyanaz a subject, szerző és author-dátum, más hash, közös ős nélkül."""
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

from harness import PageTestCase, git_in

MIRRORED = ("main-4-3", "main-4-4")          # a `main` commitjai, amelyeknek tükre van


class SubtreeTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        origin = repo.parent / "origin.git"
        git_in(repo.parent, "init", "-q", "--bare", "-b", "main", str(origin))
        git_in(repo, "remote", "add", "origin", str(origin))
        git_in(repo, "push", "-q", "-u", "origin", "main")
        git_in(repo, "remote", "set-head", "origin", "main")
        # A tükör-történet: külön repó, a tükrözött commitok metaadataival (mint a `subtree split`).
        split = repo.parent / "split"
        git_in(repo.parent, "init", "-q", "-b", "main", str(split))
        for name in MIRRORED:
            subject = f"{name}: egy commit a fixture-ből"
            date = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%ad", "--date=raw",
                                   f"--grep=^{subject}$"], check=True, capture_output=True, text=True).stdout.strip()
            (split / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
            git_in(split, "add", ".")
            git_in(split, "commit", "-qm", subject,
                   env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
        git_in(repo, "remote", "add", "widgets", str(split))
        git_in(repo, "fetch", "-q", "widgets")

    def chip(self, name: str):
        return self.page.locator("#rows .badge.ref-remote", has_text=name)

    def test_unrelated_chip(self) -> None:
        """A közös ős nélküli remote ág chipjén nincs ↑↓, helyette áthúzott lánc, a tooltip megmondja, miért."""
        chip = self.chip("widgets/main")
        self.assertEqual(chip.count(), 1)
        self.assertEqual(chip.locator(".dist.unrelated svg.ic").count(), 1)
        self.assertNotIn("↑", chip.inner_text())
        self.assertNotIn("↓", chip.inner_text())
        self.assertIn("Külön történet: nincs közös őse az alapággal", chip.get_attribute("data-tip"))

    def test_mirror_rows(self) -> None:
        """A tükör-commit sora halvány, a pöttye üres, és szaggatott ív köti a forrás pöttyéhez."""
        for name in MIRRORED:
            rows = self.page.locator("#rows .row", has_text=f"{name}: egy commit")
            self.assertEqual(rows.count(), 2)                                    # forrás és tükör
            self.assertEqual(self.page.locator("#rows .row.mirror", has_text=f"{name}:").count(), 1)
            mirror = self.page.locator("#rows .row.mirror", has_text=f"{name}:")
            opacity = mirror.locator(".subject").evaluate("e => getComputedStyle(e).opacity")
            self.assertEqual(opacity, "0.55")
        arcs = self.page.locator('#lanes path[stroke-dasharray="2 2"]')
        self.assertEqual(arcs.count(), len(MIRRORED))
        self.assertEqual(arcs.first.get_attribute("stroke-width"), "1.2")
        # a tükör pöttye üres karika: háttérszínű kitöltés
        y = mirror.evaluate("e => e.offsetTop + e.offsetHeight / 2")
        hollow = self.page.locator(f'#lanes circle[cy="{y}"]')
        self.assertEqual(hollow.get_attribute("fill"), "var(--bg)")


if __name__ == "__main__":
    unittest.main()
