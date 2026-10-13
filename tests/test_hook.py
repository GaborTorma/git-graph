"""A plugin hookja (`hook`) és a parancssor (`cli`) — alfolyamatként, kamu HOME-mal."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from helpers import PYTHON, ROOT, SCRIPT, HomeTestCase, git_in


class HookTest(HomeTestCase):
    def run_script(self, *args: str, stdin: str = "", cwd: Path | None = None, **env: str):
        base = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_PLUGIN_ROOT", "CLAUDE_CODE_ENTRYPOINT")}
        return subprocess.run([PYTHON, str(SCRIPT), *args], input=stdin, capture_output=True, text=True,
                              cwd=cwd or self.home, env={**base, "HOME": str(self.home), **env})

    def hook(self, cwd: Path, session: str = "s1", **env: str) -> str | None:
        payload = {"cwd": str(cwd), "session_id": session}
        out = self.run_script("--session-hook", stdin=json.dumps(payload), **env)
        self.assertEqual(out.returncode, 0, out.stderr)
        if not out.stdout:
            return None
        data = json.loads(out.stdout)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], "SessionStart")
        return data["additionalContext"]

    def open_url(self, cwd: Path, session: str | None, **env: str) -> str:
        out = self.run_script(str(cwd), "--open-url", *(["--session", session] if session else []), **env)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout.strip()

    def test_publish_then_open(self) -> None:
        """Nincs Artifact → a hook publikáltat; utána a mod nyit (`--open-url`), sessionönként egyszer."""
        main, extra = self.make_repo()
        context = self.hook(extra)                                   # worktree-ből is a fő checkout lapja
        self.assertIn("még nincs", context)
        self.assertIn(str(main), context)
        self.assertEqual(self.open_url(extra, "s1"), "")              # publikálandó: a session nyitja meg
        out = self.run_script(str(extra), "--published", "https://claude.ai/artifact/x")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(git_in(main, "config", "git-graph.artifact").strip(), "https://claude.ai/artifact/x")
        self.assertEqual(self.open_url(main, "s1"), "")               # a publikáló session már nyitotta
        self.assertIsNone(self.hook(main, session="s2"))              # naprakész: a hook hallgat
        self.assertEqual(self.open_url(main, "s2"), "https://claude.ai/artifact/x")
        self.assertEqual(self.open_url(extra, "s2"), "")              # a repó másik worktree-je: már nyitva
        self.assertEqual(self.open_url(main, "s3", CLAUDE_CODE_ENTRYPOINT="sdk-py"), "")
        self.assertEqual(self.open_url(self.home, "s3"), "")          # nem repó

    def test_quiet(self) -> None:
        """Nem repó, headless session és kikapcsolt megnyitás: nincs kimenet."""
        self.assertIsNone(self.hook(self.home))
        repo = self.plain_repo()
        self.assertIsNone(self.hook(repo, CLAUDE_CODE_ENTRYPOINT="sdk-py"))
        git_in(repo, "config", "git-graph.autoOpen", "false")
        self.assertIsNone(self.hook(repo))
        self.assertIsNotNone(self.hook(self.plain_repo("other")))          # a többi repóban kér
        registered = json.loads((self.state / "repos.json").read_text(encoding="utf-8")).values()
        self.assertIn(str(repo), registered)                          # csendben is regisztrál

    def test_settings(self) -> None:
        """Kikapcsolt automatikus publikálás: új Artifactot nem kér, a meglévőt frissíti;
        kikapcsolt megnyitás: a mod nem nyit, és a hook nem frissít."""
        (self.state).mkdir(parents=True, exist_ok=True)
        (self.state / "settings.json").write_text('{"autoPublish": false}', encoding="utf-8")
        repo = self.plain_repo()
        self.assertIsNone(self.hook(repo))
        self.run_script("--publish", cwd=repo)
        self.run_script(str(repo), "--published", "https://claude.ai/artifact/x")
        git_in(repo, "config", "git-graph.artifactHash", "elavult")
        self.assertIn("elavult", self.hook(repo, session="s2"))     # a meglévőt frissíti
        git_in(repo, "config", "git-graph.autoOpen", "false")
        self.assertIsNone(self.hook(repo, session="s3"))
        self.run_script(str(repo), "--published", "https://claude.ai/artifact/x")
        self.assertEqual(self.open_url(repo, "s4"), "")             # naprakész, de nem nyílik meg

    def test_open_url_for_skill(self) -> None:
        """Session nélkül (a skillé): a beállítástól függetlenül URL, elavultnál frissítés, Artifact nélkül semmi."""
        repo = self.plain_repo()
        self.assertEqual(self.open_url(repo, None), "")
        self.run_script("--publish", cwd=repo)
        self.run_script(str(repo), "--published", "https://claude.ai/artifact/x")
        git_in(repo, "config", "git-graph.autoOpen", "false")
        self.assertEqual(self.open_url(repo, None), "https://claude.ai/artifact/x")
        git_in(repo, "config", "git-graph.artifactHash", "elavult")
        self.assertTrue(self.open_url(repo, None).startswith('PUBLIKÁLD: 1) Artifact, action: "read"'))

    def test_installs_from_plugin(self) -> None:
        """A plugin hookja (CLAUDE_PLUGIN_ROOT = a kód gyökere) a stabil másolatot is kiteszi."""
        self.hook(self.home, CLAUDE_PLUGIN_ROOT=str(ROOT))
        self.assertTrue((self.state / "bin" / "git-graph").is_file())
        self.assertTrue((self.state / "page" / "js" / "main.js").is_file())

    def test_cli(self) -> None:
        """--publish, --artifacts, --forget és a hibás URL."""
        self.set_repos({})                                            # csak a kamu repó
        repo = self.plain_repo()
        publish = self.run_script("--publish", cwd=repo)
        self.assertTrue(publish.stdout.startswith("PUBLIKÁLD: "), publish.stdout)
        self.assertIn("HIBA", self.run_script(str(repo), "--published", "http://x").stderr)
        self.run_script(str(repo), "--published", "https://claude.ai/artifact/x")
        self.assertIn("naprakész", self.run_script("--publish", cwd=repo).stdout)
        self.assertEqual(self.run_script("--artifacts").stdout, f"{repo}\thttps://claude.ai/artifact/x\n")
        forget = self.run_script(str(repo), "--forget")
        self.assertIn("automatikus megnyitás KI", forget.stdout)
        self.assertEqual(self.run_script("--artifacts").stdout, "")
        self.assertIn("usage", self.run_script(cwd=repo).stdout)
        self.assertIn("nem git repó", self.run_script().stderr)
