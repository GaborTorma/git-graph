"""Sávkiosztás: a commitok oszlopa, az élek, a worktree-k oszlopai és csonkjai."""
from __future__ import annotations

from .worktrees import UNCOMMITTED


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
