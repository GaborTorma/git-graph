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
        self.assertEqual(gg.worktrees.collect_uncommitted(wt), [])
        (repo / "a.txt").write_text("1\n2\n", encoding="utf-8")
        wt = gg.worktrees.collect_worktrees()[0]
        [(commit, churn)] = gg.worktrees.collect_uncommitted(wt)
        self.assertEqual(commit["author"], "Teszt Elek")
        self.assertEqual(commit["parents"], [wt["head"]])
        self.assertEqual((churn["add"], churn["del"]), (1, 0))
        self.assertEqual(gg.worktrees.collect_uncommitted({**wt, "head": None}), [])

    def test_staged_row(self) -> None:
        """A stage-elt változás a nem stage-elt sor alatti külön sor: lánc a HEAD-re, fájlonként
        a saját oldala; csak stage-elt változásnál csak az a sor."""
        gg = self.load()
        repo = self.plain_repo()
        (repo / "a.txt").write_text("1\n2\n3\n", encoding="utf-8")
        git_in(repo, "add", "a.txt")
        gg.gitio.set_repo(repo)
        wt = gg.worktrees.collect_worktrees()[0]
        [(staged, churn)] = gg.worktrees.collect_uncommitted(wt)
        self.assertEqual((staged["sha"], staged["parents"]), (f"*staged:{wt['slug']}", [wt["head"]]))
        self.assertTrue(staged["staged"] and staged["uncommitted"])
        self.assertEqual((churn["add"], churn["del"]), (2, 0))
        (repo / "a.txt").write_text("1\n2\n3\n4\n", encoding="utf-8")
        (repo / "uj.txt").write_text("x\n", encoding="utf-8")
        wt = gg.worktrees.collect_worktrees()[0]
        (top, top_churn), (staged, churn) = gg.worktrees.collect_uncommitted(wt)
        self.assertEqual((top["sha"], top["parents"]), (f"*uncommitted:{wt['slug']}", [staged["sha"]]))
        self.assertNotIn("staged", top)
        self.assertEqual([(f["path"], f["add"]) for f in top_churn["files"]], [("a.txt", 1), ("uj.txt", 1)])
        self.assertEqual([(f["path"], f["add"]) for f in churn["files"]], [("a.txt", 2)])
        def added(sha: str) -> list[str]:
            return [ln["s"] for h in gg.diff.file_diff(sha, "a.txt")["hunks"] for ln in h["lines"] if ln["t"] == "+"]

        self.assertEqual(added(top["sha"]), ["4"])           # az indexhez képest
        self.assertEqual(added(staged["sha"]), ["2", "3"])   # a HEAD-hez képest

    def test_untracked_files(self) -> None:
        """A követetlen fájl sorai a +-ba számítanak, és útvonal szerint a helyükre kerülnek."""
        gg = self.load()
        repo = self.plain_repo()
        (repo / "0.txt").write_text("x\ny\nz\n", encoding="utf-8")
        (repo / "0.bin").write_bytes(b"\xff\x00")
        (repo / "a.txt").write_text("1\n2\n", encoding="utf-8")
        gg.gitio.set_repo(repo)
        [(_, churn)] = gg.worktrees.collect_uncommitted(gg.worktrees.collect_worktrees()[0])
        self.assertEqual([(f["path"], f["add"], f["bin"]) for f in churn["files"]],
                         [("0.bin", 0, True), ("0.txt", 3, False), ("a.txt", 1, False)])
        self.assertEqual(churn["add"], 4)

    def test_unstaged_rename(self) -> None:
        """A még nem stage-elt átnevezés (`mv` + kis módosítás) egy `R` sor; eltérő tartalom: `D` + `A`."""
        gg = self.load()
        repo = self.plain_repo()
        body = "".join(f"sor {i}\n" for i in range(10))
        (repo / "regi").mkdir()
        (repo / "regi" / "SKILL.md").write_text(body, encoding="utf-8")
        (repo / "mas.txt").write_text("egy\nketto\n", encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "alap")
        (repo / "regi").rename(repo / "uj")
        (repo / "uj" / "SKILL.md").write_text(body.replace("sor 3", "harmadik"), encoding="utf-8")
        (repo / "mas.txt").unlink()
        (repo / "teljesen-mas.txt").write_text("alma\nkorte\n", encoding="utf-8")
        gg.gitio.set_repo(repo)
        [(_, churn)] = gg.worktrees.collect_uncommitted(gg.worktrees.collect_worktrees()[0])
        self.assertEqual([(f["path"], f["add"], f["del"], f.get("status")) for f in churn["files"]],
                         [("mas.txt", 0, 2, "D"), ("teljesen-mas.txt", 2, 0, "A"),
                          ("{regi => uj}/SKILL.md", 1, 1, None)])
        self.assertEqual((churn["add"], churn["del"]), (3, 3))
        self.assertEqual(git_in(repo, "status", "--porcelain").count("??"), 2)    # az index érintetlen

    def test_rename_path(self) -> None:
        """Az átnevezés a git `--numstat` alakjában: a közös mappák a kapcsos zárójelen kívül."""
        gg = self.load()
        for old, new, want in (("a/x/f.md", "a/y/f.md", "a/{x => y}/f.md"), ("a.txt", "b.txt", "a.txt => b.txt"),
                               ("d/a.txt", "d/b.txt", "d/{a.txt => b.txt}"), ("f.md", "sub/f.md", "f.md => sub/f.md")):
            self.assertEqual(gg.worktrees.rename_path(old, new), want)
            self.assertEqual(gg.gitio.numstat_new_path(want), new)
            self.assertEqual(gg.gitio.numstat_old_path(want), old)
