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
