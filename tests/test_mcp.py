"""Füstteszt: a `git-graph --mcp` stdio-n, kamu HOME-mal — ahogy az app indítja (`mcp`).

A working tree belépőjét, a stabil másolatot (zip), a fejlesztői példányt és a
0.12.x-ről örökölt stabil belépőt is elindítja.
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess

from helpers import PYTHON, ROOT, SCRIPT, SLUG, HomeTestCase, McpClient, git


class McpServerTest(HomeTestCase):
    def check_server(self, script) -> None:
        client = McpClient(script, self.home)
        try:
            init = client.request("initialize", {"protocolVersion": "2025-06-18"})["result"]
            self.assertEqual(init["serverInfo"]["name"], "git-graph")
            tools = {t["name"]: t for t in client.request("tools/list")["result"]["tools"]}
            self.assertEqual(set(tools), {"changes", "graph_data", "file_diff", "page_code"})
            self.assertTrue(all(t["annotations"]["readOnlyHint"] for t in tools.values()))
            self.assertEqual(client.request("ping")["result"], {})

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
            changes = client.call("changes", repo=SLUG)
            self.assertTrue({"state", "since", "focus", "version"} <= set(changes))
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
        """A stabil másolat (`~/.git-graph/bin`, egy zip) a lap fájljait is magával viszi."""
        gg = self.load()
        gg.install.install_copy(ROOT)
        for name in gg.page.PAGE_FILES:
            self.assertTrue((self.state / "page" / name).is_file(), name)
        stable = self.state / "bin" / "git-graph"
        self.assertTrue(os.access(stable, os.X_OK))
        self.check_server(stable)

    def test_dev_install(self) -> None:
        """A fejlesztői példány `+dev` verzióval kerül a stabil helyre, és nem frissít vissza."""
        gg = self.load()
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink):
            self.assertEqual(gg.install.dev_install(), 0)
        version = json.loads((self.state / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertIn("+dev.", version)
        self.assertTrue((self.state / "page" / "page.js").is_file())
        self.check_server(self.state / "bin" / "git-graph")

    def test_legacy_stable_entry(self) -> None:
        """0.12.x-ről frissítve a régi szerver csak a belépőt másolja a stabil helyre: az a
        csomagot a telepített pluginból tölti be."""
        bin_dir = self.state / "bin"
        bin_dir.mkdir()
        shutil.copy2(SCRIPT, bin_dir / "git-graph")
        shutil.copytree(ROOT / "page", self.state / "page")
        self.registry({"git-graph@git-graph": [{"version": "0", "installPath": str(ROOT)}]})
        self.check_server(bin_dir / "git-graph")
        self.registry({})                                   # nincs plugin: érthető hiba, nem nyers kivétel
        out = subprocess.run([PYTHON, str(bin_dir / "git-graph"), "--help"], capture_output=True, text=True,
                             env={**os.environ, "HOME": str(self.home)})
        self.assertIn("a git_graph csomag nem található", out.stderr)
        self.assertNotIn("Traceback", out.stderr)

    def test_vanished_repo(self) -> None:
        """A regiszterben lévő, de eltűnt repó: rövid hiba, nem nyers git-kivétel."""
        self.set_repos({SLUG: str(self.home / "nincs")})
        client = McpClient(SCRIPT, self.home)
        try:
            result = client.request("tools/call", {"name": "changes",
                                                   "arguments": {"repo": SLUG}})["result"]
            self.assertTrue(result["isError"])
            self.assertIn("nem létezik", result["content"][0]["text"])
            self.assertNotIn("\n", result["content"][0]["text"])
        finally:
            client.close()

    def test_errors(self) -> None:
        """Ismeretlen repó, tool és metódus: hiba-eredmény, a szerver él tovább."""
        client = McpClient(SCRIPT, self.home)
        try:
            unknown = client.request("tools/call", {"name": "graph_data", "arguments": {"repo": "nincs"}})
            self.assertIn("ismeretlen repó", unknown["result"]["content"][0]["text"])
            tool = client.request("tools/call", {"name": "nincs", "arguments": {"repo": SLUG}})
            self.assertTrue(tool["result"]["isError"])
            method = client.request("nincs/ilyen")
            self.assertEqual(method["error"]["code"], -32601)
            self.assertEqual(client.request("ping")["result"], {})
        finally:
            client.close()


class ShortErrorTest(HomeTestCase):
    def test_short_error(self) -> None:
        """A git-hiba a lap láblécének: alparancs + az első hibasor, a repó útja nélkül."""
        gg = self.load()
        exc = subprocess.CalledProcessError(128, ["git", "--no-optional-locks", "-C", "/x/y", "log", "-1"],
                                            stderr="\nfatal: bad revision\nmásik sor\n")
        self.assertEqual(gg.mcp.short_error(exc), "git log: fatal: bad revision")
        self.assertEqual(gg.mcp.short_error(subprocess.CalledProcessError(2, "git")), "git git: kilépési kód 2")
