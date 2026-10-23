"""A lap adatcsomagja (`graph`): refek és az összerakott csomag — worktree-k, WIP-sorok, fájlállapot."""
from __future__ import annotations

import time
from unittest import mock

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

    def test_mirrors(self) -> None:
        """A közös ős nélküli történet azonos subjectű, szerzőjű és author-dátumú commitja a forrás
        tükre (`mirrorOf`); a cherry-pick (közös ős van) és a forrás maga nem az."""
        repo = self.plain_repo()
        run = lambda *a: git_in(repo, *a)  # noqa: E731
        date = "--date=@1780000000 +0000"                                # az author-dátum
        run("commit", "-q", "--allow-empty", "-m", "forrás", date)
        src = run("rev-parse", "HEAD").strip()
        run("switch", "-q", "-c", "pick", "HEAD~1")
        run("cherry-pick", "--allow-empty", src)                       # közös ős: nem tükör
        run("switch", "-q", "--orphan", "split")
        run("commit", "-q", "--allow-empty", "-m", "forrás", date)
        mirror = run("rev-parse", "HEAD").strip()
        run("switch", "-q", "main")
        gg = self.load()
        gg.gitio.set_repo(repo)
        commits = gg.graph.collect_commits(None)
        gg.graph.mark_mirrors(commits, "")
        marked = {c["sha"]: c["mirrorOf"] for c in commits if "mirrorOf" in c}
        self.assertEqual(marked, {mirror: src})

    def test_subtree_splits(self) -> None:
        """A subtree squash-commitja (gyökér) a `git-subtree-split:` commitjához kötve (`splitOf`);
        a squash nélküli subtree merge-nél a split a szülője, ott nincs `splitOf`."""
        repo = self.plain_repo()
        run = lambda *a: git_in(repo, *a)  # noqa: E731
        run("switch", "-q", "--orphan", "split")
        run("commit", "-q", "--allow-empty", "-m", "widget")
        split = run("rev-parse", "HEAD").strip()
        trailer = f"git-subtree-dir: widgets\ngit-subtree-split: {split}"
        run("switch", "-q", "--orphan", "squash")
        run("commit", "-q", "--allow-empty", "-m", f"Squashed 'widgets/' content\n\n{trailer}")
        squash = run("rev-parse", "HEAD").strip()
        run("switch", "-q", "main")
        run("merge", "-q", "--allow-unrelated-histories", "-m", f"Add 'widgets/'\n\n{trailer}", split)
        gg = self.load()
        gg.gitio.set_repo(repo)
        commits = gg.graph.collect_commits(None)
        gg.graph.mark_subtree_splits(commits)
        self.assertEqual({c["sha"]: c["splitOf"] for c in commits if "splitOf" in c}, {squash: split})

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
        self.assertEqual(files(f"*uncommitted:{slug}"), {".gitignore": ("A", None),
                                                          "u/v.txt": ("A", 0), "u/w/x.txt": ("A", 0)})
        self.assertEqual(files(f"*staged:{slug}"), {"d/n/new": ("D", 0)})     # a `git rm` stage-el

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
        owner = {c["subject"]: c["owner"] for c in data["commits"] if c.get("stash")}
        self.assertEqual(owner, {"On feat: wt": wt, "On main: fo": data["meta"]["worktrees"][0]["slug"]})

class BinarySizeTest(HomeTestCase):
    """A bináris fájl sora a méretet adja (`size`: [régi, új] bájtban, a hiányzó oldal `None`),
    ugyanazokról az oldalakról, ahonnan a diff is számol."""

    def commit_bytes(self, repo, msg: str, **files: bytes | None) -> str:
        for name, data in files.items():
            path = repo / name.replace("__", ".")
            if data is None:
                git_in(repo, "rm", "-q", str(path))
            else:
                path.write_bytes(data)
                git_in(repo, "add", str(path))
        git_in(repo, "commit", "-qm", msg)
        return git_in(repo, "rev-parse", "HEAD").strip()

    def sizes(self, data: dict, sha: str) -> dict:
        return {f["path"]: f.get("size") for f in data["stats"][sha]["files"] if f["bin"]}

    def test_commit_sizes(self) -> None:
        """Hozzáadott, törölt, módosított és azonos méretű bináris fájl a commitban; a szöveges
        fájl nem kap méretet."""
        repo = self.plain_repo()
        add = self.commit_bytes(repo, "add", logo__png=b"\0" * 12288, doc__pdf=b"\0" * 3145728,
                                same__png=b"\0" * 100, mod__png=b"\0" * 12390)
        mod = self.commit_bytes(repo, "mod", mod__png=b"\1\0" * 7116 + b"\1", same__png=b"\0\1" * 50)
        gone = self.commit_bytes(repo, "del", logo__png=None)
        gg = self.load()
        gg.gitio.set_repo(repo)
        data = gg.graph.collect_payload(None)
        self.assertEqual(self.sizes(data, add), {"doc.pdf": [None, 3145728], "logo.png": [None, 12288],
                                                 "mod.png": [None, 12390], "same.png": [None, 100]})
        self.assertEqual(self.sizes(data, mod), {"mod.png": [12390, 14233], "same.png": [100, 100]})
        self.assertEqual(self.sizes(data, gone), {"logo.png": [12288, None]})
        self.assertFalse([f for st in data["stats"].values() for f in st["files"] if not f["bin"] and "size" in f])

    def test_pending_sizes(self) -> None:
        """A stage-elt sor a HEAD-hez, a nem commitolt az indexhez méri; a követetlen bináris fájl
        új fájl. Egy `graph_data`-n belül a méretekhez egy `cat-file --batch-check` fut."""
        repo = self.plain_repo()
        self.commit_bytes(repo, "add", b__png=b"\0" * 2000)
        (repo / "b.png").write_bytes(b"\0" * 1800)
        git_in(repo, "add", "b.png")
        (repo / "b.png").write_bytes(b"\0\2" * 795)
        (repo / "u.png").write_bytes(b"\xff\0" * 32)
        gg = self.load()
        gg.gitio.set_repo(repo)
        calls = []
        run = gg.gitio.subprocess.run

        def spy(args, **kw):
            if "--batch-check" in args and "png" in (kw.get("input") or ""):
                calls.append(args)
            return run(args, **kw)

        with mock.patch.object(gg.gitio.subprocess, "run", spy):
            data = gg.graph.collect_payload(None)
        slug = data["meta"]["worktrees"][0]["slug"]
        self.assertEqual(self.sizes(data, f"*staged:{slug}"), {"b.png": [2000, 1800]})
        self.assertEqual(self.sizes(data, f"*uncommitted:{slug}"), {"b.png": [1800, 1590], "u.png": [None, 64]})
        self.assertEqual(len(calls), 1)


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


class FileListLimitTest(HomeTestCase):
    """A fájllista mérete: a host-híd 4 000 000 karakternél nagyobb választ nem ad át
    („The tool result is too large.”) — egy `node_modules` sem feszítheti szét."""

    def test_untracked_dir_collapsed(self) -> None:
        """A sok fájlos, teljesen követetlen mappa a WIP-sorban egyetlen bejegyzés, a fájlszámával."""
        gg = self.load()
        repo = self.plain_repo()
        (repo / "node_modules" / "pkg").mkdir(parents=True)
        for i in range(gg.worktrees.DIR_COLLAPSE + 1):
            (repo / "node_modules" / "pkg" / f"f{i}.js").write_text("x\n", encoding="utf-8")
        (repo / "uj").mkdir()
        (repo / "uj" / "b.txt").write_text("1\n2\n", encoding="utf-8")
        gg.gitio.set_repo(repo)
        data = gg.graph.collect_payload(None)
        churn = data["stats"][data["commits"][0]["sha"]]
        self.assertEqual([(f["path"], f.get("count"), f.get("status")) for f in churn["files"]],
                         [("node_modules/", gg.worktrees.DIR_COLLAPSE + 1, "A"), ("uj/b.txt", None, "A")])
        self.assertEqual(churn["add"], 2)

    def test_file_list_capped(self) -> None:
        """Soronként legfeljebb `FILES_MAX` fájl; a többi száma `more`, a +/− az összes fájlé."""
        gg = self.load()
        repo = self.plain_repo()
        gg.stats.FILES_MAX = 3
        for i in range(5):
            (repo / f"f{i}.txt").write_text("x\n", encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "öt fájl")
        gg.gitio.set_repo(repo)
        data = gg.graph.collect_payload(None)
        st = data["stats"][data["commits"][0]["sha"]]
        self.assertEqual([f["path"] for f in st["files"]], ["f0.txt", "f1.txt", "f2.txt"])
        self.assertEqual((st["more"], st["add"]), (2, 5))

    def test_ignored_tracked_hidden(self) -> None:
        """A `.gitignore` szerint kizárt fájl akkor is kimarad, ha commitolva van: a commitban
        és a WIP-sorban is; a száma `ignored`, a +/− nélküle. A `.gitignore` maga nem commitolt."""
        gg = self.load()
        repo = self.plain_repo()
        (repo / "node_modules").mkdir()
        (repo / "node_modules" / "x.js").write_text("1\n2\n", encoding="utf-8")
        (repo / "b.txt").write_text("b\n", encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "node_modules is")
        (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        (repo / "node_modules" / "x.js").write_text("1\n2\n3\n", encoding="utf-8")
        gg.gitio.set_repo(repo)
        data = gg.graph.collect_payload(None)
        wip, head = data["commits"][0]["sha"], data["commits"][1]["sha"]
        st = data["stats"][head]
        self.assertEqual(([f["path"] for f in st["files"]], st["add"], st["ignored"]), (["b.txt"], 1, 1))
        st = data["stats"][wip]
        self.assertEqual(([f["path"] for f in st["files"]], st["ignored"]), ([".gitignore"], 1))
