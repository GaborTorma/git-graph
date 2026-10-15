"""Fájl-diff (a lenyitott fájlsor): hunkok, sorpárok, szószintű kiemelés."""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from .gitio import git, numstat_new_path, numstat_old_path, worktree_list
from .registry import slug_for
from .worktrees import UNCOMMITTED_RE

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")
TOKEN_RE = re.compile(r"\w+|\s+|[^\w\s]")
PARAGRAPH = "\n\n"              # a szöveges blokk bekezdéshatára (üres sor) tokenként
DIFF_MAX_LINES = 3000           # egy lockfile ne fagyassza meg a lapot
FULL_CONTEXT = "-U1000000"      # a teljes fájl egy hunkban (a renderelt Markdown-diffhez)
PAIR_MAX_CELLS = 10000          # e fölött (pl. 100×100-as blokk) nincs hasonlóság-illesztés
PAIR_MIN_RATIO = 0.6            # ennél hasonlóbb sorpár számít „ugyanannak a sornak"
PROSE_SUFFIXES = {".md", ".markdown", ".mdx", ".txt", ".rst", ".adoc"}
PROSE_MAX_TOKENS = 20000        # e fölött a szöveges blokk is soronként párosodik


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


def match_blocks(a: list, b: list, row_a: list, row_b: list, par_a: list, par_b: list) -> list:
    """A két tokensor közös szakaszai: [(i, j, hossz), …], sorrendben.

    Mint a `SequenceMatcher` (a leghosszabb közös szakasz, majd két oldalán
    ugyanígy), de holtversenyben nem az első előfordulás nyer, hanem amelyik az
    előző egyezéstől mindkét oldalon ugyanannyi sorra van (`row_*`: a token
    sora). Egy ismétlődő szó (pl. két sorban ugyanaz a hivatkozás) így a vele
    egy sorban álló párjához illeszkedik. A más sorra eső, szó nélküli egyezés
    (pl. egy pont) nem számít, és az sem, amelyik az előző egyezéstől a két
    oldalon más bekezdésre (`par_*`: az üres sorok száma) esik — a bekezdés
    egység, a szavai nem vándorolnak át egy másikba.
    """
    b2j: dict = {}
    for j, t in enumerate(b):
        b2j.setdefault(t, []).append(j)
    blocks, queue = [], [(0, len(a), 0, len(b))]
    while queue:
        alo, ahi, blo, bhi = queue.pop()
        # a viszonyítási pont az előző egyezés vége (a tartomány előtti token)
        ref_a, ref_b = row_a[alo - 1] if alo else 0, row_b[blo - 1] if blo else 0
        pref_a, pref_b = par_a[alo - 1] if alo else 0, par_b[blo - 1] if blo else 0
        best, size, j2len = (0, 0, 0), 0, {}
        for i in range(alo, ahi):
            grown = {}
            for j in b2j.get(a[i], ()):
                if j < blo:
                    continue
                if j >= bhi:
                    break
                k = grown[j] = j2len.get(j - 1, 0) + 1
                if k >= size and par_a[i - k + 1] - pref_a == par_b[j - k + 1] - pref_b:
                    off = abs((row_a[i - k + 1] - ref_a) - (row_b[j - k + 1] - ref_b))
                    if k > size or off < best[2]:
                        best, size = (i - k + 1, j - k + 1, off), k
            j2len = grown
        i, j, off = best
        # egy másik sorra eső, szó nélküli egyezés (írásjel, szóköz) véletlen
        if size and (off == 0 or any(t[:1].isalnum() or t[:1] == "_" for t in a[i:i + size])):
            blocks.append((i, j, size))
            if alo < i and blo < j:
                queue.append((alo, i, blo, j))
            if i + size < ahi and j + size < bhi:
                queue.append((i + size, ahi, j + size, bhi))
    return sorted(blocks)


def opcodes(blocks: list, n: int, m: int) -> list:
    """A közös szakaszokból a `get_opcodes` formája (csak `equal` / nem `equal` számít)."""
    ops, i, j = [], 0, 0
    for ai, bj, size in [*blocks, (n, m, 0)]:
        if i < ai or j < bj:
            ops.append(("replace", i, ai, j, bj))
        if size:
            ops.append(("equal", ai, ai + size, bj, bj + size))
        i, j = ai + size, bj + size
    return ops


def mark_prose(dels: list, adds: list) -> list | None:
    """Szöveges fájl cserélt blokkja egyben, szó-szinten: a sortörés csak szóköz, az üres sor bekezdéshatár.

    Egy bekezdés újratördelése így nem változás — csak a valóban cserélt szavak
    kapnak `hl`-t, soronként. A visszaadott mátrix a sorpárok közös
    (nem szóköz) karaktereinek száma: ebből párosít a `pair_lines`. Túl nagy
    blokknál `None` (marad a soronkénti összevetés).
    """
    def tokens(lines: list) -> tuple:
        toks, line_of, pos, row, par = [], [], [], [], []
        blank = [not line["s"].strip() for line in lines]
        pars = [sum(blank[:i + 1]) for i in range(len(lines))]      # az üres sorok száma eddig
        for i, line in enumerate(lines):
            if i:
                # az üres sor körüli sortörés bekezdéshatár: nem szóköz, csak önmagával egyezik
                toks.append(PARAGRAPH if blank[i] or blank[i - 1] else "\n")
                line_of.append(None)
                pos.append(None)
                row.append(i - 1)           # a sortörés az előző sor vége
                par.append(pars[i - 1])
            at = 0
            for t in TOKEN_RE.findall(line["s"]):
                toks.append(t)
                line_of.append(i)
                pos.append(at)
                row.append(i)
                par.append(pars[i])
                at += len(t)
        return toks, line_of, pos, row, par

    a, line_a, pos_a, row_a, par_a = tokens(dels)
    b, line_b, pos_b, row_b, par_b = tokens(adds)
    if len(a) > PROSE_MAX_TOKENS or len(b) > PROSE_MAX_TOKENS:
        return None
    norm = lambda toks: [" " if t.isspace() and t != PARAGRAPH else t for t in toks]   # noqa: E731
    for line in dels + adds:
        line["hl"] = []
    sim = [[0] * len(adds) for _ in dels]

    def mark(lines: list, line_of: list, pos: list, toks: list, i1: int, i2: int) -> None:
        for k in range(i1, i2):
            if line_of[k] is None:
                continue
            hl, end = lines[line_of[k]]["hl"], pos[k] + len(toks[k])
            if hl and hl[-1][1] == pos[k]:
                hl[-1][1] = end
            else:
                hl.append([pos[k], end])

    blocks = match_blocks(norm(a), norm(b), row_a, row_b, par_a, par_b)
    for op, i1, i2, j1, j2 in opcodes(blocks, len(a), len(b)):
        if op == "equal":
            for k in range(i2 - i1):
                if not a[i1 + k].isspace():
                    sim[line_a[i1 + k]][line_b[j1 + k]] += len(a[i1 + k])
            continue
        mark(dels, line_a, pos_a, a, i1, i2)
        mark(adds, line_b, pos_b, b, j1, j2)
    # amelyik sorból egy szó sem maradt meg, az egészében változott: nincs `hl`-je
    for d, line in enumerate(dels):
        if not any(sim[d]):
            del line["hl"]
    for j, line in enumerate(adds):
        if not any(row[j] for row in sim):
            del line["hl"]
    return sim


def pair_lines(dels: list, adds: list, sim: list | None = None) -> list:
    """Törölt és hozzáadott sorok párosítása: [(törölt index, hozzáadott index), …].

    Előbb a hasonló sorok illeszkednek, sorrendtartóan (a hasonlóságok összegét
    maximalizáló DP) — így egy beszúrt sor nem csúsztatja el a többi párt, ha
    a git pl. az átszámozás miatt az egész listát cserének látja. A horgonyok
    közti maradék sorok pozíció szerint párosodnak (módosított sor). Nagy
    blokknál csak a pozíció szerinti párosítás marad. A `sim` kész hasonlóság
    (szöveges fájlnál a `mark_prose` közös karakterei): ott a közös szó nélküli
    maradék sorok nem párok.
    """
    m, n = len(dels), len(adds)
    prose, anchors = sim is not None, []
    if m and n and m * n <= PAIR_MAX_CELLS and sim is None:
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
    if m and n and m * n <= PAIR_MAX_CELLS and sim is not None:
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
        # szöveges fájlban a közös szó nélküli sorok nem párok: a sor egészében törölt / új
        pairs += [(d0 + x, a0 + x) for x in range(min(d1 - d0, a1 - a0)) if not prose or sim[d0 + x][a0 + x]]
        if d1 < m:
            pairs.append((d1, a1))
        d0, a0 = d1 + 1, a1 + 1
    return pairs


def parse_diff(raw: str, prose: bool = False) -> dict:
    """Egyfájlos unified diff → hunkok soronként, a lap ebből rajzol.

    Sor: `t` (` `/`+`/`-`), `n` (a törölt sornál a régi, máskor az új sorszám),
    `s` (szöveg), cserélt sorpárnál `hl` (a változott szakaszok). A hunk `old`
    kezdete adja a lapon a kihagyott („unmodified") sorok számát. `prose`:
    szöveges fájl, a cserélt blokk szavai egyben (`mark_prose`).
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
            sim = mark_prose(lines[i:j], lines[j:k]) if prose and j < k else None
            for d, a in pair_lines(lines[i:j], lines[j:k], sim):
                lines[i + d]["p"] = j + a
                if sim is None:
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


def file_diff(sha: str, path: str, full: bool = False) -> dict:
    """Egy fájl diffje a commitban (vagy egy Uncommitted ál-sorban: a worktree HEAD-jéhez képest).

    `full`: a változatlan sorok is mind benne vannak (egyetlen hunk) — a lap
    ebből rendereli a Markdown-fájlt, a blokkjai csak a teljes szövegből jók.
    A `sha` és a `path` a lapról jön: a sha csak hex lehet (különben `--opció`-ként
    futna), az ál-soré `*uncommitted:<slug>`, és a slug csak egy élő worktree-é
    lehet; a fájlt pedig csak akkor olvassuk közvetlenül, ha a git követetlennek
    mondja — így a lapon át nem olvasható ki tetszőleges fájl.
    """
    old, new = numstat_old_path(path), numstat_new_path(path)
    context = [FULL_CONTEXT] if full else []
    pending = UNCOMMITTED_RE.match(sha)
    if pending:
        slug = pending[1]
        root = next((wt["path"] for wt in worktree_list()
                     if slug in (None, slug_for(wt["path"]))), None)
        if root is None:
            raise ValueError(f"nincs ilyen worktree: {slug}")
        raw = git("diff", "--no-color", "--no-ext-diff", "-M", *context, "HEAD", "--", old, new,
                  repo=root)
        if not raw.strip() and path in git("ls-files", "--others", "--exclude-standard",
                                           "--", path, repo=root).splitlines():
            return untracked_diff(root, path)
    elif SHA_RE.match(sha):
        raw = git("show", "--format=", "--no-color", "--no-ext-diff", "-M",
                  "--diff-merges=first-parent", *context, sha, "--", old, new)
        # A `stash -u` követetlen fájlja a harmadik szülőben (`^3`) van, nem a bázishoz
        # mért diffben; csak stash-nél — egy octopus merge `^3`-a valódi szülő.
        if not raw.strip():
            parents = {line.split()[0]: line.split()[1:]
                       for line in git("stash", "list", "--format=%H %P").splitlines()}.get(sha, [])
            if len(parents) == 3:
                raw = git("show", "--format=", "--no-color", "--no-ext-diff", *context,
                          parents[2], "--", new)
    else:
        raise ValueError(f"érvénytelen commit: {sha!r}")
    return parse_diff(raw, Path(path).suffix.lower() in PROSE_SUFFIXES)

