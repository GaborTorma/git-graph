"""Git Graph-szerű, élő commit-gráf bármelyik repóból — Artifactként a Claude appban.

A VS Code `mhutchie.git-graph` extension gráfját követi, a Claude app
megjelenésével: bal oldalon sávokra osztott, színes commit-gráf, mellette
napokra bontva egysoros commitok ref-badge-ekkel; a soron kattintva lefelé
nyíló commit-részletek, szintaxisszínezett diffel.

Az Artifact lapjában nincs adat: a Claude appban megnyitva a gépen futó
`git-graph --mcp`-ből kéri (a Claude app host-hídján át). Kétmásodpercenként olcsó
ujjlenyomatot kér, és csak tényleges változásra tölt új adatot. A lapot a
plugin modja publikálja a session indulásakor: ha még nincs, vagy a sablonja (a
git-graph kódja), a capability-listája vagy a contractja változott. Kézzel: a mod
`/git-graph` commandja.

    git-graph --published <URL>          # a publikálás után: URL + hash a .git/config-ba
    git-graph --artifacts                # az ismert repók Artifactjai

A lapok a repón KÍVÜL keletkeznek (`~/.git-graph/<slug>/`) — a projektmappában
nincs mit ignorálni.

Telepítés: Claude Code plugin (`claude plugin install git-graph@git-graph`).
Az első session hookja beállítja a többit: a stabil másolatot
(`~/.git-graph/bin`) és a Claude app MCP-configját. Függősége nincs a Python 3
stdliben túl; minden git-hívás csak olvas. Hálózatra csak a szerzők
GitHub-avatarjáért megy (háttérben, gyorstárazva: `~/.git-graph/avatars.json`).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .gitio import git, main_checkout, remember_artifact, repo_name, resolve_repo, set_repo
from .hook import mod_plan, session_hook
from .install import dev_install
from .mcp import mcp_serve
from .publish import mark_published
from .registry import forget, list_artifacts, register


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Git Graph-szerű, élő commit-gráf Artifactként a Claude appban.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("repo", nargs="?", default=".",
                    help="a repó (bármelyik könyvtára); alap: az aktuális")
    ap.add_argument("--limit", type=int, default=0,
                    help="a --mcp graph_data-ja legfeljebb ennyi commitot ad "
                         "(0 = a teljes history, ez az alap)")
    ap.add_argument("--set-artifact", metavar="URL", default=None,
                    help="a repóhoz tartozó Artifact URL kézi megjegyzése")
    ap.add_argument("--artifacts", action="store_true",
                    help="az ismert repók Artifactjai, soronként: <repó>\\t<URL> "
                         "(a /git-graph:artifact-forget ebből dolgozik)")
    ap.add_argument("--forget", action="store_true",
                    help="a repó git-graph nyomainak törlése (.git/config kulcsok, "
                         "helyi lap, regiszter) és az automatikus megnyitás "
                         "kikapcsolása — az Artifactot nem törli")
    ap.add_argument("--published", metavar="URL", default=None,
                    help="a mod publikálása után: az URL és a lap hashe a .git/config-ba")
    ap.add_argument("--mcp", action="store_true",
                    help="MCP szerver stdio-n a Claude appnak (az app indítja a "
                         "configjából; az Artifact innen kapja az élő adatot)")
    ap.add_argument("--dev-install", action="store_true", dest="dev_install",
                    help="fejlesztés: a working tree a stabil helyre (+dev verzióval) — a "
                         "Claude appban futó git-graph átvált rá, a lap élőben kipróbálható")
    ap.add_argument("--session-hook", action="store_true", dest="session_hook",
                    help="Claude Code SessionStart hook: telepítés és a repó regisztrálása "
                         "(stdin: a hook JSON-ja)")
    ap.add_argument("--mod-plan", action="store_true", dest="mod_plan",
                    help="a plugin modjának (--session-nel): JSON, ha most publikálnia és/vagy "
                         "megnyitnia kell a repó Artifactját; különben semmi")
    ap.add_argument("--manual", action="store_true",
                    help="a --mod-plan-hez: a /git-graph command kérése — a beállításoktól és "
                         "a session korábbi megnyitásától függetlenül")
    ap.add_argument("--session", metavar="ID", default=None,
                    help="a --mod-plan-hez: a Claude Code session azonosítója")
    args = ap.parse_args()

    if args.session_hook:
        return session_hook()

    if args.mod_plan:
        plan = (mod_plan(Path(args.repo).expanduser().resolve(), args.session, manual=args.manual)
                if args.session else None)
        if plan:
            print(json.dumps(plan))
        return 0

    if args.mcp:
        return mcp_serve(args.limit or None)

    if args.dev_install:
        return dev_install()

    if args.artifacts:
        for repo, url in list_artifacts():
            print(f"{repo}\t{url}")
        return 0

    if args.forget:
        repo = main_checkout(resolve_repo(Path(args.repo).expanduser().resolve()))
        forget(repo)
        print(f"✓ {repo}: a git-graph nyomai törölve; automatikus megnyitás KI "
              "(git-graph.autoOpen=false)")
        return 0

    # Bármelyik worktree-ből: a repó közös lapja a fő checkouté.
    repo = main_checkout(resolve_repo(Path(args.repo).expanduser().resolve()))
    set_repo(repo)

    if args.set_artifact or args.published:
        url = args.set_artifact or args.published
        if not url.startswith("https://"):
            raise SystemExit("HIBA: az URL-nek https://-sel kell kezdődnie.")
        if args.published:
            mark_published(url)
        else:
            remember_artifact(url)
            register(repo)
        print(f"✓ Artifact megjegyezve: {url}")
        print(f"  {repo_name()} @ {git('rev-parse', '--short', 'HEAD').strip()}")
        return 0

    ap.print_help()
    return 0
