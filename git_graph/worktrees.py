"""A repó worktree-jei: állapotuk, a lapnak szóló adatuk és a commitolatlan változásaik ál-sora."""
from __future__ import annotations

import datetime
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .claude_app import app_worktree_branches
from .gitio import ahead_behind, git, worktree_list
from .registry import slug_for
from .stats import dir_prefixes, mark_dirs, missing_trees, numstat_files


UNCOMMITTED = "*uncommitted"
UNCOMMITTED_RE = re.compile(r"^\*uncommitted(?::([a-z0-9-]+))?$")


def user_config(root: Path, key: str) -> str:
    """A worktree git-felhasználója (`user.name` / `user.email`) — a WIP-sor szerzője."""
    try:
        return git("config", f"user.{key}", repo=root).strip()
    except subprocess.CalledProcessError:
        return ""


def last_change(root: Path, files: list[dict]) -> int:
    """A commitolatlan fájlok legutóbbi módosítása (epoch s) — a git ezt nem tárolja,
    a fájlrendszer igen; a törölt fájl kimarad. A lap ebben a sorrendben mutatja
    a worktree-k WIP-sorait."""
    latest = 0
    for f in files:
        try:
            latest = max(latest, int((root / f["path"]).stat().st_mtime))
        except OSError:
            pass
    return latest


def untracked_lines(path: Path) -> int | None:
    """Követetlen fájl sorainak száma (mint az `untracked_diff`-é); bináris vagy olvashatatlan: `None`."""
    try:
        return len(path.read_bytes()[:2_000_000].decode("utf-8").splitlines())
    except (OSError, UnicodeDecodeError):
        return None


def collect_uncommitted(wt: dict) -> tuple[dict, dict] | None:
    """Egy worktree változásai egy ál-commitként, a Git Graph mintájára.

    A gráf tetejére kerül, szülője a worktree HEAD-je — így szaggatott vonallal
    odalóg, és a soron kattintva ugyanaz a részletek-panel nyílik, mint egy
    commitnál. A sha-ja `*uncommitted:<worktree-slug>`: ebből tudja a
    `file_diff`, melyik munkakönyvtárat diffelje. A szerzője a gép git-felhasználója
    (a worktree configjából), az ideje a fájlok legutóbbi módosítása — a lap ez
    alapján teszi a helyére. Változás nélkül nincs sor.
    """
    status = wt["status"]
    if not status or not wt["head"]:     # commit nélküli repó: nincs mihez kötni
        return None
    st = numstat_files(wt["numstat"].splitlines())
    files = st["files"]

    # A követetlen fájlokat a diff nem látja: a soraik száma a fájlból jön, és a
    # helyükre kerülnek (a git útvonal szerint rendez), nem a lista aljára.
    known = {f["path"] for f in files}
    for line in status:
        if line.startswith("??"):
            path = line[3:].strip().strip('"')
            if path not in known:
                lines = untracked_lines(wt["path"] / path)
                files.append({"path": path, "add": lines or 0, "del": 0, "bin": lines is None, "status": "A"})
                st["add"] += lines or 0
    files.sort(key=lambda f: f["path"])

    # Új mappa: a HEAD-ben nincs; törölt: nem maradt benne követett fájl (az index
    # a még nem stage-elt törlést is tartalmazza, ezért a törölteket levonjuk).
    added = [f for f in files if f.get("status") == "A"]
    mark_dirs([(f, wt["head"]) for f in added],
              missing_trees({f"{wt['head']}:{d}" for f in added for d in dir_prefixes(f["path"])}, wt["path"]))
    deleted = [f for f in files if f.get("status") == "D"]
    if deleted:
        gone = {f["path"] for f in deleted}
        dirs = {d for f in deleted for d in dir_prefixes(f["path"])}
        tracked = [p for p in git("ls-files", "--", *dirs, repo=wt["path"]).splitlines()
                   if p not in gone] if dirs else []
        empty = {d for d in dirs if not any(p.startswith(d + "/") for p in tracked)}
        mark_dirs([(f, "") for f in deleted], {f":{d}" for d in empty})

    changed = last_change(wt["path"], files)
    commit = {
        "sha": f"{UNCOMMITTED}:{wt['slug']}",
        "short": "*",
        "parents": [wt["head"]],
        "author": user_config(wt["path"], "name") or "*",
        "email": user_config(wt["path"], "email"),
        "date": datetime.datetime.fromtimestamp(changed or time.time()).astimezone()
                .isoformat(timespec="seconds"),
        "refs": [],
        "subject": "Nem commitolt változások",
        "body": "",
        "uncommitted": True,
        "worktree": wt["slug"],
        "changed": changed,
    }
    return commit, st


def app_branch(wt: dict) -> str | None:
    """A leválasztott HEAD-ű hozzáadott worktree ága: a git nem jegyzi, a Claude app igen."""
    if wt["branch"] or (wt["path"] / ".git").is_dir():
        return None
    return app_worktree_branches().get(str(wt["path"].resolve()))


def collect_worktrees(repo: Path | None = None) -> list[dict]:
    """A repó (alapból a `REPO`) worktree-jei állapottal: worktree-nként `git status` + `git diff --numstat`.

    Párhuzamosan fut: 5 worktree-vel ~50 ms (sorban ~200 ms; nagy repón 330
    ms / 680 ms — mérve, docs/artifact-findings.md). A közben megszűnt worktree
    kimarad.
    """
    worktrees = worktree_list(repo)

    def fill(wt: dict) -> None:
        try:
            wt["status"] = [line for line in git("status", "--porcelain", "--untracked-files=all", repo=wt["path"])
                            .splitlines() if line.strip()]
            wt["numstat"] = git("diff", "--numstat", "--summary", "HEAD", repo=wt["path"]) if wt["head"] else ""
        except subprocess.CalledProcessError:
            wt["gone"] = True

    with ThreadPoolExecutor(max_workers=max(1, min(8, len(worktrees)))) as pool:
        list(pool.map(fill, worktrees))
    worktrees = [wt for wt in worktrees if not wt.get("gone")]
    for wt in worktrees:
        wt["slug"] = slug_for(wt["path"])
        wt["main"] = (wt["path"] / ".git").is_dir()     # a hozzáadott worktree-ben fájl
    return worktrees


def worktree_meta(wt: dict, base: str) -> dict:
    """Egy worktree a lapnak: azonosító, mappa, ág, HEAD, változások száma (az ág
    távolságait a `meta.tracks` adja). Leválasztott HEAD-nél a HEAD-commit távolsága az
    alapágtól (`base`, mint az ágaké) — ágkulcs híján itt."""
    meta = {"slug": wt["slug"], "name": wt["path"].name, "path": str(wt["path"]),
            "branch": wt["branch"], "head": wt["head"], "main": wt["main"],
            "dirty": len(wt["status"])}
    if not wt["branch"] and not wt["main"]:
        meta["appBranch"] = app_branch(wt)
    if not wt["branch"] and base and wt["head"]:
        try:
            meta["base"] = ahead_behind(base, wt["head"])
        except (subprocess.CalledProcessError, ValueError):
            pass
    return meta
