"""A plugin hookja (`--session-hook`): telepítés, és a repó Artifactjának megnyitása vagy publikálása."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .gitio import config_get, main_checkout, resolve_repo, set_repo
from .install import ensure_installed
from .publish import prepare_publish, publish_steps
from .registry import NO_AUTO_PUBLISH, register, shown_in_session
from .state import log


def session_hook() -> int:
    """Claude Code hook: a gépi rész és a repó közös Artifactja.

    SessionStartként és az `EnterWorktree` / `ExitWorktree` utáni
    PostToolUse-ként fut — a `cwd` ilyenkor már az új munkakönyvtár. A repó
    minden worktree-je a fő checkout lapját látja. Ha nincs Artifact, vagy a
    lapja elavult, a sessiont kéri meg, hogy publikálja: a lap csak
    kódfrissítéskor változik, az pedig csak új sessionnel lép életbe — és
    ilyenkor először ez a hook fut. Különben a meglévőt nyittatja meg — de egy
    sessionben csak egyszer (`shown_in_session`; worktree-váltás ugyanazon a
    repón belül nem nyit újra). Headless (`-p`, SDK) sessionben nem kér publikálást: ott nincs, aki
    a gráfot nézné.
    """
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    event = payload.get("hook_event_name") or "SessionStart"
    start = Path(payload.get("cwd") or Path.cwd())
    try:
        notice = ensure_installed()
    except Exception as exc:                       # a telepítés hibája ne vigye el a sessiont
        log(f"git-graph: telepítési hiba: {type(exc).__name__}: {exc}")
        notice = None
    try:
        repo = main_checkout(resolve_repo(start))
    except (SystemExit, subprocess.CalledProcessError):
        return emit_context(notice, event=event)   # nem repó: nincs mit mutatni
    set_repo(repo)
    slug = register(repo)                         # a git-graph --mcp a lap slugjából ebből találja meg
    url = config_get("artifact")
    headless = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").startswith("sdk")
    job = None if headless or NO_AUTO_PUBLISH.exists() else prepare_publish()
    seen = (shown_in_session(payload["session_id"], slug)
            if payload.get("session_id") and not headless else False)
    if job:
        state = "elavult (a git-graph frissült)" if job["url"] else "még nincs"
        context = (f"A(z) {repo} repó élő git-graph Artifactja {state}. Most, a "
                   "Fejlesztő kérésének folytatása előtt publikáld, és ne írj róla üzenetet: "
                   + publish_steps(job) + "\nHa valamelyik lépés nem sikerül, egy mondatban "
                   "jelezd, és folytasd a Fejlesztő kérésével.")
    elif url and not seen:
        context = (f"A(z) {repo} repó élő git-graph Artifactja: {url} (a gépen futó "
                   "git-graph-ból élőben frissül).\nMost nyisd meg EGYSZER az "
                   "Artifact eszközzel — action: \"open\", url paraméterrel —, és ne írj "
                   "róla üzenetet.")
    else:
        context = None                             # nincs Artifact, nem kérünk, vagy már nyitva van
    return emit_context(context, notice, event=event)


def emit_context(*parts: str | None, event: str = "SessionStart") -> int:
    """A hook kimenete: a nem üres részek additionalContextként; ha nincs, semmi."""
    context = "\n\n".join(p for p in parts if p)
    if context:
        json.dump({"hookSpecificOutput": {"hookEventName": event,
                                          "additionalContext": context}}, sys.stdout)
    return 0

