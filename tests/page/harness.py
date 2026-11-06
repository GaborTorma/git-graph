"""A lap viselkedési tesztjeinek közös eszközei: fixture-repó, valódi MCP-szerver, headless böngésző.

A lap ugyanúgy töltődik be, mint az appban: a `page/loader.html` betöltő a kamu
`window.claude` MCP-klienstől kéri a `page_code`-ot, és elindítja a lapot. A kamu
kliens a hívásokat a gépen futó `git-graph --mcp`-nek adja tovább (`McpClient`,
eldobható repóval, kamu HOME-mal) — a `page_code`, a `graph_data` és a `file_diff`
a valódi kimenet. A nyitva tartott `changes` hívás (`wait > 0`) a lapon függ, amíg
a lap meg nem szakítja: a teszt alatt a repó nem változik.

Futtatás (a Playwright és a pytest fejlesztői eszköz, a repóba nem kerül függőség). A
tesztek párhuzamosan futnak (`worksteal`): egy osztály tesztjei egy blokkban indulnak, és a
szabad worker átvesz a lemaradótól, így egy nagy osztály sem lesz kritikus út. Egy osztály így
több workeren is elindulhat, ezért a `setUpClass` olcsó: a fixture-történet workerenként egyszer
épül fel (osztályonként másolat), a Chromium workerenként egyszer indul (`browser()`). Az
osztályok függetlenek: saját kamu HOME, fixture-repó, MCP-szerver, tesztenként saját context.
  uvx --from playwright==1.63.0 playwright install chromium-headless-shell
  uv run --no-project --with playwright==1.63.0 --with pytest==9.0.3 --with pytest-xdist==3.8.0 python -m pytest tests/page -n auto --dist worksteal -q -p no:cacheprovider
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
# oldalra megy (`__mcp`); a nyitva tartott `changes` megszakításig függ, vagy amíg a teszt
# `__poke()`-kal meg nem válaszoltatja (a repó külső változása: `PageTestCase.poke`).
#
# A `settle` nyugalmi feltétele (`window.__quiet`): nincs futó véges animáció, folyamatban lévő
# MCP-hívás, legfeljebb `SHORT_TIMER` ms-os függő időzítő (a lap rövid késleltetései: a WIP-réteg
# újraalapozása, a „másolva” jel), és `ms` óta nem változott a DOM, nem görgetett semmi (a `glide`
# rAF-fel görget, a méretfigyelők a képkockában írnak). A hosszabb időzítőt (súgó, mentés) a
# teszt maga várja ki.
SHORT_TIMER = 250
FAKE_CLAUDE = r"""
let inflight = 0, changed = performance.now();
const bump = () => { changed = performance.now(); };
const timers = new Set(), setT = window.setTimeout, clearT = window.clearTimeout;
window.setTimeout = (fn, ms = 0, ...rest) => {
  if (ms > __SHORT__ || typeof fn !== 'function') return setT(fn, ms, ...rest);
  const id = setT((...a) => { timers.delete(id); bump(); fn(...a); }, ms, ...rest);
  timers.add(id);
  return id;
};
window.clearTimeout = id => { timers.delete(id); clearT(id); };
new MutationObserver(bump).observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
addEventListener('scroll', bump, true);
window.__quiet = ms => !inflight && !timers.size && performance.now() - changed >= ms
  && !document.getAnimations().some(a => a.playState !== 'finished' && a.effect?.getComputedTiming().endTime !== Infinity);
const mcp = (tool, args) => {
  inflight++;
  bump();
  return window.__mcp(tool, args).finally(() => { inflight--; bump(); });
};
const waiting = [];
window.__poke = () => waiting.splice(0).forEach(go => go());
window.claude = { use: async name => name !== 'mcp' ? null : {
  callTool: (server, tool, args, opts = {}) => {
    if (tool === 'changes' && args.wait > 0) {
      return new Promise((resolve, reject) => {
        opts.signal?.addEventListener('abort',
          () => reject(Object.assign(new Error('aborted'), { name: 'AbortError' })));
        waiting.push(() => mcp(tool, { ...args, wait: 0 }).then(r => resolve({ payload: JSON.parse(r).value })));
      });
    }
    return mcp(tool, args).then(r => {
      const { ok, value } = JSON.parse(r);
      if (!ok) throw Object.assign(new Error(value), { code: 'tool_error' });
      return { payload: value };
    });
  },
} };
""".replace("__SHORT__", str(SHORT_TIMER))


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

_shared: dict = {}


def history_copy(repo: Path) -> None:
    """A fixture-történet másolata a `repo` helyére: a `make_history` workerenként egyszer fut
    (~1,3 s), a másolás ~40 ms."""
    if "history" not in _shared:
        tmp = tempfile.TemporaryDirectory()
        atexit.register(tmp.cleanup)
        _shared["history"] = Path(tmp.name).resolve() / "repo"
        make_history(_shared["history"])
    shutil.copytree(_shared["history"], repo, symlinks=True)


def browser():
    """A worker közös Chromiuma: első kéréskor indul, a folyamat végén áll le. A tesztek
    saját contextet nyitnak, így egymástól függetlenek maradnak."""
    if "browser" not in _shared:
        pw = sync_playwright().start()
        _shared["browser"] = pw.chromium.launch()
        atexit.register(pw.stop)
        atexit.register(_shared["browser"].close)
    return _shared["browser"]


class PageTestCase(unittest.TestCase):
    """Osztályonként egy fixture-repó és MCP-szerver; tesztenként új context és lap (a worker közös Chromiumában)."""

    page: Page
    WIDTH, HEIGHT = 900, 700
    COLOR_SCHEME = "light"     # a rendszer témája (`prefers-color-scheme`)
    INIT = ""                  # a kamu Claude app után futó saját init-szkript (pl. a host-híd hibái)
    QUIET = True               # a `settle` a nyugalomra vár; False: a lap sosem nyugszik meg, fix 250 ms

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        home = Path(cls.tmp.name).resolve()
        (home / ".git-graph").mkdir()
        repo = home / "repo"
        history_copy(repo)
        cls.repo = repo
        cls.prepare(repo)
        (home / ".git-graph" / "repos.json").write_text(json.dumps({SLUG: str(repo)}), encoding="utf-8")
        cls.client = McpClient(SCRIPT, home)
        ctx = {"slug": SLUG, "repo": "fixture", "server": "host:git-graph", "api": 1}
        cls.html = ((ROOT / "page" / "loader.html").read_text(encoding="utf-8")
                    .replace("__CTX__", json.dumps(ctx)).replace("__TITLE__", "fixture"))
        cls.browser = browser()

    SUBJECT = ""               # a `commit_versions` témája: az `open_file` ennek a változatát nyitja

    @classmethod
    def prepare(cls, repo: Path) -> None:
        """Az osztály saját kiegészítése a fixture-történethez (alapból semmi)."""

    def open_file(self, name: str) -> None:
        """A `commit_versions` módosító commitjában a `name` fájl diffje (a commit nyitva marad)."""
        row = self.page.locator("#rows .row", has_text=f"{self.SUBJECT}: módosítva")
        if row.get_attribute("aria-expanded") != "true":
            row.click()
            self.settle()
        self.page.locator("#rows .details .file", has_text=name).click()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()
        cls.tmp.cleanup()

    def mcp(self, tool: str, args: dict) -> str:
        try:
            return json.dumps({"ok": True, "value": self.client.call(tool, **args)})
        except AssertionError as e:                # a tool hibát adott (isError)
            return json.dumps({"ok": False, "value": str(e)})

    def setUp(self) -> None:
        self.context = self.browser.new_context(viewport={"width": self.WIDTH, "height": self.HEIGHT},
                                                locale="hu-HU", timezone_id="Europe/Budapest",
                                                color_scheme=self.COLOR_SCHEME)
        self.context.set_default_timeout(5000)   # egy elakadt várakozás 5 s után bukik, nem 30 s után
        self.page = self.context.new_page()
        self.errors: list[str] = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.expose_function("__mcp", self.mcp)
        self.page.add_init_script(FAKE_CLAUDE + self.INIT)
        self.page.route(URL, lambda route: route.fulfill(
            content_type="text/html", headers={"Content-Security-Policy": CSP}, body=self.html))
        self.page.goto(URL)
        self.page.wait_for_selector("#rows .row")
        self.settle()

    def tearDown(self) -> None:
        self.context.close()
        self.assertEqual(self.errors, [], "JS-hiba a lapon")

    def settle(self) -> None:
        """Kivárja, amíg a lap megnyugszik (`window.__quiet`, a `FAKE_CLAUDE` fölött): animációk,
        MCP-hívások, rövid időzítők, és 50 ms (3 képkocka) DOM- és görgetésváltozás nélkül. A
        végtelen animáció (az élő-jel pulzálása) és a befejezett (a csukott diff `fill`-es
        animációja) nem számít. Utána még két képkocka: a méretfigyelők köre."""
        if self.QUIET:
            self.page.wait_for_function("window.__quiet(50)")
        else:
            self.page.wait_for_function("window.__quiet(0)")    # csak az animációk, hívások, időzítők
            self.page.wait_for_timeout(250)
        self.page.evaluate("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")

    def until(self, check, what: str = "a feltétel", timeout: float = 5.0) -> None:
        """Python-oldali feltételre vár (pl. a lemez tartalma), 50 ms-onként, legfeljebb `timeout`
        s-ig. A várakozás a lapon fut (`wait_for_timeout`): közben a lap MCP-hívásai is válaszolnak."""
        end = time.monotonic() + timeout
        while not check():
            if time.monotonic() > end:
                self.fail(f"{timeout} s alatt sem teljesült: {what}")
            self.page.wait_for_timeout(50)

    def poke(self) -> None:
        """A nyitva tartott `changes` hívás most válaszol: a lap az élő frissítést futtatja."""
        self.page.evaluate("window.__poke()")
        self.settle()

    def resize(self, width: int) -> None:
        self.page.set_viewport_size({"width": width, "height": self.HEIGHT})
        self.settle()
