"""Egy `git subtree split` / `push` remote-ja a lapon: a `widgets` remote története a `main`
két commitjának tükre — ugyanaz a subject, szerző és author-dátum, más hash, közös ős nélkül."""
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path

from harness import PageTestCase, git_in

MIRRORED = ("main-4-3", "main-4-4")          # a `main` commitjai, amelyeknek tükre van


def add_origin(repo: Path) -> None:
    """Az `origin` remote, a `main` pusholva, az `origin/HEAD` rá mutat."""
    origin = repo.parent / "origin.git"
    git_in(repo.parent, "init", "-q", "--bare", "-b", "main", str(origin))
    git_in(repo, "remote", "add", "origin", str(origin))
    git_in(repo, "push", "-q", "-u", "origin", "main")
    git_in(repo, "remote", "set-head", "origin", "main")


class SubtreeTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        add_origin(repo)
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

    def toggle_remote(self, name: str) -> None:
        self.page.locator("#remotesBtn").click()
        self.page.locator(f'#remotesPop .option[data-key="{name}"]').click()
        self.page.keyboard.press("Escape")
        self.settle()

    def test_remote_filter(self) -> None:
        """A remote-szűrő elrejti a remote ágait és a csak onnan elérhető commitokat; a választás újratöltve is megmarad."""
        self.assertTrue(self.page.locator("#remotesBtn").is_visible())
        self.assertEqual(self.page.locator("#remotesLabel").inner_text(), "Minden remote")
        self.toggle_remote("widgets")
        self.assertEqual(self.page.locator("#remotesLabel").inner_text(), "origin")
        self.assertEqual(self.chip("widgets/main").count(), 0)
        self.assertEqual(self.page.locator("#rows .row.mirror").count(), 0)         # csak a widgetsből érhető el
        self.assertGreater(self.page.locator("#rows .badge", has_text="origin").count(), 0)
        self.page.locator("#branchBtn").click()
        self.assertEqual(self.page.locator('#branchPop .menu-grp[data-name="widgets"]').count(), 0)
        self.page.keyboard.press("Escape")
        self.page.reload()
        self.page.wait_for_selector("#rows .row")
        self.settle()
        self.assertEqual(self.page.locator("#remotesLabel").inner_text(), "origin")
        self.assertEqual(self.chip("widgets/main").count(), 0)
        self.toggle_remote("widgets")
        self.assertEqual(self.chip("widgets/main").count(), 1)

    def test_remote_filter_follows_switch(self) -> None:
        """A „Remote ágak” kikapcsolva a remote-szűrő gombja tiltott."""
        self.page.locator("label.switch:has(#showRemotes)").click()
        self.settle()
        self.assertTrue(self.page.locator("#remotesBtn").is_disabled())


class SquashTest(PageTestCase):
    """`git subtree add --squash`: a squash-commit gyökér, a tartalma a `widgets/main`
    csúcsából jön, amire csak a `git-subtree-split:` sora mutat."""

    @classmethod
    def prepare(cls, repo: Path) -> None:
        split = repo.parent / "split"
        git_in(repo.parent, "init", "-q", "-b", "main", str(split))
        (split / "widget.txt").write_text("widget\n", encoding="utf-8")
        git_in(split, "add", ".")
        git_in(split, "commit", "-qm", "widget: a split csúcsa")
        git_in(repo, "remote", "add", "widgets", str(split))
        git_in(repo, "fetch", "-q", "widgets")
        out = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True,  # noqa: E731
                                        capture_output=True, text=True).stdout.strip()
        cls.split = out("rev-parse", "widgets/main")
        trailer = f"git-subtree-dir: widgets\ngit-subtree-split: {cls.split}"
        cls.squash = out("commit-tree", out("rev-parse", "widgets/main^{tree}"),
                         "-m", f"Squashed 'widgets/' content from commit {cls.split[:7]}\n\n{trailer}")
        git_in(repo, "merge", "-q", "--allow-unrelated-histories", "-m", "widgets subtree", cls.squash)

    def test_squash_arc(self) -> None:
        """A squash-commitot szaggatott ív köti a split-commithoz, nem folytonos él."""
        y = lambda sha: self.page.locator(f'#rows .row[data-sha="{sha}"]').evaluate(  # noqa: E731
            "e => e.offsetTop + e.offsetHeight / 2")
        arcs = self.page.locator('#lanes path[stroke-dasharray="2 2"]')
        self.assertEqual(arcs.count(), 1)
        d = arcs.first.get_attribute("d")
        self.assertTrue(d.startswith("M ") and d.split()[2] == str(y(self.squash)), d)
        self.assertTrue(d.endswith(f" {y(self.split)}"), d)


class SingleRemoteTest(PageTestCase):
    @classmethod
    def prepare(cls, repo: Path) -> None:
        add_origin(repo)

    def test_no_remote_filter(self) -> None:
        """Egyetlen remote-nál a remote-szűrő nem jelenik meg."""
        self.assertFalse(self.page.locator("#remotesBtn").is_visible())


if __name__ == "__main__":
    unittest.main()
