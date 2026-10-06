"""A lap adatcsomagja (`graph_data`): commitok, sávok, élek, worktree-k, ágak."""
from __future__ import annotations

import datetime
import hashlib
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .avatars import avatars_for
from .claude_app import app_worktree_branches
from .gitio import (FS, RS, admin_dir, ahead_behind, default_base, git, numstat_new_path, remotes, repo_name,
                    repo_url, worktree_list)
from .page import attach_icons
from .registry import slug_for


def collect_commits(limit: int | None) -> list[dict]:
    """Commitok minden refről, szülőkkel, ref-dekorációval és törzzsel."""
    fmt = FS.join(["%H", "%P", "%an", "%ae", "%aI", "%cI", "%D", "%s", "%b"])
    args = ["log", "--all", "--date-order", f"--pretty=format:{RS}{fmt}"]
    if limit:
        args.append(f"-{limit}")
    raw = git(*args)

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


REF_ORDER = {"head": 0, "detached": 0, "branch": 1, "remote": 2, "tag": 3}


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


def collect_stats(limit: int | None) -> dict[str, dict]:
    """Fájlonkénti +/− soronként, commitra bontva (`--numstat`).

    A merge commit az első szülőjéhez képest: amit a merge a fő ágra hozott
    (alapból a git a merge-hez nem ad numstatot).
    """
    args = ["log", "--all", "--date-order", "--numstat", "--diff-merges=first-parent",
            f"--pretty=format:{RS}%H"]
    if limit:
        args.append(f"-{limit}")
    raw = git(*args)

    stats: dict[str, dict] = {}
    for block in raw.split(RS):
        if not block.strip():
            continue
        lines = block.strip().splitlines()
        sha = lines[0].strip()
        files = []
        added = deleted = 0
        for line in lines[1:]:
            if not line.strip():
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
        stats[sha] = {"files": files, "add": added, "del": deleted}
    return stats


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
            latest = max(latest, int((root / f["path"].rstrip("/")).stat().st_mtime))
        except OSError:
            pass
    return latest


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
    files, added, deleted = [], 0, 0
    for line in wt["numstat"].splitlines():
        cols = line.split("\t")
        if len(cols) < 3:
            continue
        a, d, path = cols[0], cols[1], cols[2]
        ai = int(a) if a.isdigit() else 0
        di = int(d) if d.isdigit() else 0
        added += ai
        deleted += di
        files.append({"path": path, "add": ai, "del": di, "bin": not a.isdigit()})

    # A követetlen fájlokat a diff nem látja — számok helyett „új" jelöléssel.
    known = {f["path"] for f in files}
    for line in status:
        if line.startswith("??"):
            path = line[3:].strip().strip('"')
            if path not in known:
                files.append({"path": path, "add": 0, "del": 0, "bin": False, "new": True})

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
    return commit, {"files": files, "add": added, "del": deleted}


def assign_lanes(commits: list[dict], trunk: str | None = None) -> list[dict]:
    """Sávkiosztás: minden commit kap egy oszlopot, a szülők sávot foglalnak.

    A Git Graph logikája: egy commit abba a sávba ül, amelyik már rá vár
    (a gyereke foglalta le); ha nincs ilyen, az első szabad sávba. Az első
    szülő ugyanabban a sávban folytatódik, a további szülők (merge) új vagy
    már létező sávot kapnak.

    A `trunk` (a fő checkout csúcsa) a 0. sávot kapja előre lefoglalva: a
    worktree-k újabb commitjai így mindig elágaznak tőle, nem a fő vonalon ülnek.
    """
    index = {c["sha"]: i for i, c in enumerate(commits)}
    active: list[str | None] = [trunk] if trunk in index else []  # sávonként: melyik commitra vár

    for commit in commits:
        sha = commit["sha"]
        lane = next((i for i, h in enumerate(active) if h == sha), None)
        if lane is None:
            lane = next((i for i, h in enumerate(active) if h is None), None)
            if lane is None:
                active.append(None)
                lane = len(active) - 1
        commit["lane"] = lane

        # Ha több sáv is erre a commitra várt, a többi felszabadul (összefutás).
        for i, h in enumerate(active):
            if h == sha and i != lane:
                active[i] = None

        parents = commit["parents"]
        if not parents:
            active[lane] = None
            continue
        active[lane] = parents[0]
        for parent in parents[1:]:
            existing = next((i for i, h in enumerate(active) if h == parent), None)
            if existing is None:
                slot = next((i for i, h in enumerate(active) if h is None), None)
                if slot is None:
                    active.append(None)
                    slot = len(active) - 1
                active[slot] = parent

    # Élek: gyerek → szülő, sáv- és sorindexekkel (a rajzoláshoz).
    edges = []
    for row, commit in enumerate(commits):
        for order, parent in enumerate(commit["parents"]):
            prow = index.get(parent)
            if prow is None:
                continue  # a szülő a limiten kívülre esett
            edges.append(
                {
                    "fromRow": row,
                    "fromLane": commit["lane"],
                    "toRow": prow,
                    "toLane": commits[prow]["lane"],
                    "merge": order > 0,
                }
            )
    return edges


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
            wt["status"] = [line for line in git("status", "--porcelain", repo=wt["path"])
                            .splitlines() if line.strip()]
            wt["numstat"] = git("diff", "--numstat", "HEAD", repo=wt["path"]) if wt["head"] else ""
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


def collect_meta(commits: list[dict], worktrees: list[dict]) -> dict:
    base = default_base()
    return {
        "repo": repo_name(),
        "repoUrl": repo_url(),
        "head": git("rev-parse", "--abbrev-ref", "HEAD").strip(),
        "totalCommits": int(git("rev-list", "--all", "--count").strip()),
        "shown": len(commits),
        "dirty": len(worktrees[0]["status"]) if worktrees else 0,
        "generated": git("log", "-1", "--pretty=format:%aI").strip(),
        "worktrees": [worktree_meta(wt, base) for wt in worktrees],
        "remotes": sorted(remotes()),     # több remote-nál a badge a nevüket is mutatja
        "tracks": branch_tracks(base),
        "base": base,                     # az alapág (origin/HEAD célja) — a helyi párján nem dolgozunk
    }


def branch_tracks(base: str) -> dict[str, dict]:
    """Ágankénti távolság (`ahead`, `behind`): `base` az alapághoz (amire az
    `origin/HEAD` mutat; magán az alapágon nincs; a remote-only ágaknak is,
    `origin/x` kulccsal; ha van helyi párja, `local` a helyi ághoz), `up` a saját upstreamjéhez
    (ha van, és nem tűnt el). Egyetlen `for-each-ref` (git 2.41+:
    `%(ahead-behind:…)`); régebbi gitnél ágankénti `rev-list`. A `base` a `default_base()`."""
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
            entry["base"] = ([int(n) for n in rest[0].split()] if rich and rest
                             else ahead_behind(base, name))
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
                out[name] = {} if name == base else {"base": [int(a), int(b)]}
                if name in locals_:
                    out[name]["local"] = locals_[name]
        except (subprocess.CalledProcessError, ValueError):
            pass                              # régi git: a remote-only chip szám nélkül marad
    return out


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


def worktree_lanes_last(commits: list[dict], edges: list[dict], worktrees: list[dict]) -> None:
    """A hozzáadott worktree-k oszlopai a fő checkout ágai mögé kerülnek — de csak
    a worktree-k elágazási pontja fölött.

    Az oszlopok cseréje (permutáció) a rajzot nem rontja el. Az elágazás alatt
    viszont az oszlopot már más ág (pl. egy régi, beolvasztott ág) használja:
    ott az eredeti sorrend marad, különben az a vonal is hátrébb csúszna, és egy
    oszlop (szín) kimaradna. A határon átnyúló vonal a következő commitja
    fölött fordul be az eredeti oszlopába.
    """
    by_sha = {c["sha"]: c for c in commits}
    row_of = {c["sha"]: i for i, c in enumerate(commits)}
    cols: list[int] = []
    boundary = 0                              # az első sor, ahol már az eredeti oszlopok élnek
    for wt in worktrees:
        if wt["main"]:
            continue
        for key in (f"{UNCOMMITTED}:{wt['slug']}", wt["head"] or ""):
            c = by_sha.get(key)
            if not c or c["lane"] == 0:
                continue
            if c["lane"] not in cols:
                cols.append(c["lane"])
            # Az elágazási pont: az első szülő-lánc első commitja, ami már nem ebben az oszlopban ül.
            lane = c["lane"]
            while c is not None and c["lane"] == lane and c["parents"]:
                c = by_sha.get(c["parents"][0])
            boundary = max(boundary, row_of[c["sha"]] if c is not None else len(commits))
    if not cols:
        return
    count = max(c["lane"] for c in commits) + 1
    order = [lane for lane in range(count) if lane not in cols] + cols
    new = {old: i for i, old in enumerate(order)}
    lane_at = lambda row, lane: new[lane] if row < boundary else lane  # noqa: E731
    for row, c in enumerate(commits):
        c["lane"] = lane_at(row, c["lane"])
    for e in edges:
        e["fromLane"] = lane_at(e["fromRow"], e["fromLane"])
        e["toLane"] = lane_at(e["toRow"], e["toLane"])


def worktree_stubs(commits: list[dict], edges: list[dict], worktrees: list[dict]) -> None:
    """Saját commit és WIP nélküli worktree HEAD-je: leágazó csonk a commitjáról.

    Ha a worktree HEAD-je egy más által is használt commiton áll (a trunkon,
    egy továbbmenő ág közepén, vagy ahol másik HEAD is van — pl. a session
    törlésekor leválasztott worktree), a worktree nem ágazna el. A commit
    `stubs` listát kap: a sávok utáni első szabad oszloptól, commitonként újra
    kezdve; a lap vonallal és pöttyel rajzolja, a HEAD-badge ennek a színét kapja.
    """
    row_of = {c["sha"]: i for i, c in enumerate(commits)}
    has_child = {(e["toRow"], e["fromLane"]) for e in edges if not e["merge"]}
    heads: dict[str, int] = {}
    for wt in worktrees:
        heads[wt["head"] or ""] = heads.get(wt["head"] or "", 0) + 1
    lanes = max((c["lane"] for c in commits), default=-1) + 1
    for wt in worktrees:
        row = row_of.get(wt["head"] or "")
        if wt["main"] or row is None or f"{UNCOMMITTED}:{wt['slug']}" in row_of:
            continue
        c = commits[row]
        own = c["lane"] != 0 and (row, c["lane"]) not in has_child and heads[wt["head"]] == 1
        if not own:
            # Commitonként a következő szabad oszloptól: a csonk a soron belül marad,
            # más sorok csonkjaival nem ütközik — a gráf nem szélesedik feleslegesen.
            stubs = c.setdefault("stubs", [])
            stubs.append({"lane": lanes + len(stubs), "worktree": wt["slug"]})


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
    fold_remote_heads(commits)

    # Worktree-nként egy ál-sor, a gráf tetejére, a HEAD-jük fölé — a lane-kiosztás
    # előtt, mert az élek sorindexeket használnak.
    trunk = None
    for wt in reversed(worktrees):
        pending = collect_uncommitted(wt)
        if pending:
            commit, churn = pending
            commits.insert(0, commit)
            stats[commit["sha"]] = churn
        if wt["main"]:                    # a fő checkout csúcsa: az ál-sora, vagy a HEAD-je
            trunk = commit["sha"] if pending else wt["head"]

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

