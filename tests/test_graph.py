"""A lap adatcsomagja (`graph`): refek, sávok, worktree-k, ágak és távolságaik."""
from __future__ import annotations

import os
import time

from helpers import HomeTestCase, git_in


class GraphTest(HomeTestCase):
    def test_parse_refs(self) -> None:
        """A `%D` dekoráció badge-ekké: HEAD elöl, aztán ág, remote, a tag a végén."""
        gg = self.load()
        gg.gitio._REMOTES = {"origin", "fork"}
        refs = gg.graph.parse_refs("tag: v1, fork/x, HEAD -> main, origin/main, feat")
        self.assertEqual([(r["kind"], r["name"]) for r in refs],
                         [("head", "main"), ("branch", "feat"), ("remote", "fork/x"),
                          ("remote", "origin/main"), ("tag", "v1")])
        self.assertEqual(gg.graph.parse_refs("HEAD"), [{"kind": "detached", "name": "HEAD"}])

    def test_assign_lanes(self) -> None:
        """Merge: az első szülő a sávban folytatódik, a második új sávot kap; az élek sorindexesek."""
        gg = self.load()
        commits = [{"sha": "m", "parents": ["a", "b"]},
                   {"sha": "b", "parents": ["a"]},
                   {"sha": "a", "parents": []}]
        edges = gg.graph.assign_lanes(commits)
        self.assertEqual([c["lane"] for c in commits], [0, 1, 0])
        self.assertIn({"fromRow": 0, "fromLane": 0, "toRow": 1, "toLane": 1, "merge": True}, edges)
        self.assertIn({"fromRow": 1, "fromLane": 1, "toRow": 2, "toLane": 0, "merge": False}, edges)

    def test_assign_lanes_trunk(self) -> None:
        """A `trunk` a 0. sávot kapja akkor is, ha egy újabb commit előtte jön."""
        gg = self.load()
        commits = [{"sha": "f", "parents": ["a"]}, {"sha": "t", "parents": ["a"]}, {"sha": "a", "parents": []}]
        gg.graph.assign_lanes(commits, trunk="t")
        self.assertEqual([c["lane"] for c in commits], [1, 0, 0])

    def test_worktrees(self) -> None:
        """Közös adat: minden worktree HEAD-je és ál-sora, a diff a saját mappájából."""
        main, extra = self.make_repo()
        gg = self.load()
        gg.gitio.set_repo(gg.gitio.main_checkout(extra))
        self.assertEqual(gg.gitio.REPO, main)
        data = gg.graph.collect_payload(None)
        wts = data["meta"]["worktrees"]
        self.assertEqual([w["branch"] for w in wts], ["main", "feat"])
        self.assertEqual([w["main"] for w in wts], [True, False])
        pending = [c for c in data["commits"] if c.get("uncommitted")]
        self.assertEqual({c["worktree"] for c in pending}, {w["slug"] for w in wts})
        heads = {r["worktree"] for c in data["commits"] for r in c["refs"] if r["kind"] == "head"}
        self.assertEqual(heads, {w["slug"] for w in wts})
        lane = {c.get("worktree") or c["sha"]: c["lane"] for c in data["commits"]}
        self.assertEqual(lane[wts[0]["slug"]], 0)                  # a fő checkout ál-sora: 0. sáv
        self.assertEqual(lane[wts[0]["head"]], 0)
        self.assertNotEqual(lane[wts[1]["head"]], 0)               # a worktree ága elágazik
        side = git_in(main, "rev-parse", "side").strip()
        self.assertLess(lane[side], lane[wts[1]["head"]])          # a worktree oszlopa a végén
        self.assertEqual(data["meta"]["shown"], 3)                 # a valódi commitok, ál-sorok nélkül
        new = data["stats"][f"*uncommitted:{wts[1]['slug']}"]["files"]
        self.assertEqual(new, [{"path": "uj.txt", "add": 0, "del": 0, "bin": False, "new": True, "icon": "text"}])
        for c in pending:
            path = data["stats"][c["sha"]]["files"][0]["path"]
            self.assertTrue(gg.diff.file_diff(c["sha"], path)["hunks"], c["sha"])

    def test_remote_head(self) -> None:
        """Az `origin/HEAD` nem külön badge: a célja (`origin/main`) kapja a `default` jelet."""
        main, _ = self.make_repo()
        clone = main.parent / "clone"
        git_in(main.parent, "clone", "-q", str(main), str(clone))
        gg = self.load()
        gg.gitio.set_repo(clone)
        data = gg.graph.collect_payload(None)
        self.assertEqual(data["meta"]["remotes"], ["origin"])
        refs = [r for c in data["commits"] for r in c["refs"]]
        self.assertFalse([r for r in refs if r["name"].endswith("/HEAD")])
        self.assertTrue(next(r for r in refs if r["name"] == "origin/main").get("default"))

    def test_worktree_stubs(self) -> None:
        """Saját commit és WIP nélküli worktree HEAD-je csonkot kap; a saját ág csúcsa nem."""
        gg = self.load()
        commits = [{"sha": "c", "parents": ["a"], "refs": []},   # feat: saját ág
                   {"sha": "b", "parents": ["a"], "refs": []},   # trunk
                   {"sha": "a", "parents": [], "refs": []}]
        edges = gg.graph.assign_lanes(commits, "b")
        wt = lambda slug, head, main=False: {"slug": slug, "head": head, "main": main}  # noqa: E731
        gg.graph.worktree_stubs(commits, edges, [wt("m", "b", True), wt("feat", "c"), wt("old", "a")])
        self.assertNotIn("stubs", commits[0])
        self.assertNotIn("stubs", commits[1])
        self.assertEqual(commits[2]["stubs"], [{"lane": 2, "worktree": "old"}])

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
        tracks = gg.graph.branch_tracks(gg.gitio.default_base())
        self.assertEqual(gg.gitio.default_base(), "origin/main")
        self.assertEqual(tracks["feat"], {"up": [1, 0], "base": [2, 0]})
        self.assertEqual(tracks["main"], {"up": [1, 0]})              # az alapágnak nincs base-szakasza
        self.assertEqual(tracks["origin/feat"]["local"], [0, 1])       # a helyi feat egy committal előrébb
        self.assertEqual(tracks["origin/only-remote"], {"base": [2, 0]})
        self.assertEqual(tracks["origin/main"], {"local": [0, 1]})     # az alapág remote-ja: csak a helyi párjához
        branches = {b["name"]: b for b in gg.graph.collect_branches(gg.graph.collect_worktrees())}
        self.assertTrue(branches["origin/only-remote"]["remote"])      # a csak remote ág is választható
        self.assertNotIn("origin/feat", branches)                      # a helyi párja képviseli
        self.assertTrue(branches["main"]["current"])
        commits, stats = gg.graph.collect_commits(None), gg.graph.collect_stats(None)
        gg.graph.mark_pushed(commits, stats)       # a payload csak GitHub-os originnél hívja
        pushed = {c["subject"] for c in commits if c.get("pushed")}
        self.assertEqual(pushed, {"init", "f1", "f2"})                 # a helyi main előfutása nem

    def test_branch_owners(self) -> None:
        """Az ág a worktree-é, amelyikben utoljára ki volt véve (HEAD-reflog); a soha ki nem vett gazdátlan."""
        main, extra = self.make_repo()
        git_in(extra, "switch", "-q", "-c", "wt-side")                 # a worktree-ben létrehozva
        git_in(extra, "switch", "-q", "feat")
        git_in(main, "branch", "orphan")                               # sehol nem volt kivéve
        gg = self.load()
        gg.gitio.set_repo(main)
        wts = gg.graph.collect_worktrees()
        owners = gg.graph.branch_owners(wts)
        slug = {w["path"]: w["slug"] for w in wts}
        self.assertEqual(owners["main"], slug[main])
        self.assertEqual(owners["side"], slug[main])                   # a fő checkoutban járt
        self.assertEqual(owners["feat"], slug[extra])                  # ott van kivéve
        self.assertEqual(owners["wt-side"], slug[extra])
        self.assertNotIn("orphan", owners)
        branches = {b["name"]: b for b in gg.graph.collect_branches(wts)}
        self.assertEqual(branches["wt-side"]["owner"], slug[extra])
        self.assertIsNone(branches["orphan"]["owner"])
        self.assertEqual(branches["feat"]["worktree"], slug[extra])

    def test_last_change(self) -> None:
        """A WIP-sor ideje: a commitolatlan fájlok legutóbbi mtime-ja; a törölt kimarad."""
        gg = self.load()
        (self.home / "a.txt").write_text("x", encoding="utf-8")
        os.utime(self.home / "a.txt", (1000, 1000))
        files = [{"path": "a.txt"}, {"path": "torolt.txt"}]
        self.assertEqual(gg.graph.last_change(self.home, files), 1000)

    def test_collect_uncommitted(self) -> None:
        """Változás nélkül és commit nélküli repóban nincs ál-sor; a szerző a worktree git-felhasználója."""
        gg = self.load()
        repo = self.plain_repo()
        git_in(repo, "config", "user.name", "Teszt Elek")
        gg.gitio.set_repo(repo)
        wt = gg.graph.collect_worktrees()[0]
        self.assertIsNone(gg.graph.collect_uncommitted(wt))
        (repo / "a.txt").write_text("1\n2\n", encoding="utf-8")
        wt = gg.graph.collect_worktrees()[0]
        commit, churn = gg.graph.collect_uncommitted(wt)
        self.assertEqual(commit["author"], "Teszt Elek")
        self.assertEqual(commit["parents"], [wt["head"]])
        self.assertEqual((churn["add"], churn["del"]), (1, 0))
        self.assertIsNone(gg.graph.collect_uncommitted({**wt, "head": None}))


class WorktreeListTest(HomeTestCase):
    def test_worktree_order(self) -> None:
        """A hozzáadott worktree-k a létrehozásuk sorrendjében, nem név szerint."""
        main, extra = self.make_repo()
        later = self.home / "aaa-wt"                                   # névben előrébb, de újabb
        time.sleep(0.05)
        git_in(main, "worktree", "add", "-q", "--detach", str(later))
        gg = self.load()
        self.assertEqual([w["path"] for w in gg.gitio.worktree_list(main)], [main, extra, later])
        self.assertIsNone(gg.gitio.worktree_list(main)[2]["branch"])   # leválasztott HEAD
