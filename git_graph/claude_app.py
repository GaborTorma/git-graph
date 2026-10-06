"""A Claude app belső fájljai: melyik session van előtérben, és az app worktree-inek ága."""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from .registry import slug_for

# A worktree-k közös lapot látnak, az app pedig egy Artifactnak egyetlen
# keretet tart, és azt mutatja minden sessionben — a lap maga nem tudhatja,
# melyik sessionben látszik éppen; a host-híd hívásából sem derül ki (mérve,
# docs/artifact-findings.md). A Claude app viszont sessionönként JSON-t tart
# (`claude-code-sessions/<fiók>/<szervezet>/local_<id>.json`) a
# munkakönyvtárral és a `lastFocusedAt` időbélyeggel: a repóban dolgozó
# sessionök közül a legutóbb fókuszált van előtérben. Belső fájl — ismeretlen
# formánál nem dönt (a fő checkout a saját).
#
# A `lastFocusedAt` 1–3 s késéssel kerül a fájlba, az app naplója
# (`~/Library/Logs/Claude/main.log`) viszont a váltás után ~20 ms-mal már
# tartalmazza (`setFocusedSession: sessionId=local_<id>`, mérve,
# docs/artifact-findings.md). A fókusz idejét ezért a naplóból vesszük, ha
# ott van; a fájlból csak a munkakönyvtár és az archiváltság jön.

APP_SESSIONS = (Path.home() / "Library" / "Application Support" / "Claude"
                / "claude-code-sessions")
_APP_SESSIONS: dict[str, tuple[float, dict | None]] = {}   # fájl → (mtime, {id, cwd, focused, archived})
APP_LOG = Path.home() / "Library" / "Logs" / "Claude" / "main.log"
APP_LOG_TAIL = 2 << 20          # induláskor ennyit olvasunk vissza a napló végéből
FOCUS_LINE = re.compile(rb"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) \[info\] \[CCD\] "
                        rb"LocalSessions\.setFocusedSession: sessionId=(local_[0-9a-f-]+)", re.M)
_APP_LOG: dict = {"ino": None, "pos": 0, "seq": 0, "focus": {}}   # focus: id → (idő, sorszám)
FOCUS_LOCK = threading.Lock()


def app_sessions() -> list[dict]:
    """A Claude app desktop-sessionjei: munkakönyvtár és utolsó fókusz.

    A fájlok nagyok (több száz, egyenként akár ~800 KB), a fókuszt pedig minden
    `changes`-válasz kéri: mindet `stat`-oljuk (< 1 ms), de csak a megváltozottat
    olvassuk újra — váltáskor ez egyetlen fájl.
    """
    out, live = [], set()
    for path in APP_SESSIONS.glob("*/*/local_*.json"):
        key = str(path)
        live.add(key)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        cached = _APP_SESSIONS.get(key)
        if cached is None or cached[0] != mtime:
            info = None
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cwd = data.get("worktreePath") or data.get("cwd")
                focused = data.get("lastFocusedAt")
                if isinstance(cwd, str) and isinstance(focused, (int, float)):
                    info = {"id": path.stem, "cwd": cwd, "focused": focused / 1000,
                            "archived": bool(data.get("isArchived"))}
            except (OSError, ValueError, AttributeError):
                pass
            cached = _APP_SESSIONS[key] = (mtime, info)
        if cached[1]:
            out.append(cached[1])
    for key in set(_APP_SESSIONS) - live:
        del _APP_SESSIONS[key]
    return out


def app_log_focus() -> dict:
    """Session-azonosító → a legutóbbi fókusz (idő, sorszám) az app naplójából.

    Csak az új sorokat olvassa; a napló forgatását (új inode, rövidebb fájl)
    az elejéről kezdi. A napló másodpercre kerekít: a fókusz a másodperc
    végére kerül (a fájl ms-os értéke ugyanarra a váltásra így sosem előzi),
    az egy másodpercen belüli váltások sorrendjét a sorszám dönti el.
    """
    state = _APP_LOG
    try:
        st = APP_LOG.stat()
    except OSError:
        return state["focus"]
    if st.st_ino != state["ino"] or st.st_size < state["pos"]:
        first = state["ino"] is None
        state.update(ino=st.st_ino, pos=max(0, st.st_size - APP_LOG_TAIL) if first else 0)
    state["pos"] = max(state["pos"], st.st_size - APP_LOG_TAIL)
    if st.st_size == state["pos"]:
        return state["focus"]
    try:
        with APP_LOG.open("rb") as f:
            f.seek(state["pos"])
            chunk = f.read(st.st_size - state["pos"])
    except OSError:
        return state["focus"]
    end = chunk.rfind(b"\n") + 1                  # a félbe írt sor a következő körre marad
    state["pos"] += end
    for m in FOCUS_LINE.finditer(chunk, 0, end):
        try:
            at = time.mktime(time.strptime(m.group(1).decode(), "%Y-%m-%d %H:%M:%S")) + 0.999
        except ValueError:
            continue
        state["seq"] += 1
        state["focus"][m.group(2).decode()] = (at, state["seq"])
    return state["focus"]


def log_advance(ino: int, pos: int) -> tuple[int, int, bool]:
    """Az app naplója az (inode, pozíció) kurzortól: az új kurzor, és volt-e közben
    session-váltás. Ismeretlen kurzornál (`-1`) a napló végéről indul, jelzés nélkül;
    forgatásnál (új inode) jelez. Saját fájlolvasás, megosztott állapot nélkül."""
    try:
        st = APP_LOG.stat()
    except OSError:
        return ino, pos, False
    if st.st_ino != ino or st.st_size < pos:
        return st.st_ino, st.st_size, ino != -1
    if st.st_size == pos:
        return ino, pos, False
    try:
        with APP_LOG.open("rb") as f:
            f.seek(pos)
            chunk = f.read(st.st_size - pos)
    except OSError:
        return ino, pos, False
    end = chunk.rfind(b"\n") + 1
    return ino, pos + end, bool(FOCUS_LINE.search(chunk, 0, end))


APP_WORKTREES = Path.home() / "Library" / "Application Support" / "Claude" / "git-worktrees.json"
_APP_WORKTREES: dict = {"mtime": None, "branches": {}}


def app_worktree_branches() -> dict[str, str]:
    """Az app által létrehozott worktree-k ága, a mappájuk szerint (`git-worktrees.json`).

    A session törlésekor az app leválasztja a worktree HEAD-jét; az ágat a git
    ezután semmivel nem köti a worktree-hez, az app nyilvántartása igen. Belső
    fájl: ismeretlen formánál üres.
    """
    try:
        mtime = APP_WORKTREES.stat().st_mtime
    except OSError:
        return {}
    if mtime != _APP_WORKTREES["mtime"]:
        branches = {}
        try:
            entries = json.loads(APP_WORKTREES.read_text(encoding="utf-8")).get("worktrees") or {}
            for entry in entries.values():
                path, branch = entry.get("path"), entry.get("branch")
                if isinstance(path, str) and isinstance(branch, str) and branch:
                    branches[str(Path(path).resolve())] = branch
        except (OSError, ValueError, AttributeError):
            branches = {}
        _APP_WORKTREES.update(mtime=mtime, branches=branches)
    return _APP_WORKTREES["branches"]


def worktree_of(cwd: str, roots: list[tuple[Path, str]]) -> str | None:
    """A munkakönyvtárat tartalmazó worktree slugja (a legmélyebb, ha egymásba
    ágyazottak). `roots`: a worktree-k feloldott útja és slugja, hívásonként egyszer."""
    path = Path(cwd).resolve()                    # a git a valódi utat adja (/var → /private/var)
    hits = [(root, slug) for root, slug in roots if root == path or root in path.parents]
    return max(hits, key=lambda hit: len(hit[0].parts))[1] if hits else None


def focused_worktree(worktrees: list[dict]) -> dict:
    """A repó előtérben lévő sessionjének worktree-je (`worktree`: slug, vagy None).

    `known`: van-e a repóban dolgozó session; ha nincs, a lap a fő checkoutot
    tekinti sajátnak.
    """
    with FOCUS_LOCK:                          # a várakozó hívás szála is számolja
        logged, sessions = dict(app_log_focus()), app_sessions()
    roots = [(wt["path"].resolve(), slug_for(wt["path"])) for wt in worktrees]
    best = None
    for session in sessions:
        if session["archived"]:
            continue
        slug = worktree_of(session["cwd"], roots)
        at = max((session["focused"], 0), logged.get(session["id"], (0, 0)))
        if slug and (best is None or at > best[0]):
            best = (at, slug)
    return {"worktree": best[1] if best else None, "known": best is not None}


