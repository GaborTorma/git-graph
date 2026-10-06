"""Fájl-diff (a lenyitott fájlsor): hunkok, sorpárok, szószintű kiemelés."""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from .gitio import git, numstat_new_path, numstat_old_path, worktree_list
from .graph import UNCOMMITTED_RE
from .registry import slug_for

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")
TOKEN_RE = re.compile(r"\w+|\s+|[^\w\s]")
DIFF_MAX_LINES = 3000           # egy lockfile ne fagyassza meg a lapot
PAIR_MAX_CELLS = 10000          # e fölött (pl. 100×100-as blokk) nincs hasonlóság-illesztés
PAIR_MIN_RATIO = 0.6            # ennél hasonlóbb sorpár számít „ugyanannak a sornak"


def mark_words(old: dict, new: dict) -> None:
    """Egy cserélt sorpár szó-szintű különbsége: `hl` = [[kezdet, vég], …] karakterben."""
    a, b = TOKEN_RE.findall(old["s"]), TOKEN_RE.findall(new["s"])
    old["hl"], new["hl"] = [], []
    pos_a = [0]
    for t in a:
        pos_a.append(pos_a[-1] + len(t))
    pos_b = [0]
    for t in b:
        pos_b.append(pos_b[-1] + len(t))
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            continue
        if i2 > i1:
            old["hl"].append([pos_a[i1], pos_a[i2]])
        if j2 > j1:
            new["hl"].append([pos_b[j1], pos_b[j2]])


def pair_lines(dels: list, adds: list) -> list:
    """Törölt és hozzáadott sorok párosítása: [(törölt index, hozzáadott index), …].

    Előbb a hasonló sorok illeszkednek, sorrendtartóan (a hasonlóságok összegét
    maximalizáló DP) — így egy beszúrt sor nem csúsztatja el a többi párt, ha
    a git pl. az átszámozás miatt az egész listát cserének látja. A horgonyok
    közti maradék sorok pozíció szerint párosodnak (módosított sor). Nagy
    blokknál csak a pozíció szerinti párosítás marad.
    """
    m, n = len(dels), len(adds)
    anchors: list = []
    if m and n and m * n <= PAIR_MAX_CELLS:
        sim = [[0.0] * n for _ in range(m)]
        for d in range(m):
            sm = difflib.SequenceMatcher(None, autojunk=False)
            sm.set_seq2(dels[d]["s"])
            for a in range(n):
                sm.set_seq1(adds[a]["s"])
                if sm.real_quick_ratio() >= PAIR_MIN_RATIO and sm.quick_ratio() >= PAIR_MIN_RATIO:
                    r = sm.ratio()
                    if r >= PAIR_MIN_RATIO:
                        sim[d][a] = r
        best = [[0.0] * (n + 1) for _ in range(m + 1)]
        for d in range(m - 1, -1, -1):
            for a in range(n - 1, -1, -1):
                best[d][a] = max(best[d + 1][a], best[d][a + 1],
                                 best[d + 1][a + 1] + sim[d][a] if sim[d][a] else 0.0)
        d = a = 0
        while d < m and a < n:
            if sim[d][a] and best[d][a] == best[d + 1][a + 1] + sim[d][a]:
                anchors.append((d, a))
                d, a = d + 1, a + 1
            elif best[d][a] == best[d + 1][a]:
                d += 1
            else:
                a += 1
    pairs, d0, a0 = [], 0, 0
    for d1, a1 in anchors + [(m, n)]:
        pairs += [(d0 + x, a0 + x) for x in range(min(d1 - d0, a1 - a0))]
        if d1 < m:
            pairs.append((d1, a1))
        d0, a0 = d1 + 1, a1 + 1
    return pairs


def parse_diff(raw: str) -> dict:
    """Egyfájlos unified diff → hunkok soronként, a lap ebből rajzol.

    Sor: `t` (` `/`+`/`-`), `n` (a törölt sornál a régi, máskor az új sorszám),
    `s` (szöveg), cserélt sorpárnál `hl` (a változott szakaszok). A hunk `old`
    kezdete adja a lapon a kihagyott („unmodified") sorok számát.
    """
    hunks: list[dict] = []
    binary = truncated = False
    count = 0
    old_no = new_no = 0
    for line in raw.splitlines():
        m = HUNK_RE.match(line)
        if m:
            old_no, new_no = int(m[1]), int(m[2])
            hunks.append({"old": old_no, "lines": []})
            continue
        if not hunks:
            binary = binary or line.startswith("Binary files")
            continue
        tag = line[:1]
        if tag not in (" ", "+", "-"):
            continue                          # „\ No newline at end of file"
        if count >= DIFF_MAX_LINES:
            truncated = True
            break
        count += 1
        if tag == "-":
            n, old_no = old_no, old_no + 1
        elif tag == "+":
            n, new_no = new_no, new_no + 1
        else:
            n, old_no, new_no = new_no, old_no + 1, new_no + 1
        hunks[-1]["lines"].append({"t": tag, "n": n, "s": line[1:]})

    # Egy törölt blokk és a rá következő hozzáadott blokk sorait párba állítjuk
    # (`pair_lines`): a pár a side-by-side nézetben egy sorba kerül (`p` a
    # törölt sornál: a párja indexe a hunkban), és szó-szinten vetjük össze.
    for h in hunks:
        lines, i = h["lines"], 0
        while i < len(lines):
            if lines[i]["t"] != "-":
                i += 1
                continue
            j = i
            while j < len(lines) and lines[j]["t"] == "-":
                j += 1
            k = j
            while k < len(lines) and lines[k]["t"] == "+":
                k += 1
            for d, a in pair_lines(lines[i:j], lines[j:k]):
                lines[i + d]["p"] = j + a
                mark_words(lines[i + d], lines[j + a])
            i = k
    return {"hunks": hunks, "binary": binary, "truncated": truncated}


def untracked_diff(root: Path, path: str) -> dict:
    """Követetlen fájl: a git nem diffeli, minden sora hozzáadott."""
    try:
        text = (root / path).read_bytes()[:2_000_000].decode("utf-8")
    except UnicodeDecodeError:
        return {"hunks": [], "binary": True, "truncated": False}
    lines = text.splitlines()
    truncated = len(lines) > DIFF_MAX_LINES
    rows = [{"t": "+", "n": i + 1, "s": s} for i, s in enumerate(lines[:DIFF_MAX_LINES])]
    return {"hunks": [{"old": 0, "lines": rows}] if rows else [], "binary": False,
            "truncated": truncated}


def file_diff(sha: str, path: str) -> dict:
    """Egy fájl diffje a commitban (vagy egy Uncommitted ál-sorban: a worktree HEAD-jéhez képest).

    A `sha` és a `path` a lapról jön: a sha csak hex lehet (különben `--opció`-ként
    futna), az ál-soré `*uncommitted:<slug>`, és a slug csak egy élő worktree-é
    lehet; a fájlt pedig csak akkor olvassuk közvetlenül, ha a git követetlennek
    mondja — így a lapon át nem olvasható ki tetszőleges fájl.
    """
    old, new = numstat_old_path(path), numstat_new_path(path)
    pending = UNCOMMITTED_RE.match(sha)
    if pending:
        slug = pending[1]
        root = next((wt["path"] for wt in worktree_list()
                     if slug in (None, slug_for(wt["path"]))), None)
        if root is None:
            raise ValueError(f"nincs ilyen worktree: {slug}")
        raw = git("diff", "--no-color", "--no-ext-diff", "-M", "HEAD", "--", old, new, repo=root)
        if not raw.strip() and path.endswith("/"):      # a status így mutat egy új mappát
            return {"hunks": [], "binary": False, "truncated": False,
                    "note": "követetlen mappa — a fájljai a git add után látszanak"}
        if not raw.strip() and path in git("ls-files", "--others", "--exclude-standard",
                                           "--", path, repo=root).splitlines():
            return untracked_diff(root, path)
    elif SHA_RE.match(sha):
        raw = git("show", "--format=", "--no-color", "--no-ext-diff", "-M",
                  "--diff-merges=first-parent", sha, "--", old, new)
    else:
        raise ValueError(f"érvénytelen commit: {sha!r}")
    return parse_diff(raw)

