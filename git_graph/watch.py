"""A `changes` tool: a nyitva tartott hívás, amely a repó vagy a fókusz változásáig vár."""
from __future__ import annotations

import hashlib
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .avatars import avatar_signal
from .claude_app import APP_LOG, FOCUS_LINE, focused_worktree
from .gitio import git, worktree_list
from .install import RUNNING_VERSION, installed_version


def repo_state(repo: Path) -> str:
    """A repó állapotának hashe — ha változik, a lap újrakéri a `graph_data`-t.

    Benne minden ref és worktree-nként a HEAD és az ág (ágváltás ugyanarra a
    commitra is badge-változás, új vagy megszűnt worktree is változás), a
    státusz és a commitolatlan fájlok legutóbbi módosítása ns-ban — ez jelzi egy
    már módosított fájl újabb szerkesztését is, a `diff --numstat` nélkül —, és a
    megtalált avatarok száma. A `for-each-ref` és a worktree-k `status`-a
    párhuzamosan fut: ~15 ms egy kis repón (sorban, numstattal ~50 ms volt).
    """
    with ThreadPoolExecutor(max_workers=8) as pool:
        refs = pool.submit(git, "for-each-ref", "--format=%(objectname) %(refname)", repo=repo)
        worktrees = worktree_list(repo)

        def status(wt: dict) -> list[str] | None:
            try:
                return [line for line in git("status", "--porcelain", repo=wt["path"]).splitlines()
                        if line.strip()]
            except subprocess.CalledProcessError:
                return None                         # közben megszűnt

        parts = [refs.result(), str(avatar_signal())]
        for wt, lines in zip(worktrees, pool.map(status, worktrees)):
            if lines is None:
                continue
            newest = 0
            for line in lines:
                try:
                    newest = max(newest, (wt["path"] / line[3:].strip().strip('"').rstrip("/"))
                                 .stat().st_mtime_ns)
                except OSError:
                    pass
            parts.append(f"{wt['path']} {wt['head']} {wt['branch']}\n" + "\n".join(lines) + f"\n{newest}")
    return hashlib.sha1("\0".join(parts).encode()).hexdigest()


WAIT_MAX = 50.0               # s — a host válasz-időkorlátja alatt (mérve)
STATE_EVERY = 2.0             # s — a teljes állapot (`repo_state`) legalább ennyi időnként
WAKE = threading.Event()      # újraindulás előtt: a várakozó hívások azonnal válaszolnak


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


def stamp_paths(repo: Path) -> list[Path]:
    """Az olcsó előszűrő fájljai: worktree-nként a HEAD, az index és a HEAD reflogja,
    közösen a packed-refs, a FETCH_HEAD és a ref-mappák (egy ref írása átnevezés,
    a mappa mtime-ja változik). A fájlszerkesztést nem fogja: arra a teljes állapot."""
    common = repo / ".git"
    if not common.is_dir():
        common = Path(git("rev-parse", "--path-format=absolute", "--git-common-dir", repo=repo).strip())
    admins = [common, *sorted((common / "worktrees").glob("*"))]
    refs = [common / "refs" / "heads", common / "refs" / "tags",
            *sorted((common / "refs" / "remotes").glob("*"))]
    return [*(a / name for a in admins for name in ("HEAD", "index", "logs/HEAD")),
            common / "packed-refs", common / "FETCH_HEAD", *refs]


def file_stamp(paths: list[Path]) -> tuple[int, ...]:
    """A fájlok mtime-ja (ns; a hiányzóé 0) — 10 fájlra ~0,03 ms (mérve)."""
    out = []
    for path in paths:
        try:
            out.append(path.stat().st_mtime_ns)
        except OSError:
            out.append(0)
    return tuple(out)


def wait_changes(repo: Path, since: str, wait: float) -> dict:
    """A `changes` tool: vár, amíg a repó állapota eltér a `since`-étől, vagy az app
    naplójában session-váltás jelenik meg — legfeljebb `wait` s-ig (`WAIT_MAX`).

    A `since` az előző válasz átlátszatlan tokenje: állapot-hash és naplókurzor
    (`<hash>.<inode>:<pozíció>`); üresen azonnal válaszol. A két hívás között
    jött változás sem vész el. Várakozás közben 50 ms-onként a naplót és az
    olcsó stat-jelet nézi (git-művelet ~50 ms-on belül), a teljes állapotot
    (`repo_state`, ~15 ms) a stat-jel változásakor és `STATE_EVERY`-nként — a
    fájlszerkesztés így legfeljebb ~2 s alatt jön. Külön szálon fut, explicit
    repóval: a `REPO` globálist nem használja.
    """
    old, _, cursor = since.partition(".")
    try:
        ino, pos = (int(x) for x in cursor.split(":"))
    except ValueError:
        ino = pos = -1
    ino, pos, switched = log_advance(ino, pos)
    state = repo_state(repo)
    paths = stamp_paths(repo)
    stamp, full_at = file_stamp(paths), time.monotonic() + STATE_EVERY
    deadline = time.monotonic() + max(0.0, min(wait, WAIT_MAX))
    while not switched and state == old and not WAKE.is_set() and time.monotonic() < deadline:
        time.sleep(0.05)
        ino, pos, switched = log_advance(ino, pos)
        now = file_stamp(paths)
        if now != stamp or time.monotonic() >= full_at:
            stamp, full_at = now, time.monotonic() + STATE_EVERY
            state = repo_state(repo)
    # A verziók is itt: egy frissítés utáni, még újra nem indított app a láblécben látszik.
    return {"since": f"{state}.{ino}:{pos}", "state": state,
            "focus": focused_worktree(worktree_list(repo)),
            "version": RUNNING_VERSION, "installed": installed_version()}

