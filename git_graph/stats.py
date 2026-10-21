"""Commitonkénti fájlstatisztika (`--numstat`): +/−, új és törölt fájl, új és kiürült mappa."""
from __future__ import annotations

import re
from pathlib import Path

from .gitio import ALL_BUT_STASH, RS, git, numstat_new_path, numstat_old_path, stash_list


def collect_stats(limit: int | None) -> dict[str, dict]:
    """Fájlonkénti +/− soronként, commitra bontva (`--numstat`).

    A merge commit az első szülőjéhez képest: amit a merge a fő ágra hozott
    (alapból a git a merge-hez nem ad numstatot). A stash is: a bázisához képest, és
    a `-u`-val félretett követetlen fájljai (`untracked_stashed`) új fájlként.
    """
    opts = ["--numstat", "--summary", "--diff-merges=first-parent", f"--pretty=format:{RS}%H %P"]
    args = ["log", *ALL_BUT_STASH, "--date-order", *opts]
    if limit:
        args.append(f"-{limit}")
    stashes = stash_list(*opts)
    raw = git(*args) + stashes

    stats: dict[str, dict] = {}
    checks: list[tuple[dict, str]] = []
    for block in raw.split(RS):
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        sha, *parents = lines[0].split()
        stats[sha] = numstat_files(lines[1:])
        # A bináris fájl mérete (`mark_sizes`): az első szülőben és a commitban.
        # Új mappa: az első szülőben nem volt; törölt: a commitban már nincs.
        for f in stats[sha]["files"]:
            if f["bin"]:
                f["size"] = [None if f.get("status") == "A" or not parents else [f"{parents[0]}:{numstat_old_path(f['path'])}"],
                             None if f.get("status") == "D" else [f"{sha}:{numstat_new_path(f['path'])}"]]
            if f.get("status") == "D":
                checks.append((f, sha))
            elif f.get("status") == "A":
                if parents:
                    checks.append((f, parents[0]))
                else:                                # gyökércommit: minden mappája új
                    f["dirFrom"] = 0
    checks += untracked_stashed(stashes, stats)
    mark_dirs(checks, missing_trees({f"{rev}:{d}" for f, rev in checks for d in dir_prefixes(f["path"])}))
    return stats


def untracked_stashed(stashes: str, stats: dict[str, dict]) -> list[tuple[dict, str]]:
    """A `stash -u` követetlen fájljai a stash fájllistájába, új fájlként (`A`).

    Ezek nem a stash commitban vannak, hanem a harmadik szülőjében (`^3`, `untracked
    files on …`): egy szülő nélküli commitban, amelyben csak ők vannak — a bázishoz
    mért diffből ezért kimaradnának. Egyetlen `log --no-walk`-kal, a gyökér-diffjükből.
    A visszaadott párok a `mark_dirs`-é: az új mappa a bázishoz képest új.
    """
    owner: dict[str, tuple[str, str]] = {}        # ^3 → (stash, bázis)
    for block in stashes.split(RS):
        if not block.strip():
            continue
        sha, *parents = block.strip().splitlines()[0].split()
        if len(parents) == 3:
            owner[parents[2]] = (sha, parents[0])
    if not owner:
        return []
    raw = git("log", "--no-walk=unsorted", "--numstat", "--summary", f"--pretty=format:{RS}%H", *owner)
    checks = []
    for block in raw.split(RS):
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        stash, base = owner[lines[0].strip()]
        extra = numstat_files(lines[1:])
        for f in extra["files"]:
            if f["bin"]:
                f["size"] = [None, [f"{lines[0].strip()}:{f['path']}"]]
        st = stats[stash]
        st["files"] += extra["files"]
        st["add"] += extra["add"]
        st["del"] += extra["del"]
        checks += [(f, base) for f in extra["files"]]
    return checks


def dir_prefixes(path: str) -> list[str]:
    """A fájl mappái kívülről befelé, `/` nélkül: `a/b/c.txt` → `a`, `a/b`."""
    return [path[:i] for i, ch in enumerate(path) if ch == "/"]


def missing_trees(specs: set[str], repo: Path | None = None) -> set[str]:
    """A `<rev>:<mappa>` alakú hivatkozások közül a nem létezők — egyetlen `cat-file`-lal."""
    if not specs:
        return set()
    order = sorted(specs)
    out = git("cat-file", "--batch-check", repo=repo, stdin="\n".join(order) + "\n").splitlines()
    return {spec for spec, line in zip(order, out) if line.endswith(" missing")}


def mark_dirs(checks: list[tuple[dict, str]], missing: set[str]) -> None:
    """Az új / törölt fájl útvonalában az első új / törölt mappa kezdete (`dirFrom`,
    karakterindex): onnan a mappa-előtag is a fájl színét kapja a lapon."""
    for f, rev in checks:
        for d in dir_prefixes(f["path"]):
            if f"{rev}:{d}" in missing:
                f["dirFrom"] = d.rfind("/") + 1
                break


def mark_sizes(stats: dict[str, dict]) -> None:
    """A bináris fájlok mérete (`size`: [régi, új] bájtban, a hiányzó oldal `None`). A
    `collect_stats` és a WIP-sorok oldalanként a forrást teszik a `size`-ba: objektumnevek
    listája (`<rev>:<út>` vagy blob), az első meglévő számít, vagy a lemez fájlja (`Path`).
    Az objektumok mérete az összes sorra egyetlen `cat-file --batch-check`-kel (a
    worktree-k objektumtára közös)."""
    sides = [f["size"] for st in stats.values() for f in st["files"] if "size" in f]
    names = sorted({n for side in sides for spec in side if isinstance(spec, list) for n in spec if "\n" not in n})
    found = {}
    if names:
        out = git("cat-file", "--batch-check", stdin="\n".join(names) + "\n").splitlines()
        found = {n: int(line.rsplit(" ", 1)[1]) for n, line in zip(names, out) if not line.endswith(" missing")
                 and line.rsplit(" ", 1)[1].isdigit()}
    for side in sides:
        for i, spec in enumerate(side):
            if isinstance(spec, Path):
                try:
                    side[i] = spec.stat().st_size
                except OSError:
                    side[i] = None
            elif spec is not None:
                side[i] = next((found[n] for n in spec if n in found), None)


SUMMARY_RE = re.compile(r"^ (create|delete) mode \d+ (.+)$")
SUMMARY_STATUS = {"create": "A", "delete": "D"}


def numstat_files(lines: list[str]) -> dict:
    """A `--numstat --summary` kimenete fájlonként: +/− és az új (`A`) / törölt (`D`)
    állapot (`status`; a `--summary` `create` / `delete mode` sorából)."""
    files, status = [], {}
    added = deleted = 0
    for line in lines:
        if line.startswith(":"):                    # a `--raw` sora (a WIP-soroké): `raw_blobs`
            continue
        m = SUMMARY_RE.match(line)
        if m:
            status[m.group(2)] = SUMMARY_STATUS[m.group(1)]
            continue
        cols = line.split("\t")
        if len(cols) < 3:
            continue
        a, d, path = cols[0], cols[1], cols[2]
        # Bináris fájlnál a git "-" jelet ad szám helyett.
        ai = int(a) if a.isdigit() else 0
        di = int(d) if d.isdigit() else 0
        added += ai
        deleted += di
        files.append({"path": path, "add": ai, "del": di, "bin": not a.isdigit()})
    for f in files:
        if f["path"] in status:
            f["status"] = status[f["path"]]
    return {"files": files, "add": added, "del": deleted}
