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

    def hook(self, cwd: Path, session: str = "s1", event: str | None = None, **env: str) -> str | None:
        payload = {"cwd": str(cwd), "session_id": session}
        if event:
            payload["hook_event_name"] = event
        out = self.run_script("--session-hook", stdin=json.dumps(payload), **env)
        self.assertEqual(out.returncode, 0, out.stderr)
        if not out.stdout:
            return None
        data = json.loads(out.stdout)["hookSpecificOutput"]
        self.assertEqual(data["hookEventName"], event or "SessionStart")
        return data["additionalContext"]

    def test_publish_then_open(self) -> None:
        """Nincs Artifact → publikálás; a session publikálása után → megnyitás, sessionönként egyszer."""
        main, extra = self.make_repo()
        context = self.hook(extra)                                   # worktree-ből is a fő checkout lapja
        self.assertIn("még nincs", context)
        self.assertIn(str(main), context)
        out = self.run_script(str(extra), "--published", "https://claude.ai/artifact/x")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(git_in(main, "config", "git-graph.artifact").strip(), "https://claude.ai/artifact/x")
        self.assertIn("nyisd meg EGYSZER", self.hook(main, session="s2"))
        self.assertIsNone(self.hook(extra, session="s2", event="PostToolUse"))   # worktree-váltás: már nyitva
        self.assertIn("nyisd meg", self.hook(main, session="s3", event="PostToolUse"))

    def test_quiet(self) -> None:
        """Nem repó, headless session és kikapcsolt publikálás: nincs kimenet."""
        self.assertIsNone(self.hook(self.home))
        repo = self.plain_repo()
        self.assertIsNone(self.hook(repo, CLAUDE_CODE_ENTRYPOINT="sdk-py"))
        (self.state / "no-auto-publish").touch()
        self.assertIsNone(self.hook(repo))
        registered = json.loads((self.state / "repos.json").read_text(encoding="utf-8")).values()
        self.assertIn(str(repo), registered)                          # csendben is regisztrál

    def test_installs_from_plugin(self) -> None:
        """A plugin hookja (CLAUDE_PLUGIN_ROOT = a kód gyökere) a stabil másolatot is kiteszi."""
        self.hook(self.home, CLAUDE_PLUGIN_ROOT=str(ROOT))
        self.assertTrue((self.state / "bin" / "git-graph").is_file())
        self.assertTrue((self.state / "page" / "page.js").is_file())

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
        self.assertIn("automatikus publikálás KI", forget.stdout)
        self.assertEqual(self.run_script("--artifacts").stdout, "")
        self.assertIn("usage", self.run_script(cwd=repo).stdout)
        self.assertIn("nem git repó", self.run_script().stderr)
