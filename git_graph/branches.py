"""Az ágak: upstream, gazda-worktree (reflog) és a távolságaik az alapághoz és az upstreamhez."""
from __future__ import annotations

import re
import subprocess

from .gitio import FS, admin_dir, ahead_behind, git
from .worktrees import app_branch


def collect_branches(worktrees: list[dict]) -> list[dict]:
    """Ágak upstreammel, ahead/behind számokkal, és hogy melyik worktree-ben vannak kivéve."""
    fmt = FS.join(
        [
            "%(refname:short)",
            "%(objectname:short)",
            "%(upstream:short)",
            "%(upstream:track)",
            "%(committerdate:short)",
        ]
    )
    out = git("for-each-ref", f"--format={fmt}", "refs/heads")
    head = git("rev-parse", "--abbrev-ref", "HEAD").strip()
    checked_out = {wt["branch"]: wt["slug"] for wt in worktrees if wt["branch"]}
    owners = branch_owners(worktrees)
    branches = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, sha, upstream, track, date = (line.split(FS) + [""] * 5)[:5]
        branches.append(
            {
                "name": name,
                "sha": sha,
                "upstream": upstream,
                "track": track.strip("[]"),
                "date": date,
                "current": name == head,
                "worktree": checked_out.get(name),
                "owner": owners.get(name),
            }
        )
    # A csak remote-on élő ágak (aminek nincs helyi párja) is választhatók.
    paired = {b["upstream"] for b in branches if b["upstream"]}
    for line in git("for-each-ref", "--format=%(refname:short)" + FS + "%(objectname:short)"
                    + FS + "%(committerdate:short)", "refs/remotes").splitlines():
        name, sha, date = (line.split(FS) + [""] * 3)[:3]
        if name and not name.endswith("/HEAD") and "/" in name and name not in paired:
            branches.append({"name": name, "sha": sha, "date": date, "remote": True})
    return branches


def branch_owners(worktrees: list[dict]) -> dict[str, str]:
    """Ág → a worktree slugja, amelyikben utoljára ki volt véve.

    A git nem jegyzi, hol jött létre egy ág, de minden worktree HEAD-reflogja
    (`logs/HEAD`) igen, mikor váltott rá vagy róla (`checkout: moving from A to
    B`: az A-n is ott állt addig — a `worktree add -b` nem ír checkout-sort). A
    most kivett ág azé, ahol ki van véve; a leválasztott HEAD-ű worktree-é az
    ág, amit a Claude app jegyez neki (`appBranch`). A törölt worktree reflogja
    vele megy, és a lejárt bejegyzés is kiesik: az ilyen ág gazdátlan (nincs a
    kimenetben). Csak fájlt olvas, git-hívás nincs.
    """
    best: dict[str, tuple[float, str]] = {}
    pattern = re.compile(r"> (\d+) [+-]\d{4}\tcheckout: moving from (\S+) to (\S+)$")
    for wt in worktrees:
        claim = wt["branch"] or app_branch(wt)
        if claim:
            best[claim] = (float("inf"), wt["slug"])
        try:
            lines = (admin_dir(wt) / "logs" / "HEAD").read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            m = pattern.search(line)
            if not m:
                continue
            for name in (m[2], m[3]):
                if float(m[1]) > best.get(name, (-1.0, ""))[0]:
                    best[name] = (float(m[1]), wt["slug"])
    return {name: slug for name, (_, slug) in best.items()}


def branch_tracks(base: str) -> dict[str, dict]:
    """Ágankénti távolság (`ahead`, `behind`): `base` az alapághoz (amire az
    `origin/HEAD` mutat; magán az alapágon nincs; a remote-only ágaknak is,
    `origin/x` kulccsal; ha van helyi párja, `local` a helyi ághoz), `up` a saját upstreamjéhez
    (ha van, és nem tűnt el). Egyetlen `for-each-ref` (git 2.41+:
    `%(ahead-behind:…)`); régebbi gitnél ágankénti `rev-list`. A `base` a `default_base()`.

    Közös ős nélkül (pl. egy `git subtree split` / `push` remote-ja) a távolság a két
    oldal összes commitja volna: ilyenkor `base` helyett `unrelated: true`."""
    base_count: list[int] = []

    def to_base(counts: list[int]) -> dict:
        # Nincs közös ős ⇔ az alapág egyetlen commitja sem érhető el a refből, azaz a
        # lemaradás az alapág teljes commitszáma. A számlálás egyszer, és csak akkor fut,
        # ha van jelölt (mindkét irány nem nulla) — `merge-base` refenként nem kell.
        if counts[0] and counts[1]:
            if not base_count:
                base_count.append(int(git("rev-list", "--count", base).strip()))
            if counts[1] == base_count[0]:
                return {"unrelated": True}
        return {"base": counts}

    fields = "%(refname:short)%00%(upstream:short)%00%(upstream:track,nobracket)"
    try:
        lines = git("for-each-ref", f"--format={fields}%00%(ahead-behind:{base or 'HEAD'})",
                    "refs/heads").splitlines()
        rich = True
    except subprocess.CalledProcessError:
        lines, rich = git("for-each-ref", f"--format={fields}", "refs/heads").splitlines(), False
    out: dict[str, dict] = {}
    locals_: dict[str, list[int]] = {}             # upstream neve → távolsága a helyi ágtól
    for line in lines:
        name, upstream, track, *rest = line.split("\0")
        entry: dict = {}
        if upstream and track != "gone":
            ahead = re.search(r"ahead (\d+)", track)
            behind = re.search(r"behind (\d+)", track)
            entry["up"] = [int(ahead.group(1)) if ahead else 0, int(behind.group(1)) if behind else 0]
            locals_[upstream] = entry["up"][::-1]     # a remote chipjén: a helyi ághoz mérve
        if base and base.split("/", 1)[-1] != name:
            entry.update(to_base([int(n) for n in rest[0].split()] if rich and rest
                                 else ahead_behind(base, name)))
        out[name] = entry
    # A csak remote-on élő ágaknak is (`origin/x`): a távolságuk az alapágtól.
    if base:
        try:
            for line in git("for-each-ref", f"--format=%(refname:short)%00%(ahead-behind:{base})",
                            "refs/remotes").splitlines():
                name, counts = line.split("\0")
                if name.endswith("/HEAD") or name in out:
                    continue
                a, b = counts.split()
                # Az alapág remote-jának nincs base-szakasza (önmaga), de a helyi párjához mérve igen.
                out[name] = {} if name == base else to_base([int(a), int(b)])
                if name in locals_:
                    out[name]["local"] = locals_[name]
        except (subprocess.CalledProcessError, ValueError):
            pass                              # régi git: a remote-only chip szám nélkül marad
    return out
