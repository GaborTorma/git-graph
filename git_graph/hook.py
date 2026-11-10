"""A plugin hookja (`--session-hook`) és a modja (`--mod-plan`): telepítés, publikálás, megnyitás."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from . import gitio
from .gitio import config_get, main_checkout, resolve_repo, set_repo
from .install import ensure_installed
from .publish import (PUBLISH_CAPS, PUBLISH_CONTRACT, auto_open, auto_publish, prepare_publish,
                      publish_steps)
from .registry import register, shown_in_session
from .state import log


def session_hook() -> int:
    """Claude Code hook: a gépi rész telepítése és a repó regisztrálása.

    SessionStartként fut. A repó Artifactját nem ez publikálja és nyitja meg,
    hanem a plugin modja (`hooks/register.ts` → `mod_plan`), a modell nélkül:
    a 2.1.321 óta a mod kérés nélkül publikálhat (mérve, .claude/memory/mod-limits.md).
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
        set_repo(main_checkout(resolve_repo(start)))
        register(gitio.REPO)                      # a git-graph --mcp a lap slugjából ebből találja meg
    except (SystemExit, subprocess.CalledProcessError):
        pass                                       # nem repó: nincs mit regisztrálni
    return emit_context(notice)


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
    """A mod kérdése a session indulásakor: publikálja-e és nyissa-e meg a repó Artifactját.

    A terv: `repo`, `url` (új Artifactnál üres), és ha a lap nem naprakész (nincs
    még, a betöltő, a capability-lista vagy a contract változott), `publish`: a
    lap fájlja, címe, a teljes capability-lista és a rögzített contract. A mod
    `Artifact` `read` + `publish`-sal küldi fel, a `--published`-del írja vissza,
    majd az `open`-nel nyitja meg. Akkor ad tervet, ha be van kapcsolva az
    automatikus megnyitás (Artifact nélkül a gép automatikus publikálása is), és
    ebben a sessionben még nem volt (`shown_in_session`). Headless sessionben nincs.
    """
    if headless():
        return None
    try:
        repo = main_checkout(resolve_repo(start))
    except (SystemExit, subprocess.CalledProcessError):
        return None
    set_repo(repo)
    url = config_get("artifact")
    if not auto_open() or not (url or auto_publish()):
        return None
    if shown_in_session(session_id, register(repo)):
        return None
    plan: dict = {"repo": str(repo), "url": url}
    job = prepare_publish()
    if job:
        plan["publish"] = {"file_path": str(job["page"]), "title": job["title"],
                           "capabilities": PUBLISH_CAPS, "contract": PUBLISH_CONTRACT}
    return plan


def emit_context(*parts: str | None) -> int:
    """A hook kimenete: a nem üres részek additionalContextként; ha nincs, semmi."""
    context = "\n\n".join(p for p in parts if p)
    if context:
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                          "additionalContext": context}}, sys.stdout)
    return 0

