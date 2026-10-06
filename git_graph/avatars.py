"""GitHub-avatarok a commitok szerzőinek."""
from __future__ import annotations

import base64
import json
import re
import threading
import time
import urllib.request
from pathlib import Path

from .state import STATE_DIR, log, place, read_json

# A lap a kinyitott commit szerzőjének képét mutatja. Az Artifact CSP-je külső
# képet nem enged, ezért a Python tölti le, és data URI-ként adja a
# `graph_data`-ban. A letöltés háttérszálon fut (a pollozás nem vár rá); amikor
# kész, az ujjlenyomat (`avatar_signal`) változik, és a lap újrakéri az adatot.

AVATARS_FILE_NAME = "avatars.json"     # e-mail → {"img": data URI | None, "at": időbélyeg}
AVATAR_TTL = 7 * 24 * 3600             # a megtalált kép hetente frissül
AVATAR_RETRY = 6 * 3600                # ami nem jött (privát repó, nincs fiók, offline), ennyi után újra
AVATAR_SIZE = 44                       # 22 px-es kép, retina
AVATAR_MAX_BYTES = 64_000
NOREPLY_RE = re.compile(r"^(?:\d+\+)?([A-Za-z0-9-]+)@users\.noreply\.github\.com$")
_AVATAR_JOBS: set[str] = set()         # éppen letöltés alatt (e-mail)
_AVATAR_LOCK = threading.Lock()


def avatars_path() -> Path:
    return STATE_DIR / AVATARS_FILE_NAME


_AVATAR_MEMO: tuple[int, dict] | None = None   # (mtime_ns, tartalom) — a fájlt csak változáskor olvassuk


def avatar_cache() -> dict:
    """A gyorstár (másolat). Az állapot (`repo_state`) 2 s-onként kérdezi, a fájl
    pedig a képekkel nagy: csak akkor olvassuk újra, ha módosult."""
    global _AVATAR_MEMO
    try:
        mtime = avatars_path().stat().st_mtime_ns
    except OSError:
        return {}
    if _AVATAR_MEMO is None or _AVATAR_MEMO[0] != mtime:
        data = read_json(avatars_path())
        _AVATAR_MEMO = (mtime, data if isinstance(data, dict) else {})
    return dict(_AVATAR_MEMO[1])


def avatar_signal() -> int:
    """A megtalált képek száma — az ujjlenyomat része: új képre a lap újrakéri az adatot."""
    return sum(1 for v in avatar_cache().values() if isinstance(v, dict) and v.get("img"))


def avatars_for(commits: list[dict], repo_url_: str) -> dict[str, str]:
    """A szerzők avatarja (e-mail → data URI) a gyorstárból; a hiányzót háttérben kéri.

    Csak GitHub-os repónál, és csak olyan szerzőnél, akinek van pusholt commitja
    (az API azon át adja a fiókot) vagy GitHub noreply címe van.
    """
    if not repo_url_:
        return {}
    cache, now = avatar_cache(), time.time()
    found: dict[str, str] = {}
    todo: dict[str, str] = {}               # e-mail → egy pusholt commitja
    for c in commits:
        email = c.get("email")
        if not email or email in found or email in todo:
            continue
        entry = cache.get(email)
        if isinstance(entry, dict):
            if entry.get("img"):
                found[email] = entry["img"]
            if now - entry.get("at", 0) < (AVATAR_TTL if entry.get("img") else AVATAR_RETRY):
                continue
        if c.get("pushed") or NOREPLY_RE.match(email):
            todo[email] = c["sha"]
    with _AVATAR_LOCK:
        todo = {e: s for e, s in todo.items() if e not in _AVATAR_JOBS}
        _AVATAR_JOBS.update(todo)
    if todo:
        threading.Thread(target=fetch_avatars, args=(repo_url_, todo), daemon=True).start()
    return found


def http_get(url: str) -> tuple[bytes, str]:
    """(törzs, tartalomtípus); hibánál OSError (a `URLError` is az)."""
    req = urllib.request.Request(url, headers={"User-Agent": "git-graph",
                                               "Accept": "application/vnd.github+json, image/*"})
    with urllib.request.urlopen(req, timeout=5) as resp:   # csak https://…github…
        return resp.read(AVATAR_MAX_BYTES + 1), resp.headers.get_content_type()


def fetch_avatar(owner_repo: str, email: str, sha: str) -> str | None:
    """Egy szerző képe data URI-ként; None, ha a GitHub nem ismeri."""
    m = NOREPLY_RE.match(email)
    if m:
        src = f"https://github.com/{m[1]}.png?size={AVATAR_SIZE}"
    else:
        info = json.loads(http_get(f"https://api.github.com/repos/{owner_repo}/commits/{sha}")[0])
        src = (info.get("author") or {}).get("avatar_url")
        if not src:
            return None
        src += ("&" if "?" in src else "?") + f"s={AVATAR_SIZE}"
    body, ctype = http_get(src)
    if not ctype.startswith("image/") or len(body) > AVATAR_MAX_BYTES:
        return None
    return f"data:{ctype};base64,{base64.b64encode(body).decode('ascii')}"


def fetch_avatars(repo_url_: str, todo: dict[str, str]) -> None:
    """Háttérszál: a képek letöltése és gyorstárba írása, egyenként."""
    owner_repo = repo_url_[len("https://github.com/"):]
    for email, sha in todo.items():
        try:
            img = fetch_avatar(owner_repo, email, sha)
        except (OSError, ValueError):
            img = None
        with _AVATAR_LOCK:
            cache = avatar_cache()
            cache[email] = {"img": img, "at": time.time()}
            try:
                place(json.dumps(cache).encode("utf-8"), avatars_path(), 0o644)
            except OSError as exc:
                log(f"git-graph: az avatar-gyorstár nem írható: {exc}")
            _AVATAR_JOBS.discard(email)

