"""A plugin hookja (`--session-hook`) és a modja (`--open-url`): telepítés, publikálás, megnyitás."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .gitio import config_get, main_checkout, resolve_repo, set_repo
from .install import ensure_installed
from .publish import is_current, prepare_publish, publish_steps
from .registry import NO_AUTO_PUBLISH, register, shown_in_session
from .state import log


def session_hook() -> int:
    """Claude Code hook: a gépi rész és a repó közös Artifactja.

    SessionStartként fut. A repó minden worktree-je a fő checkout lapját
    látja, ezért a worktree-váltásra nem kell hook. Ha nincs Artifact, vagy a
    lapja elavult, a sessiont kéri meg, hogy publikálja: a lap csak
    kódfrissítéskor változik, az pedig csak új sessionnel lép életbe — és
    ilyenkor először ez a hook fut. A meglévő lapot nem ez nyitja meg, hanem a
    plugin modja (`hooks/register.ts` → `open_url`), a modell nélkül. Headless
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
    job = None if headless() or NO_AUTO_PUBLISH.exists() else prepare_publish()
    context = None                                 # nincs Artifact, nem kérünk, vagy a mod nyitja meg
    if job:
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


def open_url(start: Path, session_id: str | None) -> str | None:
    """A mod kérdése: meg kell-e most nyitni a repó Artifactját, és mi az URL-je.

    Akkor igen, ha van naprakész Artifact (különben a hook publikáltat, és
    utána a session nyitja meg), és ebben a sessionben még nem volt nyitva
    (`shown_in_session`).
    """
    try:
        repo = main_checkout(resolve_repo(start))
    except (SystemExit, subprocess.CalledProcessError):
        return None
    set_repo(repo)
    if headless() or not is_current():
        return None
    if session_id and shown_in_session(session_id, register(repo)):
        return None
    return config_get("artifact")


def emit_context(*parts: str | None) -> int:
    """A hook kimenete: a nem üres részek additionalContextként; ha nincs, semmi."""
    context = "\n\n".join(p for p in parts if p)
    if context:
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                          "additionalContext": context}}, sys.stdout)
    return 0

