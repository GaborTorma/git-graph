"""A plugin hookja (`--session-hook`) és a modja (`--mod-plan`): telepítés, publikálás, megnyitás."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .gitio import config_get, main_checkout, resolve_repo, set_repo
from .install import ensure_installed
from .publish import auto_open, auto_publish, caps_current, mod_can_publish, prepare_publish, publish_steps
from .registry import register, shown_in_session
from .state import log


def session_hook() -> int:
    """Claude Code hook: a gépi rész és a repó közös Artifactja.

    SessionStartként fut. A repó minden worktree-je a fő checkout lapját
    látja, ezért a worktree-váltásra nem kell hook. Ha nincs Artifact, vagy a
    lapja elavult, a sessiont kéri meg, hogy publikálja (`auto_open`,
    `auto_publish`): a lap csak
    kódfrissítéskor változik, az pedig csak új sessionnel lép életbe — és
    ilyenkor először ez a hook fut. A meglévő lapot nem ez nyitja meg, hanem a
    plugin modja (`hooks/register.ts` → `mod_plan`), a modell nélkül, ha a
    beállítások engedik (`mod_can_publish`). Headless
    (`-p`, SDK) sessionben nem kér publikálást: ott nincs, aki a gráfot nézné.
    """
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    start = Path(payload.get("cwd") or Path.cwd())
    try:
        notice = ensure_installed()
    except Exception as exc:                       # a telepítés hibája ne vigye el a sessiont
        log(f"git-graph: telepítési hiba: {type(exc).__name__}: {exc}")
        notice = None
    try:
        repo = main_checkout(resolve_repo(start))
    except (SystemExit, subprocess.CalledProcessError):
        return emit_context(notice)                # nem repó: nincs mit mutatni
    set_repo(repo)
    slug = register(repo)                         # a git-graph --mcp a lap slugjából ebből találja meg
    # A meglévő lapot az automatikus megnyitás frissíti; Artifact nélküli
    # repóban a gép automatikus publikálása is kell (a lap beállítás-menüje).
    auto = auto_open() and (bool(config_get("artifact")) or auto_publish())
    job = prepare_publish() if auto and not headless() else None
    context = None                                 # naprakész, vagy a mod frissíti; vagy nem kérünk
    if job and not (mod_can_publish() and caps_current()):
        if payload.get("session_id"):              # a publikálás után a session nyitja meg, a mod ne
            shown_in_session(payload["session_id"], slug)
        state = "elavult (a git-graph frissült)" if job["url"] else "még nincs"
        context = (f"A(z) {repo} repó élő git-graph Artifactja {state}. Most, a "
                   "Fejlesztő kérésének folytatása előtt publikáld, és ne írj róla üzenetet: "
                   + publish_steps(job) + "\nHa valamelyik lépés nem sikerül, egy mondatban "
                   "jelezd, és folytasd a Fejlesztő kérésével.")
    return emit_context(context, notice)


def headless() -> bool:
    """`-p` vagy SDK session: ott nincs, aki a gráfot nézné."""
    return os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk")


def open_url(start: Path) -> str | None:
    """A `/git-graph:artifact-open`-nek, a beállítástól függetlenül: az URL, elavult
    lapnál a frissítés lépései (`PUBLIKÁLD: …`), Artifact nélkül semmi."""
    try:
        repo = main_checkout(resolve_repo(start))
    except (SystemExit, subprocess.CalledProcessError):
        return None
    set_repo(repo)
    if not config_get("artifact"):
        return None
    job = prepare_publish()
    return "PUBLIKÁLD: " + publish_steps(job) if job else config_get("artifact")


def mod_plan(start: Path, session_id: str) -> dict | None:
    """A mod kérdése a session indulásakor: küldje-e újra és nyissa-e meg a repó Artifactját.

    Az app Artifact-panelje csak a sessionben publikált lapot mutatja (az
    `Artifact` tool és az `open` megszűnt, mérve 2026-11-05), ezért a mod a
    megnyitáshoz újraküldi a lapot (`force`) — az elavultat is, ha csak a
    betöltő változott: a capability a republishnél öröklődik. Ha a
    capability-lista változott (`caps_current`), vagy nincs még Artifact, a hook
    a sessiontől kéri: a `declare_capabilities`-t modból az auto mód az
    allow-szabály és a kattintás `consent`-je mellett sem engedi (mérve,
    2026-11-06). Akkor ad tervet, ha be van kapcsolva az automatikus megnyitás,
    a beállítások engedik (`mod_can_publish`), és ebben a sessionben még nem volt
    (`shown_in_session`).
    """
    if headless() or not mod_can_publish():
        return None
    try:
        repo = main_checkout(resolve_repo(start))
    except (SystemExit, subprocess.CalledProcessError):
        return None
    set_repo(repo)
    if not auto_open() or not caps_current():
        return None
    if shown_in_session(session_id, register(repo)):
        return None
    job = prepare_publish(force=True)
    return {"repo": str(repo), "url": config_get("artifact"), "page": str(job["page"])}


def emit_context(*parts: str | None) -> int:
    """A hook kimenete: a nem üres részek additionalContextként; ha nincs, semmi."""
    context = "\n\n".join(p for p in parts if p)
    if context:
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                          "additionalContext": context}}, sys.stdout)
    return 0

