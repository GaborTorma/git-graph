"""A tesztek közös eszközei: kamu HOME, a csomag friss betöltése, eldobható repók, MCP-kliens.

Futtatás: `/usr/bin/python3 -m unittest discover -s tests` (csak stdlib).
A valódi `~/.git-graph`-hoz és az app configjához nem nyúlnak.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "bin" / "git-graph"
PYTHON = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else "python3"
SLUG = "test-repo"
GIT_USER = ["-c", "user.name=T", "-c", "user.email=t@x.hu"]


def git(*args: str) -> str:
    """Git a git-graph saját repójában (a working tree)."""
    return git_in(ROOT, *args)


def git_in(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *GIT_USER, "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout


def load(home: Path):
    """A `git_graph` csomag frissen, kamu HOME-mal (a HOME-ra épülő utak betöltéskor rögzülnek).

    Minden modul újra betöltődik — a modulszintű állapot (gyorstárak, `REPO`)
    tesztenként tiszta.
    """
    for name in [n for n in sys.modules if n == "git_graph" or n.startswith("git_graph.")]:
        del sys.modules[name]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    old = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        importlib.import_module("git_graph.cli")           # minden modult behúz
        return sys.modules["git_graph"]
    finally:
        if old is not None:
            os.environ["HOME"] = old


class HomeTestCase(unittest.TestCase):
    """Kamu HOME (`self.home`), benne a regiszterrel: `SLUG` → a git-graph working tree-je."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve()       # a git a valódi utat adja (/var → /private/var)
        self.state = self.home / ".git-graph"
        self.state.mkdir()
        (self.state / "repos.json").write_text(json.dumps({SLUG: str(ROOT)}), encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def load(self):
        return load(self.home)

    def make_repo(self) -> tuple[Path, Path]:
        """Eldobható repó egy hozzáadott worktree-vel; mindkettőben változás.

        `main`: a fő checkout (`main` ág, egy újabb `side` ággal), `extra`: a
        hozzáadott worktree (`feat` ág, egy committal előrébb).
        """
        main, extra = self.home / "repo", self.home / "repo-wt"
        main.mkdir()
        git_in(main, "init", "-q", "-b", "main")
        (main / "a.txt").write_text("egy\n", encoding="utf-8")
        git_in(main, "add", ".")
        git_in(main, "commit", "-qm", "init")
        git_in(main, "worktree", "add", "-q", "-b", "feat", str(extra))
        (extra / "b.txt").write_text("feat\n", encoding="utf-8")
        git_in(extra, "add", ".")
        git_in(extra, "commit", "-qm", "feat")
        git_in(main, "switch", "-q", "-c", "side")
        (main / "c.txt").write_text("side\n", encoding="utf-8")
        git_in(main, "add", ".")
        git_in(main, "commit", "-qm", "side")
        git_in(main, "switch", "-q", "main")
        (main / "a.txt").write_text("kettő\n", encoding="utf-8")
        (extra / "uj.txt").write_text("új\n", encoding="utf-8")
        return main, extra

    def plain_repo(self, name: str = "plain") -> Path:
        """Egycommitos repó, worktree nélkül."""
        repo = self.home / name
        repo.mkdir()
        git_in(repo, "init", "-q", "-b", "main")
        (repo / "a.txt").write_text("1\n", encoding="utf-8")
        git_in(repo, "add", "a.txt")
        git_in(repo, "commit", "-qm", "init")
        return repo


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
