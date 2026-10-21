"""A lap adatcsomagja (`graph_data`): commitok, refek, és az összerakás — a sávok, a
worktree-k, az ágak és a fájlstatisztika a saját moduljukban."""
from __future__ import annotations

import hashlib
import re
import subprocess
from datetime import datetime

from .avatars import avatars_for
from .branches import branch_tracks, collect_branches
from .gitio import ALL_BUT_STASH, FS, RS, default_base, git, numstat_new_path, remotes, repo_name, repo_url, stash_list
from .lanes import assign_lanes, worktree_lanes_last, worktree_stubs
from .page import attach_icons
from .stats import collect_stats, mark_sizes
from .worktrees import collect_uncommitted, collect_worktrees, worktree_meta


COMMIT_FMT = FS.join(["%H", "%P", "%an", "%ae", "%aI", "%cI", "%D", "%s", "%b"])


def collect_commits(limit: int | None) -> list[dict]:
    """Commitok minden refről, szülőkkel, ref-dekorációval és törzzsel; köztük a stash-ek."""
    args = ["log", *ALL_BUT_STASH, "--date-order", f"--pretty=format:{RS}{COMMIT_FMT}"]
    if limit:
        args.append(f"-{limit}")
    return insert_stashes(parse_commits(git(*args)), stash_commits())


def parse_commits(raw: str) -> list[dict]:
    commits: list[dict] = []
    for record in raw.split(RS):
        if not record.strip():
            continue
        parts = record.split(FS)
        if len(parts) < 9:
            continue
        sha, parents, author, email, date, committed, refs, subject, body = parts[:9]
        commits.append(
            {
                "sha": sha.strip(),
                "short": sha.strip()[:7],
                "parents": parents.split() if parents.strip() else [],
                "author": author,
                "email": email,       # az avatar kulcsa
                "date": date,
                # Mikor került a repóba (amend, rebase is frissít) — a friss-kiemelésé.
                "committed": committed,
                "refs": parse_refs(refs),
                "subject": subject,
                "body": body.strip(),
            }
        )
    return commits


STASH_ON_RE = re.compile(r"(?:WIP on|On) (.+?): ")


def stash_commits() -> list[dict]:
    """A stash-ek (`git stash list`, a legújabb elöl), mint a VS Code Git Graph-ban: egy
    sor, egyetlen szülővel — a bázissal (`^1`); az index- és a követetlen-commit
    (`^2`, `^3`) nem sor és nem sáv. A chipje `stash`, a neve `stash@{N}`; a `branch`
    az ág, amelyen készült (az üzenetéből: `On <ág>: …`, `WIP on <ág>: …`) — a lap
    ebből tudja, melyik worktree-é."""
    stashes = parse_commits(stash_list(f"--pretty=format:{RS}{COMMIT_FMT}"))
    for n, c in enumerate(stashes):
        on = STASH_ON_RE.match(c["subject"])
        c.update(parents=c["parents"][:1], refs=[{"kind": "stash", "name": f"stash@{{{n}}}"}], stash=True,
                 branch=on[1] if on and on[1] != "(no branch)" else None)
    return stashes


def committed_at(c: dict) -> datetime:
    # A `%cI` UTC-nél `Z`-vel végződik: a Python 3.9 `fromisoformat`-ja nem ismeri.
    return datetime.fromisoformat(c["committed"].replace("Z", "+00:00"))


def insert_stashes(commits: list[dict], stashes: list[dict]) -> list[dict]:
    """A stash-ek a `--date-order` szerinti helyükre: az első nem újabb commit elé, de
    legkésőbb a bázisuk elé. Ha a bázis és a helyük is a limiten túl van, kimaradnak."""
    shas = {c["sha"] for c in commits}
    times = [committed_at(c) for c in commits]
    for st in reversed(stashes):                 # a régebbi előbb: az újabb fölé kerül, azonos időnél is
        if st["sha"] in shas:
            continue
        end = len(commits)
        base = next((i for i, c in enumerate(commits) if c["sha"] == st["parents"][0]), end)
        when = committed_at(st)
        at = next((i for i, t in enumerate(times) if t <= when), end)
        if base == end and at == end:
            continue
        commits.insert(min(at, base), st)
        times.insert(min(at, base), when)
    return commits


REF_ORDER = {"head": 0, "detached": 0, "branch": 1, "remote": 2, "tag": 3, "stash": 4}


def parse_refs(decoration: str) -> list[dict]:
    """A `%D` dekoráció badge-ekké: HEAD, lokális ág, remote ág, tag."""
    refs: list[dict] = []
    for item in (r.strip() for r in decoration.split(",")):
        if not item:
            continue
        if item.startswith("tag: "):
            refs.append({"kind": "tag", "name": item[5:]})
        elif " -> " in item:  # "HEAD -> main"
            head, _, branch = item.partition(" -> ")
            refs.append({"kind": "head", "name": branch})
            del head
        elif item == "HEAD":
            refs.append({"kind": "detached", "name": "HEAD"})
        elif item.startswith("origin/") or "/" in item and item.split("/")[0] in remotes():
            refs.append({"kind": "remote", "name": item})
        else:
            refs.append({"kind": "branch", "name": item})
    # A HEAD-badge megy előre, utána az ágak, a remote-ok, a tag mindig a végén.
    refs.sort(key=lambda r: REF_ORDER.get(r["kind"], 9))
    return refs


def collect_meta(commits: list[dict], worktrees: list[dict]) -> dict:
    base = default_base()
    return {
        "repo": repo_name(),
        "repoUrl": repo_url(),
        "head": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "totalCommits": int(git("rev-list", *ALL_BUT_STASH, "--count").strip())
        + sum(1 for c in commits if c.get("stash")),
        "shown": len(commits),
        "dirty": len(worktrees[0]["status"]) if worktrees else 0,
        "generated": git("log", "-1", "--pretty=format:%aI").strip(),
        "worktrees": [worktree_meta(wt, base) for wt in worktrees],
        "remotes": sorted(remotes()),     # több remote-nál a badge a nevüket is mutatja
        "tracks": branch_tracks(base),
        "base": base,                     # az alapág (origin/HEAD célja) — a helyi párján nem dolgozunk
    }


def mark_pushed(commits: list[dict], stats: dict[str, dict]) -> None:
    """Az `origin` által ismert commitok linkelhetők a GitHubra — a pusholatlan 404-et adna.

    A fájlokhoz a GitHub commit-oldalának diff-horgonya kerül
    (`#diff-<az új út sha256-ja>`), hogy a lap valódi, kész `href`-et írhasson.
    (Az Artifact nem tárol adatot, így a méret itt nem számít.)
    """
    pushed = set(git("rev-list", "--remotes=origin").split())
    for c in commits:
        if c["sha"] not in pushed:
            continue
        c["pushed"] = True
        for f in stats.get(c["sha"], {}).get("files", []):
            f["anchor"] = hashlib.sha256(numstat_new_path(f["path"]).encode()).hexdigest()


def mark_worktree_heads(commits: list[dict], worktrees: list[dict]) -> None:
    """Minden worktree HEAD-je badge-et kap (`head`, illetve `detached`), a worktree slugjával.

    A `%D` dekoráció csak a `REPO` (a fő checkout) HEAD-jét ismeri — a
    worktree-k közös lapján mindegyiké kell, a lap ebből jelöli a sajátját.
    """
    by_sha = {c["sha"]: c for c in commits}
    for c in commits:
        c["refs"] = [dict(r, kind="branch") if r["kind"] == "head" else r
                     for r in c["refs"] if r["kind"] != "detached"]
    for wt in worktrees:
        c = by_sha.get(wt["head"] or "")
        if c is None:
            continue                       # a limiten kívül
        ref = next((r for r in c["refs"] if r["kind"] == "branch" and r["name"] == wt["branch"]), None)
        if ref:
            ref.update(kind="head", worktree=wt["slug"])
        else:
            c["refs"].insert(0, {"kind": "detached", "name": "HEAD", "worktree": wt["slug"]})
    for c in commits:
        c["refs"].sort(key=lambda r: REF_ORDER.get(r["kind"], 9))


def mark_stash_owners(commits: list[dict], worktrees: list[dict]) -> None:
    """A stash gazdája (`owner`, worktree-slug): ahol az ága (`branch`) ki van véve, ha
    egyikben sincs, a fő checkout. A stash a bázisáról mindenhonnan elérhető, ezért a
    halványítás és a sáv ebből dönt, nem az elérhetőségből."""
    main = next((wt["slug"] for wt in worktrees if wt["main"]), None)
    by_branch = {wt["branch"]: wt["slug"] for wt in worktrees if wt["branch"]}
    for c in commits:
        if c.get("stash"):
            c["owner"] = by_branch.get(c["branch"], main)


def fold_remote_heads(commits: list[dict]) -> None:
    """A `<remote>/HEAD` nem külön badge: csak mutató a remote alapértelmezett ágára.

    A célja (pl. `origin/main`) `default` jelet kap, a lap a tooltipben mondja
    ki; maga a mutató kikerül — ahol a cél látszik, ott ismétlés lenne.
    """
    targets = set()
    for remote in remotes():
        try:
            targets.add(git("symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD").strip())
        except subprocess.CalledProcessError:
            pass
    for c in commits:
        c["refs"] = [r for r in c["refs"]
                     if not (r["kind"] == "remote" and r["name"].endswith("/HEAD"))]
        for r in c["refs"]:
            if r["kind"] == "remote" and r["name"] in targets:
                r["default"] = True


def collect_payload(limit: int | None) -> dict:
    """A lap teljes adatcsomagja — a `git-graph --mcp` graph_data toolja adja."""
    commits = collect_commits(limit)
    if not commits:
        return {}
    stats = collect_stats(limit)
    worktrees = collect_worktrees()
    meta = collect_meta(commits, worktrees)   # még a valódi commitokból: `shown`
    if meta["repoUrl"]:
        mark_pushed(commits, stats)
    mark_worktree_heads(commits, worktrees)
    mark_stash_owners(commits, worktrees)
    fold_remote_heads(commits)

    # Worktree-nként legfeljebb két ál-sor (nem stage-elt, stage-elt), a gráf tetejére,
    # a HEAD-jük fölé — a lane-kiosztás előtt, mert az élek sorindexeket használnak.
    trunk = None
    for wt in reversed(worktrees):
        pending = collect_uncommitted(wt)
        for commit, churn in reversed(pending):
            commits.insert(0, commit)
            stats[commit["sha"]] = churn
        if wt["main"]:                    # a fő checkout csúcsa: a felső ál-sora, vagy a HEAD-je
            trunk = pending[0][0]["sha"] if pending else wt["head"]

    mark_sizes(stats)
    edges = assign_lanes(commits, trunk)
    worktree_lanes_last(commits, edges, worktrees)
    worktree_stubs(commits, edges, worktrees)
    return {
        "commits": commits,
        "edges": edges,
        "stats": stats,
        "branches": collect_branches(worktrees),
        "meta": meta,
        "avatars": avatars_for(commits, meta["repoUrl"]),
        "fileIcons": attach_icons(stats),
    }
