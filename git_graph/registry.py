"""A repók nyilvántartása a gépen: slug → repó, sessionök, a repó nyomainak törlése."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .gitio import config_get, git, set_repo, worktree_paths
from .state import STATE_DIR, log

REPOS = STATE_DIR / "repos.json"       # slug → repó útvonal (a hook írja, a git-graph --mcp olvassa)
NO_AUTO_PUBLISH = STATE_DIR / "no-auto-publish"   # ha létezik: a hook nem kér publikálást
SESSIONS = STATE_DIR / "sessions.json"  # session_id → {slug: időbélyeg}: ezekben már megnyílt a lap
SESSION_TTL = 7 * 24 * 3600            # ennyi idő után a bejegyzés törlődik (archiválásra nincs hook)


def slug_for(repo: Path) -> str:
    """Stabil azonosító a repóhoz — az Artifact lapja ezzel kérdezi a `git-graph --mcp`-t.

    A mappanév olvashatóvá teszi, az útvonal-hash pedig egyértelművé: két
    azonos nevű mappa (`~/a/app`, `~/b/app`) nem üthet össze.
    """
    base = re.sub(r"[^a-z0-9]+", "-", repo.name.lower()).strip("-") or "repo"
    return f"{base[:40]}-{hashlib.sha1(str(repo).encode()).hexdigest()[:6]}"


def register(repo: Path) -> str:
    """A repó felvétele a slug-regiszterbe; a slugot adja vissza."""
    slug = slug_for(repo)
    try:
        data = json.loads(REPOS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if data.get(slug) != str(repo):
        data[slug] = str(repo)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        REPOS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    return slug


def repo_for_slug(slug: str) -> Path | None:
    try:
        data = json.loads(REPOS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    path = data.get(slug)
    return Path(path) if path else None


def shown_in_session(session_id: str, slug: str) -> bool:
    """Igaz, ha ebben a sessionben a hook már kérte a lap megnyitását vagy publikálását.

    Egyúttal felveszi a mostanit, és törli a `SESSION_TTL`-nél régebbi
    bejegyzéseket. A `resume` és a `/clear` a sessionben megnyitott Artifactot
    nem zárja be, a `compact` sem — ezért a forrást (`source`) nem nézzük.
    """
    now = time.time()
    try:
        data = json.loads(SESSIONS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data = {sid: {k: t for k, t in slugs.items() if now - t < SESSION_TTL}
            for sid, slugs in data.items() if isinstance(slugs, dict)}
    data = {sid: slugs for sid, slugs in data.items() if slugs}
    seen = slug in data.get(session_id, {})
    data.setdefault(session_id, {})[slug] = now
    # Az app indulásakor több session hookja fut egyszerre: atomi csere, hogy
    # egyik se olvasson félig írt fájlt. Írási hiba nem viheti el a hookot.
    tmp = SESSIONS.with_name(f".sessions.{os.getpid()}.tmp")
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, SESSIONS)
    except OSError as exc:
        log(f"git-graph: a session-napló nem írható: {exc}")
    return seen


def registered_repos() -> dict:
    try:
        data = json.loads(REPOS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def list_artifacts() -> list[tuple[Path, str]]:
    """(repó, Artifact URL) párok — a `/git-graph:remove` ebből dolgozik.

    A regiszter hiányos lehet (leszereléskor törlődik, és csak a hook tölti
    újra), ezért a regisztrált repók szülőmappáinak többi repóját is nézi.
    """
    candidates: set[Path] = set()
    for path in registered_repos().values():
        repo = Path(path)
        candidates.add(repo)
        try:
            candidates.update(p for p in repo.parent.iterdir() if (p / ".git").exists())
        except OSError:
            pass
    found: dict[str, Path] = {}             # URL → repó; a worktree-k configja közös
    for repo in sorted(candidates):
        set_repo(repo)
        try:
            main = worktree_paths()[0]
            url = config_get("artifact")
        except subprocess.CalledProcessError:
            continue                             # eltűnt vagy sérült repó
        if url:
            found.setdefault(url, main)
    return [(repo, url) for url, repo in found.items()]


def forget(repo: Path) -> None:
    """A repó minden git-graph nyoma: a config-szakasza, a helyi lapja és a
    regiszterbejegyzése.

    Az automatikus publikálást is kikapcsolja — különben a következő session
    hookja új Artifactot kérne.
    """
    set_repo(repo)
    slug = slug_for(repo)
    try:
        git("config", "--local", "--remove-section", "git-graph")
    except subprocess.CalledProcessError:
        pass
    shutil.rmtree(STATE_DIR / slug, ignore_errors=True)
    data = registered_repos()
    if data.pop(slug, None) is not None:
        REPOS.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    NO_AUTO_PUBLISH.touch()

