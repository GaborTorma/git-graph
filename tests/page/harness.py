"""A lap viselkedési tesztjeinek közös eszközei: fixture-repó, valódi MCP-szerver, headless böngésző.

A lap ugyanúgy töltődik be, mint az appban: a `page/loader.html` betöltő a kamu
`window.claude` MCP-klienstől kéri a `page_code`-ot, és elindítja a lapot. A kamu
kliens a hívásokat a gépen futó `git-graph --mcp`-nek adja tovább (`McpClient`,
eldobható repóval, kamu HOME-mal) — a `page_code`, a `graph_data` és a `file_diff`
a valódi kimenet. A nyitva tartott `changes` hívás (`wait > 0`) a lapon függ, amíg
a lap meg nem szakítja: a teszt alatt a repó nem változik.

Futtatás (a Playwright fejlesztői eszköz, a repóba nem kerül függőség):
  uvx --from playwright==1.63.0 playwright install chromium-headless-shell
  uv run --no-project --with playwright==1.63.0 python -m unittest discover -s tests/page
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from helpers import ROOT, SCRIPT, McpClient  # noqa: E402

from playwright.sync_api import Page, sync_playwright  # noqa: E402

SLUG = "fixture"
URL = "https://git-graph.test/"
DAY = 86400
T0 = 1_780_000_000          # 2026 májusa; a commitok napjai innen előre

# A kamu Claude app: `window.claude.use('mcp')` → a host-híd. A hívás a Python
# oldalra megy (`__mcp`); a nyitva tartott `changes` megszakításig függ.
FAKE_CLAUDE = r"""
window.claude = { use: async name => name !== 'mcp' ? null : {
  callTool: (server, tool, args, opts = {}) => {
    if (tool === 'changes' && args.wait > 0) {
      return new Promise((_, reject) => opts.signal?.addEventListener('abort',
        () => reject(Object.assign(new Error('aborted'), { name: 'AbortError' }))));
    }
    return window.__mcp(tool, args).then(r => {
      const { ok, value } = JSON.parse(r);
      if (!ok) throw Object.assign(new Error(value), { code: 'tool_error' });
      return { payload: value };
    });
  },
} };
"""


def git_in(repo: Path, *args: str, env: dict | None = None) -> None:
    """Git a fixture-repóban, a teszt szerzőjével."""
    subprocess.run(["git", "-c", "user.name=Teszt Elek", "-c", "user.email=teszt@x.hu", "-C", str(repo), *args],
                   check=True, capture_output=True, env=env)


def commit_versions(repo: Path, files: dict, subject: str) -> None:
    """Két commit a `files` két változatával ({név: (régi, új)}; `None`: abban nincs): a régi
    a `subject`, az új a `<subject>: módosítva` üzenettel (`PageTestCase.open_file`)."""
    for side, msg in ((0, subject), (1, f"{subject}: módosítva")):
        for name, versions in files.items():
            if versions[side] is not None:
                (repo / name).write_text(versions[side], encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", msg)


def make_history(repo: Path) -> None:
    """Fixture-történet: 5 nap, naponta 6 commit a `main`-en, egy beolvasztott ág, és a
    HEAD-en sok, hosszú nevű ref (a badge-es sor tördelődéséhez)."""
    n = 0

    def git(*args: str, day: int = 0) -> None:
        nonlocal n
        n += 1
        date = f"@{T0 + day * DAY + n * 60} +0000"
        git_in(repo, *args, env={**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})

    def commit(name: str, day: int) -> None:
        (repo / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        git("add", ".", day=day)
        git("commit", "-qm", f"{name}: egy commit a fixture-ből", day=day)

    repo.mkdir()
    git("init", "-q", "-b", "main")
    for day in range(5):
        for k in range(6):
            commit(f"main-{day}-{k}", day)
            if (day, k) == (1, 2):
                git("switch", "-q", "-c", "feature/egy-nagyon-hosszu-ag-nev-a-badge-ekhez", day=day)
                for j in range(3):
                    commit(f"feat-{j}", day)
                git("switch", "-q", "main", day=day)
            if (day, k) == (2, 1):
                git("merge", "-q", "--no-ff", "-m", "Merge: a feature ág",
                    "feature/egy-nagyon-hosszu-ag-nev-a-badge-ekhez", day=day)
    for ref in ("release/2026-oszi-kiadas-hosszu-nevvel", "hotfix/meg-egy-hosszu-ag-nev"):
        git("branch", ref)
    for tag in ("v1.0.0", "v1.1.0-release-candidate-1"):
        git("tag", tag)

# Az Artifact CSP-jének mért része (.claude/memory/artifact-csp.md): a lap blobból futtat
# (modulok, Mermaid), inline `<style>`-t ír; a CDN-lista itt nem kell.
CSP = "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:; style-src 'self' 'unsafe-inline'"


class PageTestCase(unittest.TestCase):
    """Osztályonként egy fixture-repó, MCP-szerver és böngésző; tesztenként új lap."""

    page: Page
    WIDTH, HEIGHT = 900, 700

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        home = Path(cls.tmp.name).resolve()
        (home / ".git-graph").mkdir()
        repo = home / "repo"
        make_history(repo)
        cls.prepare(repo)
        (home / ".git-graph" / "repos.json").write_text(json.dumps({SLUG: str(repo)}), encoding="utf-8")
        cls.client = McpClient(SCRIPT, home)
        ctx = {"slug": SLUG, "repo": "fixture", "server": "host:git-graph", "api": 1}
        cls.html = ((ROOT / "page" / "loader.html").read_text(encoding="utf-8")
                    .replace("__CTX__", json.dumps(ctx)).replace("__TITLE__", "fixture"))
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    SUBJECT = ""               # a `commit_versions` témája: az `open_file` ennek a változatát nyitja

    @classmethod
    def prepare(cls, repo: Path) -> None:
        """Az osztály saját kiegészítése a fixture-történethez (alapból semmi)."""

    def open_file(self, name: str) -> None:
        """A `commit_versions` módosító commitjában a `name` fájl diffje."""
        self.page.locator("#rows .row", has_text=f"{self.SUBJECT}: módosítva").click()
        self.settle()
        self.page.locator("#rows .details .file", has_text=name).click()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.pw.stop()
        cls.client.close()
        cls.tmp.cleanup()

    def mcp(self, tool: str, args: dict) -> str:
        try:
            return json.dumps({"ok": True, "value": self.client.call(tool, **args)})
        except AssertionError as e:                # a tool hibát adott (isError)
            return json.dumps({"ok": False, "value": str(e)})

    def setUp(self) -> None:
        self.context = self.browser.new_context(viewport={"width": self.WIDTH, "height": self.HEIGHT},
                                                locale="hu-HU", timezone_id="Europe/Budapest")
        self.page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.expose_function("__mcp", self.mcp)
        self.page.add_init_script(FAKE_CLAUDE)
        self.page.route(URL, lambda route: route.fulfill(
            content_type="text/html", headers={"Content-Security-Policy": CSP}, body=self.html))
        self.page.goto(URL)
        self.page.wait_for_selector("#rows .row")
        self.settle()

    def tearDown(self) -> None:
        self.context.close()
        self.assertEqual(self.errors, [], "JS-hiba a lapon")

    def settle(self) -> None:
        """Kivárja az animációkat (a `glide` görgetése rAF-fel fut: annak az ideje is) és a
        méretfigyelők körét (két képkocka). A végtelen animáció (az élő-jel pulzálása) nem számít."""
        self.page.wait_for_function(
            "!document.getAnimations().some(a => a.effect?.getComputedTiming().endTime !== Infinity)")
        self.page.wait_for_timeout(250)
        self.page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

    def resize(self, width: int) -> None:
        self.page.set_viewport_size({"width": width, "height": self.HEIGHT})
        self.settle()
