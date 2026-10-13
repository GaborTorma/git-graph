"""A lap adatcsomagja (`graph`): refek és az összerakott csomag — worktree-k, WIP-sorok, fájlállapot."""
from __future__ import annotations

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
        self.assertEqual(new, [{"path": "uj.txt", "add": 1, "del": 0, "bin": False, "status": "A",
                               "icon": "text"}])
        for c in pending:
            path = data["stats"][c["sha"]]["files"][0]["path"]
            self.assertTrue(gg.diff.file_diff(c["sha"], path)["hunks"], c["sha"])

    def test_file_status(self) -> None:
        """Új fájl `A`, törölt `D`; a `dirFrom` az első új / kiürült mappa kezdete — commitban és a WIP-ben is."""
        main = self.plain_repo()

        def commit(msg: str, **files: str | None) -> str:
            for path, text in files.items():
                path = main / path.replace("__", "/")
                if text is None:
                    git_in(main, "rm", "-q", str(path))
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(text, encoding="utf-8")
                    git_in(main, "add", str(path))
            git_in(main, "commit", "-qm", msg)
            return git_in(main, "rev-parse", "HEAD").strip()

        first = commit("d", d__old="1\n", a="2\n")
        second = commit("n", d__n__new="más\n", d__old=None)
        git_in(main, "rm", "-q", "d/n/new")                         # d/n és d is kiürül
        (main / "u" / "w").mkdir(parents=True)
        (main / "u" / "v.txt").write_text("1\n", encoding="utf-8")  # követetlen mappa: a fájljai látszanak
        (main / "u" / "w" / "x.txt").write_text("1\n", encoding="utf-8")
        (main / "ures").mkdir()                                     # fájl nélküli mappa: nem látszik
        (main / ".gitignore").write_text("ign/\n", encoding="utf-8")
        (main / "ign").mkdir()
        (main / "ign" / "y.txt").write_text("1\n", encoding="utf-8")  # ignorált: nem látszik
        gg = self.load()
        gg.gitio.set_repo(main)
        data = gg.graph.collect_payload(None)

        def files(sha: str) -> dict:
            return {f["path"]: (f.get("status"), f.get("dirFrom")) for f in data["stats"][sha]["files"]}

        self.assertEqual(files(first), {"a": ("A", None), "d/old": ("A", 0)})
        self.assertEqual(files(second), {"d/n/new": ("A", 2), "d/old": ("D", None)})   # a d megmaradt
        slug = data["meta"]["worktrees"][0]["slug"]
        self.assertEqual(files(f"*uncommitted:{slug}"), {"d/n/new": ("D", 0), ".gitignore": ("A", None),
                                                          "u/v.txt": ("A", 0), "u/w/x.txt": ("A", 0)})

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

    def test_stash(self) -> None:
        """A stash egy sor a bázisán (`-u`-val is): a segédcommitjai (`^2`, `^3`) nem sorok,
        a régebbi stash is látszik, a fájllista és a diff a bázishoz képest."""
        main = self.plain_repo()
        base = git_in(main, "rev-parse", "HEAD").strip()
        (main / "a.txt").write_text("2\n", encoding="utf-8")
        (main / "u.txt").write_text("új\n", encoding="utf-8")
        git_in(main, "stash", "push", "-q", "-u", "-m", "egy")
        (main / "a.txt").write_text("3\n", encoding="utf-8")
        git_in(main, "stash", "push", "-q", "-m", "ketto")
        top, old = git_in(main, "stash", "list", "--format=%H").split()
        gg = self.load()
        gg.gitio.set_repo(main)
        data = gg.graph.collect_payload(None)
        self.assertEqual([c["sha"] for c in data["commits"]], [top, old, base])
        for sha, name in ((top, "stash@{0}"), (old, "stash@{1}")):
            c = next(c for c in data["commits"] if c["sha"] == sha)
            self.assertEqual((c["parents"], c["refs"], c.get("stash"), c.get("branch")),
                             ([base], [{"kind": "stash", "name": name}], True, "main"))
        self.assertEqual([(e["fromRow"], e["toRow"]) for e in data["edges"]], [(0, 2), (1, 2)])
        self.assertEqual(len({c["lane"] for c in data["commits"]}), 3)   # a két stash a saját sávján
        self.assertEqual(data["meta"]["totalCommits"], 3)
        # A `-u` követetlen fájlja (a `^3`-ban) is a listában, új fájlként.
        files = {f["path"]: f.get("status") for f in data["stats"][old]["files"]}
        self.assertEqual(files, {"a.txt": None, "u.txt": "A"})
        self.assertEqual(data["stats"][old]["add"], 2)
        self.assertEqual([f["path"] for f in data["stats"][top]["files"]], ["a.txt"])
        for path in files:
            self.assertTrue(gg.diff.file_diff(old, path)["hunks"], path)


    def test_stash_lanes(self) -> None:
        """A hozzáadott worktree stash-e (az ága szerint) a worktree oszlopai után ül; a fő
        checkouté a fő checkout oszlopai közt marad."""
        main, extra = self.make_repo()
        (extra / "b.txt").write_text("stash\n", encoding="utf-8")
        git_in(extra, "stash", "push", "-q", "-m", "wt", "--", "b.txt")
        (main / "c.txt").write_text("stash\n", encoding="utf-8")
        git_in(main, "stash", "push", "-q", "-u", "-m", "fo", "--", "c.txt")
        gg = self.load()
        gg.gitio.set_repo(main)
        data = gg.graph.collect_payload(None)
        lane = {c["subject"]: c["lane"] for c in data["commits"]}
        wt = data["meta"]["worktrees"][1]["slug"]
        wt_lane = next(c["lane"] for c in data["commits"] if c.get("worktree") == wt)
        self.assertLess(lane["On main: fo"], wt_lane)
        self.assertEqual(lane["On feat: wt"], wt_lane + 1)

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
