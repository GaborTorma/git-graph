"""Füstteszt: a `git-graph --mcp` stdio-n, kamu HOME-mal — ahogy az app indítja.

Futtatás: `/usr/bin/python3 -m unittest discover -s tests` (csak stdlib).
A valódi `~/.git-graph`-hoz és az app configjához nem nyúl.
"""
from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import time
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "git-graph"
PYTHON = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else "python3"
SLUG = "test-repo"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True,
                          capture_output=True, text=True).stdout


def git_in(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


class McpClient:
    """Soronként egy JSON-RPC üzenet, mint a Claude app host-hídja."""

    def __init__(self, script: Path, home: Path) -> None:
        env = {**os.environ, "HOME": str(home)}
        self.proc = subprocess.Popen([PYTHON, str(script), "--mcp"], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.next_id = 0

    def request(self, method: str, params: dict | None = None) -> dict:
        self.next_id += 1
        msg = {"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}}
        self.proc.stdin.write(json.dumps(msg).encode() + b"\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        line.decode("ascii")                       # a stdout csak ASCII lehet
        reply = json.loads(line)
        assert reply["id"] == self.next_id, reply
        return reply

    def call(self, name: str, **arguments: object) -> object:
        result = self.request("tools/call", {"name": name, "arguments": arguments})["result"]
        text = result["content"][0]["text"]
        if result["isError"]:
            raise AssertionError(f"{name}: {text}")
        return json.loads(text)

    def close(self) -> None:
        self.proc.stdin.close()
        self.proc.wait(timeout=10)
        self.proc.stdout.close()
        self.proc.stderr.close()


def load_module(home: Path):
    """A script modulként, kamu HOME-mal (a `STATE_DIR` betöltéskor rögzül)."""
    old = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        loader = importlib.machinery.SourceFileLoader("git_graph", str(SCRIPT))
        spec = importlib.util.spec_from_loader("git_graph", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        return module
    finally:
        if old is not None:
            os.environ["HOME"] = old


class McpServerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        state = self.home / ".git-graph"
        state.mkdir()
        (state / "repos.json").write_text(json.dumps({SLUG: str(ROOT)}), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def check_server(self, script: Path) -> None:
        client = McpClient(script, self.home)
        try:
            init = client.request("initialize", {"protocolVersion": "2025-06-18"})["result"]
            self.assertEqual(init["serverInfo"]["name"], "git-graph")
            tools = {t["name"]: t for t in client.request("tools/list")["result"]["tools"]}
            self.assertEqual(set(tools), {"fingerprint", "graph_data", "file_diff", "page_code"})
            self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in tools.values()))

            code = client.call("page_code", repo=SLUG, api=1)
            self.assertIn("<style>", code["head"])
            self.assertIn('id="rows"', code["body"])
            self.assertIn("globalThis.GIT_GRAPH", code["js"])
            with self.assertRaises(AssertionError):            # eltérő betöltő-szerződés
                client.call("page_code", repo=SLUG, api=0)

            data = client.call("graph_data", repo=SLUG)
            self.assertTrue(data["commits"])
            self.assertIn("edges", data)
            self.assertIn("avatars", data)
            self.assertTrue(all("email" in c for c in data["commits"] if not c.get("uncommitted")))
            self.assertIn("refs", client.call("fingerprint", repo=SLUG))
            icons = {f.get("icon") for st in data["stats"].values() for f in st["files"]}
            self.assertTrue(icons - {None} and icons - {None} <= set(data["fileIcons"]))

            merge = git("log", "-1", "--merges", "--format=%H").strip()
            if merge and merge in data["stats"]:                # a merge az első szülőjéhez képest
                files = data["stats"][merge]["files"]
                self.assertTrue(files, "a merge commit fájllistája üres")
                diff = client.call("file_diff", repo=SLUG, sha=merge, path=files[0]["path"])
                self.assertTrue(diff["hunks"] or diff.get("binary"))

            sha = git("log", "-1", "--no-merges", "--format=%H").strip()   # a merge-nek nincs fájllistája
            path = git("show", "--format=", "--name-only", sha).split()[0]
            self.assertIsInstance(client.call("file_diff", repo=SLUG, sha=sha, path=path), dict)
            with self.assertRaises(AssertionError):            # opcióként menne a gitnek
                client.call("file_diff", repo=SLUG, sha="--output=/tmp/x", path=path)
        finally:
            client.close()

    def test_working_tree(self) -> None:
        self.check_server(SCRIPT)

    def test_stable_copy(self) -> None:
        """A stabil másolat (`~/.git-graph/bin`) a lap fájljait is magával viszi."""
        module = load_module(self.home)
        module.install_copy(ROOT)
        stable = self.home / ".git-graph" / "bin" / "git-graph"
        for name in module.PAGE_FILES:
            self.assertTrue((self.home / ".git-graph" / "page" / name).is_file(), name)
        self.check_server(stable)

    def test_stable_copy_without_page(self) -> None:
        """Régi szerver frissítette a stabil másolatot lapfájlok nélkül: az új pótolja."""
        state = self.home / ".git-graph"
        stable = state / "bin" / "git-graph"
        stable.parent.mkdir()
        stable.write_bytes(SCRIPT.read_bytes())
        (state / ".claude-plugin").mkdir()
        manifest = ROOT / ".claude-plugin" / "plugin.json"
        (state / ".claude-plugin" / "plugin.json").write_bytes(manifest.read_bytes())
        version = json.loads(manifest.read_text(encoding="utf-8"))["version"]
        plugins = self.home / ".claude" / "plugins"
        plugins.mkdir(parents=True)
        (plugins / "installed_plugins.json").write_text(json.dumps({"version": 2, "plugins": {
            "git-graph@git-graph": [{"version": version, "installPath": str(ROOT)}]}}), encoding="utf-8")
        self.check_server(stable)
        self.assertTrue((state / "page" / "page.js").is_file())

    def test_dev_install(self) -> None:
        """A fejlesztői példány `+dev` verzióval kerül a stabil helyre, és nem frissít vissza."""
        module = load_module(self.home)
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink):
            self.assertEqual(module.dev_install(), 0)
        state = self.home / ".git-graph"
        version = json.loads((state / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertIn("+dev.", version)
        self.assertTrue((state / "page" / "page.js").is_file())
        self.check_server(state / "bin" / "git-graph")

    def test_dev_active(self) -> None:
        """A friss dev-példányt a hook nem írja felül, a lejártat igen."""
        module = load_module(self.home)
        manifest = self.home / ".git-graph" / ".claude-plugin" / "plugin.json"
        manifest.parent.mkdir(parents=True)
        for version, active in ((f"0.11.0+dev.{int(module.time.time())}", True),
                                (f"0.11.0+dev.{int(module.time.time()) - module.DEV_TTL - 60}", False),
                                ("0.11.0", False)):
            manifest.write_text(json.dumps({"version": version}), encoding="utf-8")
            self.assertEqual(module.dev_active(), active, version)

    def test_avatar_cache(self) -> None:
        """Gyorstárból jön a kép; friss bejegyzésre nem indul letöltés."""
        module = load_module(self.home)
        now = module.time.time()
        (self.home / ".git-graph" / "avatars.json").write_text(json.dumps({
            "a@x.hu": {"img": "data:image/png;base64,AAAA", "at": now},
            "b@x.hu": {"img": None, "at": now}}), encoding="utf-8")
        commits = [{"sha": "1" * 40, "email": "a@x.hu", "pushed": True},
                   {"sha": "2" * 40, "email": "b@x.hu", "pushed": True}]
        found = module.avatars_for(commits, "https://github.com/o/r")
        self.assertEqual(found, {"a@x.hu": "data:image/png;base64,AAAA"})
        self.assertEqual(module._AVATAR_JOBS, set())
        self.assertEqual(module.avatar_signal(), 1)
        self.assertEqual(module.avatars_for(commits, ""), {})          # nem GitHub-os repó

    def test_file_icon(self) -> None:
        """Fájlnév, a leghosszabb kiterjesztés, átnevezés; ismeretlenre az általános ikon."""
        module = load_module(self.home)
        cases = {"page/page.js": "javascript", "README.md": "readme", "app/x.spec.ts": "typescript-test",
                 "src/{a => b}/main.py": "python", "bin/git-graph": "_file", "LICENSE": "license"}
        for path, icon in cases.items():
            self.assertEqual(module.file_icon(path), icon, path)
        svg = module.file_icons()["icons"]["python"]
        self.assertIn("var(--ic-", svg)
        self.assertNotIn("--vscode-ctp", svg)

    def make_repo(self) -> tuple[Path, Path]:
        """Eldobható repó egy hozzáadott worktree-vel; mindkettőben változás."""
        root = self.home.resolve()                   # a git a valódi utat adja (/var → /private/var)
        main, extra = root / "repo", root / "repo-wt"
        run = lambda *a, cwd=main: subprocess.run(["git", *a], cwd=cwd, check=True,  # noqa: E731
                                                   capture_output=True)
        main.mkdir()
        run("init", "-q", "-b", "main")
        (main / "a.txt").write_text("egy\n", encoding="utf-8")
        run("add", ".")
        run("-c", "user.name=T", "-c", "user.email=t@x.hu", "commit", "-qm", "init")
        run("worktree", "add", "-q", "-b", "feat", str(extra))
        (extra / "b.txt").write_text("feat\n", encoding="utf-8")         # a feat előrébb jár
        run("add", ".", cwd=extra)
        run("-c", "user.name=T", "-c", "user.email=t@x.hu", "commit", "-qm", "feat", cwd=extra)
        run("switch", "-q", "-c", "side")                           # a fő checkout egy újabb ága
        (main / "c.txt").write_text("side\n", encoding="utf-8")
        run("add", ".")
        run("-c", "user.name=T", "-c", "user.email=t@x.hu", "commit", "-qm", "side")
        run("switch", "-q", "main")
        (main / "a.txt").write_text("kettő\n", encoding="utf-8")
        (extra / "uj.txt").write_text("új\n", encoding="utf-8")
        return main, extra

    def test_worktrees(self) -> None:
        """Közös adat: minden worktree HEAD-je és ál-sora, a diff a saját mappájából."""
        main, extra = self.make_repo()
        module = load_module(self.home)
        module.REPO = module.main_checkout(extra)
        self.assertEqual(module.REPO, main)
        data = module.collect_payload(None)
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
        for c in pending:
            path = data["stats"][c["sha"]]["files"][0]["path"]
            self.assertTrue(module.file_diff(c["sha"], path)["hunks"], c["sha"])
        with self.assertRaises(ValueError):
            module.file_diff("*uncommitted:nincs-ilyen-000000", "a.txt")

    def test_remote_head(self) -> None:
        """Az `origin/HEAD` nem külön badge: a célja (`origin/main`) kapja a `default` jelet."""
        main, _ = self.make_repo()
        clone = main.parent / "clone"
        subprocess.run(["git", "clone", "-q", str(main), str(clone)], check=True, capture_output=True)
        module = load_module(self.home)
        module.REPO = clone
        data = module.collect_payload(None)
        self.assertEqual(data["meta"]["remotes"], ["origin"])
        refs = [r for c in data["commits"] for r in c["refs"]]
        self.assertFalse([r for r in refs if r["name"].endswith("/HEAD")])
        self.assertTrue(next(r for r in refs if r["name"] == "origin/main").get("default"))

    def test_focused_worktree(self) -> None:
        """A saját worktree a repóban dolgozó, legutóbb fókuszált desktop-sessioné."""
        main, extra = self.make_repo()
        module = load_module(self.home)
        folder = module.APP_SESSIONS / "acc" / "org"
        folder.mkdir(parents=True)

        def session(name: str, cwd: Path, focused: float, **more: object) -> None:
            data = {"cwd": str(cwd), "lastFocusedAt": focused * 1000, **more}
            (folder / f"local_{name}.json").write_text(json.dumps(data), encoding="utf-8")

        wts = module.worktree_list(main)
        self.assertEqual(module.focused_worktree(wts), {"worktree": None, "known": False})
        session("a", main, 100)
        session("b", extra / "sub", 200)
        session("c", self.home, 300)                                 # más repó: nem számít
        session("d", main, 400, isArchived=True)                     # archivált: nem számít
        self.assertEqual(module.focused_worktree(wts), {"worktree": module.slug_for(extra), "known": True})
        session("a", main, 500)                                      # visszaváltás a fő checkoutra
        os.utime(folder / "local_a.json", (1e9, 1e9))                # más mtime: újraolvassa
        self.assertEqual(module.focused_worktree(wts)["worktree"], module.slug_for(main))

        # Az app naplója a fájlnál előbb tudja a fókuszt; egy másodpercen belül a sorrend dönt.
        module.APP_LOG.parent.mkdir(parents=True)

        def focus(*ids: str, tail: str = "") -> None:
            with module.APP_LOG.open("a", encoding="utf-8") as f:
                for sid in ids:
                    f.write(f"2001-01-01 00:00:00 [info] [CCD] LocalSessions.setFocusedSession: sessionId={sid}\n")
                f.write(tail)

        focus("null", "local_b")
        self.assertEqual(module.focused_worktree(wts)["worktree"], module.slug_for(extra))
        focus("null", "local_a")
        self.assertEqual(module.focused_worktree(wts)["worktree"], module.slug_for(main))
        focus(tail="2001-01-01 00:00:00 [info] [CCD] LocalSessions.setFocusedSession: sessionId=local_b")
        self.assertEqual(module.focused_worktree(wts)["worktree"], module.slug_for(main))  # félbe írt sor
        focus(tail="\n")
        self.assertEqual(module.focused_worktree(wts)["worktree"], module.slug_for(extra))

        # A nyitva tartott hívás: a cursor óta jött váltásra azonnal, különben a határidőre válaszol.
        cursor = module.wait_focus("", 5)["cursor"]
        self.assertEqual(module.wait_focus(cursor, 0.1), {"switched": False, "cursor": cursor})
        focus("local_a")
        self.assertTrue(module.wait_focus(cursor, 5)["switched"])

    def test_worktree_stubs(self) -> None:
        """Saját commit és WIP nélküli worktree HEAD-je csonkot kap; a saját ág csúcsa nem."""
        module = load_module(self.home)
        commits = [{"sha": "c", "parents": ["a"], "refs": []},   # feat: saját ág
                   {"sha": "b", "parents": ["a"], "refs": []},   # trunk
                   {"sha": "a", "parents": [], "refs": []}]
        edges = module.assign_lanes(commits, "b")
        wt = lambda slug, head, main=False: {"slug": slug, "head": head, "main": main}  # noqa: E731
        module.worktree_stubs(commits, edges, [wt("m", "b", True), wt("feat", "c"), wt("old", "a")])
        self.assertNotIn("stubs", commits[0])
        self.assertNotIn("stubs", commits[1])
        self.assertEqual(commits[2]["stubs"], [{"lane": 2, "worktree": "old"}])

    def test_branch_tracks(self) -> None:
        """Ágankénti távolság: az alapághoz, az upstreamhez, és a remote-only ágnak a helyi párjához."""
        root = self.home.resolve()
        bare, repo = root / "remote.git", root / "work"
        git = lambda *a, cwd=repo: subprocess.run(["git", "-c", "user.name=T", "-c", "user.email=t@x.hu", *a],  # noqa: E731
                                                  cwd=cwd, check=True, capture_output=True)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
        repo.mkdir()
        git("init", "-q", "-b", "main")
        git("remote", "add", "origin", str(bare))
        git("commit", "-q", "--allow-empty", "-m", "init")
        git("push", "-q", "-u", "origin", "main")
        git("remote", "set-head", "origin", "main")
        git("switch", "-q", "-c", "feat")
        git("commit", "-q", "--allow-empty", "-m", "f1")
        git("push", "-q", "-u", "origin", "feat")
        git("commit", "-q", "--allow-empty", "-m", "f2")                 # egy pusholatlan
        git("push", "-q", "origin", "feat:only-remote")                 # remote-only ág
        git("switch", "-q", "main")
        git("commit", "-q", "--allow-empty", "-m", "anomália")           # a helyi main előreszalad
        module = load_module(self.home)
        module.REPO = repo
        tracks = module.branch_tracks(module.default_base())
        self.assertEqual(module.default_base(), "origin/main")
        self.assertEqual(tracks["feat"], {"up": [1, 0], "base": [2, 0]})
        self.assertEqual(tracks["main"], {"up": [1, 0]})              # az alapágnak nincs base-szakasza
        self.assertEqual(tracks["origin/feat"]["local"], [0, 1])       # a helyi feat egy committal előrébb
        self.assertEqual(tracks["origin/only-remote"], {"base": [2, 0]})
        self.assertEqual(tracks["origin/main"], {"local": [0, 1]})     # az alapág remote-ja: csak a helyi párjához

    def test_branch_owners(self) -> None:
        """Az ág a worktree-é, amelyikben utoljára ki volt véve (HEAD-reflog); a soha ki nem vett gazdátlan."""
        main, extra = self.make_repo()
        git_in(extra, "switch", "-q", "-c", "wt-side")                 # a worktree-ben létrehozva
        git_in(extra, "switch", "-q", "feat")
        git_in(main, "branch", "orphan")                               # sehol nem volt kivéve
        module = load_module(self.home)
        module.REPO = main
        wts = module.collect_worktrees()
        owners = module.branch_owners(wts)
        slug = {w["path"]: w["slug"] for w in wts}
        self.assertEqual(owners["main"], slug[main])
        self.assertEqual(owners["side"], slug[main])                   # a fő checkoutban járt
        self.assertEqual(owners["feat"], slug[extra])                  # ott van kivéve
        self.assertEqual(owners["wt-side"], slug[extra])
        self.assertNotIn("orphan", owners)
        branches = {b["name"]: b for b in module.collect_branches(wts)}
        self.assertEqual(branches["wt-side"]["owner"], slug[extra])
        self.assertIsNone(branches["orphan"]["owner"])

    def test_worktree_order(self) -> None:
        """A hozzáadott worktree-k a létrehozásuk sorrendjében, nem név szerint."""
        main, extra = self.make_repo()
        later = self.home.resolve() / "aaa-wt"                         # névben előrébb, de újabb
        time.sleep(0.05)
        git_in(main, "worktree", "add", "-q", "--detach", str(later))
        module = load_module(self.home)
        self.assertEqual([w["path"] for w in module.worktree_list(main)], [main, extra, later])

    def test_last_change(self) -> None:
        """A WIP-sor ideje: a commitolatlan fájlok legutóbbi mtime-ja; a törölt kimarad."""
        module = load_module(self.home)
        (self.home / "a.txt").write_text("x", encoding="utf-8")
        os.utime(self.home / "a.txt", (1000, 1000))
        files = [{"path": "a.txt"}, {"path": "torolt.txt"}]
        self.assertEqual(module.last_change(self.home, files), 1000)

    def test_app_worktree_branches(self) -> None:
        """A leválasztott worktree ága a Claude app nyilvántartásából, a mappa szerint."""
        module = load_module(self.home)
        self.assertEqual(module.app_worktree_branches(), {})
        module.APP_WORKTREES.parent.mkdir(parents=True, exist_ok=True)
        folder = self.home / "wt"
        module.APP_WORKTREES.write_text(json.dumps({"worktrees": {
            "wt": {"path": str(folder), "branch": "claude/wt"}, "rossz": {"path": 1}}}), encoding="utf-8")
        self.assertEqual(module.app_worktree_branches(), {str(folder.resolve()): "claude/wt"})

    def test_vanished_worktree(self) -> None:
        """A régi, worktree-nkénti lap a mappája megszűnése után rövid üzenetet kap."""
        state = self.home / ".git-graph"
        (state / "repos.json").write_text(json.dumps({SLUG: str(self.home / "nincs")}), encoding="utf-8")
        client = McpClient(SCRIPT, self.home)
        try:
            result = client.request("tools/call", {"name": "fingerprint",
                                                   "arguments": {"repo": SLUG}})["result"]
            self.assertTrue(result["isError"])
            self.assertIn("megszűnt", result["content"][0]["text"])
            self.assertNotIn("\n", result["content"][0]["text"])
        finally:
            client.close()

    def test_loader(self) -> None:
        """A betöltőbe a kontextus és a cím kerül, `</script>`-biztosan."""
        module = load_module(self.home)
        module.REPO = ROOT
        page = module.build("Git Graph </script>", "x</script>")
        self.assertNotIn("__CTX__", page)
        self.assertNotIn("__TITLE__", page)
        self.assertEqual(page.count("</script>"), 1)


if __name__ == "__main__":
    unittest.main()
