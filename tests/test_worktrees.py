"""A worktree-k (`worktrees`): a WIP-sor ideje, szerzője és a követetlen fájlai."""
from __future__ import annotations

import os

from helpers import HomeTestCase, git_in


class WorktreesTest(HomeTestCase):
    def test_last_change(self) -> None:
        """A WIP-sor ideje: a commitolatlan fájlok legutóbbi mtime-ja; a törölt kimarad."""
        gg = self.load()
        (self.home / "a.txt").write_text("x", encoding="utf-8")
        os.utime(self.home / "a.txt", (1000, 1000))
        files = [{"path": "a.txt"}, {"path": "torolt.txt"}]
        self.assertEqual(gg.worktrees.last_change(self.home, files), 1000)

    def test_collect_uncommitted(self) -> None:
        """Változás nélkül és commit nélküli repóban nincs ál-sor; a szerző a worktree git-felhasználója."""
        gg = self.load()
        repo = self.plain_repo()
        git_in(repo, "config", "user.name", "Teszt Elek")
        gg.gitio.set_repo(repo)
        wt = gg.worktrees.collect_worktrees()[0]
        self.assertIsNone(gg.worktrees.collect_uncommitted(wt))
        (repo / "a.txt").write_text("1\n2\n", encoding="utf-8")
        wt = gg.worktrees.collect_worktrees()[0]
        commit, churn = gg.worktrees.collect_uncommitted(wt)
        self.assertEqual(commit["author"], "Teszt Elek")
        self.assertEqual(commit["parents"], [wt["head"]])
        self.assertEqual((churn["add"], churn["del"]), (1, 0))
        self.assertIsNone(gg.worktrees.collect_uncommitted({**wt, "head": None}))

    def test_untracked_files(self) -> None:
        """A követetlen fájl sorai a +-ba számítanak, és útvonal szerint a helyükre kerülnek."""
        gg = self.load()
        repo = self.plain_repo()
        (repo / "0.txt").write_text("x\ny\nz\n", encoding="utf-8")
        (repo / "0.bin").write_bytes(b"\xff\x00")
        (repo / "a.txt").write_text("1\n2\n", encoding="utf-8")
        gg.gitio.set_repo(repo)
        _, churn = gg.worktrees.collect_uncommitted(gg.worktrees.collect_worktrees()[0])
        self.assertEqual([(f["path"], f["add"], f["bin"]) for f in churn["files"]],
                         [("0.bin", 0, True), ("0.txt", 3, False), ("a.txt", 1, False)])
        self.assertEqual(churn["add"], 4)
