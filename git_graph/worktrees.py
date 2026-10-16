"""A repó worktree-jei: állapotuk, a lapnak szóló adatuk és a commitolatlan változásaik ál-sorai."""
from __future__ import annotations

import datetime
import difflib
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .claude_app import app_worktree_branches
from .gitio import ahead_behind, git, numstat_new_path, worktree_list
from .registry import slug_for
from .stats import dir_prefixes, mark_dirs, missing_trees, numstat_files


UNCOMMITTED = "*uncommitted"
STAGED = "*staged"
UNCOMMITTED_RE = re.compile(r"^\*(uncommitted|staged)(?::([a-z0-9-]+))?$")
RENAME_MIN = 0.5            # a git `-M` alapküszöbe: ennyi közös tartalom már átnevezés
RENAME_MAX_CELLS = 2000     # e fölött (törölt × követetlen) nincs párosítás — egy friss build-mappa ne lassítson


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
            latest = max(latest, int((root / numstat_new_path(f["path"])).stat().st_mtime))
        except OSError:
            pass
    return latest


def read_lines(path: Path) -> list[str] | None:
    """Követetlen fájl sorai (mint az `untracked_diff`-é); bináris vagy olvashatatlan: `None`."""
    try:
        return path.read_bytes()[:2_000_000].decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def untracked_lines(path: Path) -> int | None:
    """Követetlen fájl sorainak száma; bináris vagy olvashatatlan: `None`."""
    lines = read_lines(path)
    return None if lines is None else len(lines)


def head_lines(root: Path, head: str, path: str) -> list[str] | None:
    """Egy fájl sorai a HEAD-ben (üres `head`: az indexben); bináris vagy hiányzó: `None`."""
    try:
        return git("cat-file", "blob", f"{head}:{path}", repo=root)[:2_000_000].splitlines()
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return None


def line_churn(old: list[str], new: list[str], sm: difflib.SequenceMatcher | None = None) -> tuple[int, int, float]:
    """Két sorlista különbsége: (+, −, hasonlóság). A hasonlóság a közös sorok aránya
    a hosszabbikhoz (mint a git `-M`-é, csak sorokban, nem bájtokban); üres fájl
    sosem hasonló — a git sem párosítja. `sm`: a két listára már felépített matcher."""
    sm = sm or difflib.SequenceMatcher(None, old, new, autojunk=False)
    add = rem = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            rem, add = rem + i2 - i1, add + j2 - j1
    longest = max(len(old), len(new))
    same = sum(b.size for b in sm.get_matching_blocks())
    return add, rem, same / longest if old and new else 0.0


def rename_path(old: str, new: str) -> str:
    """Átnevezés a `--numstat` alakjában (`x/{a => b}/y`, `a => b`): a közös mappa-előtag és
    -utótag a kapcsos zárójelen kívül, ahogy a git írja — a lap és a `file_diff` ezt bontja."""
    pre = 0
    for i, (a, b) in enumerate(zip(old, new)):
        if a != b:
            break
        if a == "/":
            pre = i + 1
    suf, room = 0, min(len(old), len(new)) - pre
    for k in range(1, room + 1):
        if old[-k] != new[-k]:
            break
        if old[-k] == "/":
            suf = k
    if not pre and not suf:
        return f"{old} => {new}"
    return f"{old[:pre]}{{{old[pre:len(old) - suf]} => {new[pre:len(new) - suf]}}}{old[len(old) - suf:]}"


def pair_renames(root: Path, base: str, deleted: list[str], untracked: list[str]) -> list[tuple[str, str, int, int]]:
    """A törölt (`D`) és a követetlen (`??`) fájlok párjai, hasonlóság szerint: [(régi, új, +, −), …].

    A még nem stage-elt átnevezést a git nem látja (az új fájl követetlen; `git add -N`
    után látná, de az indexet nem írjuk), így a párosítás itt történik: a legjobb
    hasonlóságú párok előbb, egy fájl egyszer. Szöveges fájlokra; a túl sok jelölt
    (`RENAME_MAX_CELLS`) esetén nincs párosítás. A régi tartalom a `base`-ből jön (üres: az index).
    """
    if not deleted or not untracked or len(deleted) * len(untracked) > RENAME_MAX_CELLS:
        return []
    olds = {p: head_lines(root, base, p) for p in deleted}
    news = {p: read_lines(root / p) for p in untracked}
    scored = []
    for o, a in olds.items():
        if a is None:
            continue
        for n, b in news.items():
            if b is None or not a or not b:
                continue
            sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
            if sm.real_quick_ratio() < RENAME_MIN or sm.quick_ratio() < RENAME_MIN:
                continue                     # a 2M/(a+b) felső korlát, ≥ a mérték
            add, rem, score = line_churn(a, b, sm)
            if score >= RENAME_MIN:
                scored.append((-score, o.rsplit("/", 1)[-1] != n.rsplit("/", 1)[-1], o, n, add, rem))
    pairs, used = [], set()
    for _, _, o, n, add, rem in sorted(scored):
        if o not in used and n not in used:
            used |= {o, n}
            pairs.append((o, n, add, rem))
    return pairs


def collect_uncommitted(wt: dict) -> list[tuple[dict, dict]]:
    """Egy worktree változásai ál-commitokként, a Git Graph mintájára: felül a még nem
    stage-elt (index → munkakönyvtár, a követetlen fájlokkal), alatta a stage-elt
    (HEAD → index) változások sora — amelyiknek van változása.

    A gráf tetejére kerülnek, láncban: a felső szülője az alsó, az alsóé a worktree
    HEAD-je — így szaggatott vonallal odalógnak, és a soron kattintva ugyanaz a
    részletek-panel nyílik, mint egy commitnál. A sha `*uncommitted:<worktree-slug>`,
    ill. `*staged:<worktree-slug>`: ebből tudja a `file_diff`, melyik munkakönyvtárat
    és melyik oldalát diffelje. A szerző a gép git-felhasználója (a worktree
    configjából), az idő a fájlok legutóbbi módosítása — a lap ez alapján teszi a
    helyére. Commit nélküli repóban nincs sor.
    """
    status = wt["status"]
    if not status or not wt["head"]:     # commit nélküli repó: nincs mihez kötni
        return []
    rows = []
    parent = wt["head"]
    if any(line[0] not in " ?" for line in status):      # az X oszlop: az index változása
        st = numstat_files(wt["staged"].splitlines())
        mark_new_dirs(wt, st["files"])
        mark_gone_dirs(wt, st["files"])
        rows.append(pending_row(wt, STAGED, "Stage-elt változások", parent, st))
        parent = rows[-1][0]["sha"]
    if any(line[1] != " " for line in status):           # az Y oszlop: a munkakönyvtár változása
        rows.append(pending_row(wt, UNCOMMITTED, "Nem commitolt változások", parent, unstaged_stats(wt, status)))
    return rows[::-1]


def unstaged_stats(wt: dict, status: list[str]) -> dict:
    """A még nem stage-elt változások (index → munkakönyvtár) fájlonként, a követetlenekkel."""
    st = numstat_files(wt["unstaged"].splitlines())
    files = st["files"]

    # A követetlen fájlokat a diff nem látja: a soraik száma a fájlból jön, és a
    # helyükre kerülnek (a git útvonal szerint rendez), nem a lista aljára.
    known = {f["path"] for f in files}
    untracked = [p for p in (line[3:].strip().strip('"') for line in status if line.startswith("??"))
                 if p not in known]
    # A még nem stage-elt átnevezés: a törölt és az új fájl egy sor (`pair_renames`).
    gone = {f["path"]: f for f in files if f.get("status") == "D" and not f["bin"]}
    for old, new, add, rem in pair_renames(wt["path"], "", list(gone), untracked):
        f = gone[old]
        st["add"], st["del"] = st["add"] + add, st["del"] - f["del"] + rem
        f.update({"path": rename_path(old, new), "add": add, "del": rem})
        del f["status"]
        untracked.remove(new)
    for path in untracked:
        lines = untracked_lines(wt["path"] / path)
        files.append({"path": path, "add": lines or 0, "del": 0, "bin": lines is None, "status": "A"})
        st["add"] += lines or 0
    files.sort(key=lambda f: numstat_new_path(f["path"]))
    mark_new_dirs(wt, files)
    mark_gone_dirs(wt, files)
    return st


def mark_new_dirs(wt: dict, files: list[dict]) -> None:
    """Új mappa: a HEAD-ben nincs."""
    added = [f for f in files if f.get("status") == "A"]
    mark_dirs([(f, wt["head"]) for f in added],
              missing_trees({f"{wt['head']}:{d}" for f in added for d in dir_prefixes(f["path"])}, wt["path"]))


def mark_gone_dirs(wt: dict, files: list[dict]) -> None:
    """Törölt mappa: nem maradt benne követett fájl (az index a még nem stage-elt
    törlést is tartalmazza, ezért a törölteket levonjuk)."""
    deleted = [f for f in files if f.get("status") == "D"]
    if not deleted:
        return
    gone = {f["path"] for f in deleted}
    dirs = {d for f in deleted for d in dir_prefixes(f["path"])}
    tracked = [p for p in git("ls-files", "--", *dirs, repo=wt["path"]).splitlines()
               if p not in gone] if dirs else []
    empty = {d for d in dirs if not any(p.startswith(d + "/") for p in tracked)}
    mark_dirs([(f, "") for f in deleted], {f":{d}" for d in empty})


def pending_row(wt: dict, kind: str, subject: str, parent: str, st: dict) -> tuple[dict, dict]:
    """Egy WIP ál-sor (`kind`: `UNCOMMITTED` vagy `STAGED`) és a fájlstatisztikája."""
    changed = last_change(wt["path"], st["files"])
    commit = {
        "sha": f"{kind}:{wt['slug']}",
        "short": "*",
        "parents": [parent],
        "author": user_config(wt["path"], "name") or "*",
        "email": user_config(wt["path"], "email"),
        "date": datetime.datetime.fromtimestamp(changed or time.time()).astimezone()
                .isoformat(timespec="seconds"),
        "refs": [],
        "subject": subject,
        "body": "",
        "uncommitted": True,
        "worktree": wt["slug"],
        "changed": changed,
    }
    if kind == STAGED:
        commit["staged"] = True
    return commit, st


def app_branch(wt: dict) -> str | None:
    """A leválasztott HEAD-ű hozzáadott worktree ága: a git nem jegyzi, a Claude app igen."""
    if wt["branch"] or (wt["path"] / ".git").is_dir():
        return None
    return app_worktree_branches().get(str(wt["path"].resolve()))


def collect_worktrees(repo: Path | None = None) -> list[dict]:
    """A repó (alapból a `REPO`) worktree-jei állapottal: worktree-nként `git status` + két
    `git diff --numstat` (stage-elt és még nem stage-elt).

    Párhuzamosan fut: 5 worktree-vel ~50 ms (sorban ~200 ms; nagy repón 330
    ms / 680 ms — mérve, docs/artifact-findings.md). A közben megszűnt worktree
    kimarad.
    """
    worktrees = worktree_list(repo)

    def fill(wt: dict) -> None:
        try:
            wt["status"] = [line for line in git("status", "--porcelain", "--untracked-files=all", repo=wt["path"])
                            .splitlines() if line.strip()]
            wt["staged"] = git("diff", "--cached", "--numstat", "--summary", repo=wt["path"]) if wt["head"] else ""
            wt["unstaged"] = git("diff", "--numstat", "--summary", repo=wt["path"]) if wt["head"] else ""
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
