"""Az ágak (`branches`): távolságok, csak remote ágak, gazda-worktree."""
from __future__ import annotations

from helpers import HomeTestCase, git_in


class BranchesTest(HomeTestCase):
    def test_branch_tracks(self) -> None:
        """Ágankénti távolság: az alapághoz, az upstreamhez, és a remote-only ágnak a helyi párjához."""
        bare, repo = self.home / "remote.git", self.home / "work"
        git_in(self.home, "init", "-q", "--bare", "-b", "main", str(bare))
        repo.mkdir()
        run = lambda *a: git_in(repo, *a)  # noqa: E731
        run("init", "-q", "-b", "main")
        run("remote", "add", "origin", str(bare))
        run("commit", "-q", "--allow-empty", "-m", "init")
        run("push", "-q", "-u", "origin", "main")
        run("remote", "set-head", "origin", "main")
        run("switch", "-q", "-c", "feat")
        run("commit", "-q", "--allow-empty", "-m", "f1")
        run("push", "-q", "-u", "origin", "feat")
        run("commit", "-q", "--allow-empty", "-m", "f2")                 # egy pusholatlan
        run("push", "-q", "origin", "feat:only-remote")                 # remote-only ág
        run("switch", "-q", "main")
        run("commit", "-q", "--allow-empty", "-m", "anomália")           # a helyi main előreszalad
        gg = self.load()
        gg.gitio.set_repo(repo)
        tracks = gg.branches.branch_tracks(gg.gitio.default_base())
        self.assertEqual(gg.gitio.default_base(), "origin/main")
        self.assertEqual(tracks["feat"], {"up": [1, 0], "base": [2, 0]})
        self.assertEqual(tracks["main"], {"up": [1, 0]})              # az alapágnak nincs base-szakasza
        self.assertEqual(tracks["origin/feat"]["local"], [0, 1])       # a helyi feat egy committal előrébb
        self.assertEqual(tracks["origin/only-remote"], {"base": [2, 0]})
        self.assertEqual(tracks["origin/main"], {"local": [0, 1]})     # az alapág remote-ja: csak a helyi párjához
        branches = {b["name"]: b for b in gg.branches.collect_branches(gg.worktrees.collect_worktrees())}
        self.assertTrue(branches["origin/only-remote"]["remote"])      # a csak remote ág is választható
        self.assertNotIn("origin/feat", branches)                      # a helyi párja képviseli
        self.assertTrue(branches["main"]["current"])
        commits, stats = gg.graph.collect_commits(None), gg.stats.collect_stats(None)
        gg.graph.mark_pushed(commits, stats)       # a payload csak GitHub-os originnél hívja
        pushed = {c["subject"] for c in commits if c.get("pushed")}
        self.assertEqual(pushed, {"init", "f1", "f2"})                 # a helyi main előfutása nem

    def test_other_name_upstream(self) -> None:
        """A más nevű upstream (az `origin/main`-ből indított branché) nem számít: nincs upstream,
        nincs távolság hozzá; a `-u` nélkül pusholt azonos nevű remote ág külön, csak remote ág."""
        bare, repo = self.home / "remote.git", self.home / "work"
        git_in(self.home, "init", "-q", "--bare", "-b", "main", str(bare))
        repo.mkdir()
        run = lambda *a: git_in(repo, *a)  # noqa: E731
        run("init", "-q", "-b", "main")
        run("remote", "add", "origin", str(bare))
        run("commit", "-q", "--allow-empty", "-m", "init")
        run("push", "-q", "-u", "origin", "main")
        run("remote", "set-head", "origin", "main")
        run("switch", "-q", "-c", "feat", "--track", "origin/main")
        run("commit", "-q", "--allow-empty", "-m", "f1")
        run("push", "-q", "origin", "feat")                              # -u nélkül
        gg = self.load()
        gg.gitio.set_repo(repo)
        tracks = gg.branches.branch_tracks(gg.gitio.default_base())
        self.assertEqual(tracks["feat"], {"base": [1, 0]})
        self.assertNotIn("local", tracks["origin/feat"])
        branches = {b["name"]: b for b in gg.branches.collect_branches(gg.worktrees.collect_worktrees())}
        self.assertEqual((branches["feat"]["upstream"], branches["feat"]["track"]), ("", ""))
        self.assertTrue(branches["origin/feat"]["remote"])

    def test_unrelated_history(self) -> None:
        """Közös ős nélkül (`git subtree push` remote-ja) nincs `base` távolság, csak `unrelated` jel;
        a szétvált, de rokon ágnál (mindkét irány nem nulla) a távolság marad."""
        bare, repo = self.home / "remote.git", self.home / "work"
        git_in(self.home, "init", "-q", "--bare", "-b", "main", str(bare))
        repo.mkdir()
        run = lambda *a: git_in(repo, *a)  # noqa: E731
        run("init", "-q", "-b", "main")
        run("remote", "add", "origin", str(bare))
        run("commit", "-q", "--allow-empty", "-m", "init")
        run("switch", "-q", "-c", "feat")
        run("commit", "-q", "--allow-empty", "-m", "f1")
        run("switch", "-q", "main")
        run("commit", "-q", "--allow-empty", "-m", "m1")
        run("push", "-q", "-u", "origin", "main", "feat")
        run("remote", "set-head", "origin", "main")
        run("switch", "-q", "--orphan", "split")
        run("commit", "-q", "--allow-empty", "-m", "s1")
        run("push", "-q", "origin", "split:only-split")                # remote-only, közös ős nélkül
        run("switch", "-q", "main")
        gg = self.load()
        gg.gitio.set_repo(repo)
        tracks = gg.branches.branch_tracks(gg.gitio.default_base())
        self.assertEqual(tracks["split"], {"unrelated": True})
        self.assertEqual(tracks["origin/only-split"], {"unrelated": True})
        self.assertEqual(tracks["feat"]["base"], [1, 1])               # rokon: a távolság marad

    def test_branch_owners(self) -> None:
        """Az ág a worktree-é, amelyikben utoljára ki volt véve (HEAD-reflog); a soha ki nem vett gazdátlan."""
        main, extra = self.make_repo()
        git_in(extra, "switch", "-q", "-c", "wt-side")                 # a worktree-ben létrehozva
        git_in(extra, "switch", "-q", "feat")
        git_in(main, "branch", "orphan")                               # sehol nem volt kivéve
        gg = self.load()
        gg.gitio.set_repo(main)
        wts = gg.worktrees.collect_worktrees()
        owners = gg.branches.branch_owners(wts)
        slug = {w["path"]: w["slug"] for w in wts}
        self.assertEqual(owners["main"], slug[main])
        self.assertEqual(owners["side"], slug[main])                   # a fő checkoutban járt
        self.assertEqual(owners["feat"], slug[extra])                  # ott van kivéve
        self.assertEqual(owners["wt-side"], slug[extra])
        self.assertNotIn("orphan", owners)
        branches = {b["name"]: b for b in gg.branches.collect_branches(wts)}
        self.assertEqual(branches["wt-side"]["owner"], slug[extra])
        self.assertIsNone(branches["orphan"]["owner"])
        self.assertEqual(branches["feat"]["worktree"], slug[extra])
