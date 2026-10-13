"""Commitonkénti fájlstatisztika (`--numstat`): +/−, új és törölt fájl, új és kiürült mappa."""
from __future__ import annotations

import re
from pathlib import Path

from .gitio import RS, git


def collect_stats(limit: int | None) -> dict[str, dict]:
    """Fájlonkénti +/− soronként, commitra bontva (`--numstat`).

    A merge commit az első szülőjéhez képest: amit a merge a fő ágra hozott
    (alapból a git a merge-hez nem ad numstatot).
    """
    args = ["log", "--all", "--date-order", "--numstat", "--summary", "--diff-merges=first-parent",
            f"--pretty=format:{RS}%H %P"]
    if limit:
        args.append(f"-{limit}")
    raw = git(*args)

    stats: dict[str, dict] = {}
    checks: list[tuple[dict, str]] = []
    for block in raw.split(RS):
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        sha, *parents = lines[0].split()
        stats[sha] = numstat_files(lines[1:])
        # Új mappa: az első szülőben nem volt; törölt: a commitban már nincs.
        for f in stats[sha]["files"]:
            if f.get("status") == "D":
                checks.append((f, sha))
            elif f.get("status") == "A":
                if parents:
                    checks.append((f, parents[0]))
                else:                                # gyökércommit: minden mappája új
                    f["dirFrom"] = 0
    mark_dirs(checks, missing_trees({f"{rev}:{d}" for f, rev in checks for d in dir_prefixes(f["path"])}))
    return stats


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


SUMMARY_RE = re.compile(r"^ (create|delete) mode \d+ (.+)$")
SUMMARY_STATUS = {"create": "A", "delete": "D"}


def numstat_files(lines: list[str]) -> dict:
    """A `--numstat --summary` kimenete fájlonként: +/− és az új (`A`) / törölt (`D`)
    állapot (`status`; a `--summary` `create` / `delete mode` sorából)."""
    files, status = [], {}
    added = deleted = 0
    for line in lines:
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
