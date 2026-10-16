"""Fájl-diff (a lenyitott fájlsor): hunkok, sorpárok, szószintű kiemelés."""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from .gitio import git, numstat_new_path, numstat_old_path, worktree_list
from .registry import slug_for
from .worktrees import UNCOMMITTED_RE, head_lines, read_lines

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
SHA_RE = re.compile(r"^[0-9a-f]{7,64}$")
TOKEN_RE = re.compile(r"\w+|\s+|[^\w\s]")
LIST_RE = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")    # listaelem eleje
# a markdown blokkjainak eleje, a lap `mdBlocks`-a szerint (md-diff.js, MD_*)
MD_FENCE_RE = re.compile(r"\s{0,3}(`{3,}|~{3,})")
MD_HEAD_RE = re.compile(r"\s{0,3}(?:#{1,6}(?:\s|$)|([-*_])(?:\s*\1){2,}\s*$)")   # címsor, vonal
MD_KIND_RE = re.compile(r"\s*(\|)|\s{0,3}(>)")                                      # táblázat, idézet
DIFF_MAX_LINES = 3000           # egy lockfile ne fagyassza meg a lapot
FULL_CONTEXT = "-U1000000"      # a teljes fájl egy hunkban (a renderelt Markdown-diffhez)
PAIR_MAX_CELLS = 10000          # e fölött (pl. 100×100-as blokk) nincs hasonlóság-illesztés
PAIR_MIN_RATIO = 0.6            # ennél hasonlóbb sorpár számít „ugyanannak a sornak"
PARA_MIN_RATIO = 0.4            # ennél hasonlóbb bekezdéspár (a szavaik szerint) párosodik
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


def match_blocks(a: list, b: list, row_a: list, row_b: list) -> list:
    """A két tokensor közös szakaszai: [(i, j, hossz), …], sorrendben.

    Mint a `SequenceMatcher` (a leghosszabb közös szakasz, majd két oldalán
    ugyanígy), de holtversenyben nem az első előfordulás nyer, hanem amelyik az
    előző egyezéstől mindkét oldalon ugyanannyi sorra van (`row_*`: a token
    sora). Egy ismétlődő szó (pl. két sorban ugyanaz a hivatkozás) így a vele
    egy sorban álló párjához illeszkedik. A más sorra eső, szó nélküli egyezés
    (pl. egy pont) nem számít.
    """
    b2j: dict = {}
    for j, t in enumerate(b):
        b2j.setdefault(t, []).append(j)
    blocks, queue = [], [(0, len(a), 0, len(b))]
    while queue:
        alo, ahi, blo, bhi = queue.pop()
        # a viszonyítási pont az előző egyezés vége (a tartomány előtti token)
        ref_a, ref_b = row_a[alo - 1] if alo else 0, row_b[blo - 1] if blo else 0
        best, size, j2len = (0, 0, 0), 0, {}
        for i in range(alo, ahi):
            grown = {}
            for j in b2j.get(a[i], ()):
                if j < blo:
                    continue
                if j >= bhi:
                    break
                k = grown[j] = j2len.get(j - 1, 0) + 1
                if k >= size:
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


def paragraphs(lines: list) -> list:
    """A sorok bekezdései (az üres sor határ, magában nem bekezdés): [[sorindex, …], …]."""
    out: list = [[]]
    for i, line in enumerate(lines):
        if line["s"].strip():
            out[-1].append(i)
        elif out[-1]:
            out.append([])
    return [p for p in out if p]


def list_items(lines: list, para: list) -> list:
    """Egy bekezdés listaelemei (a listaelemek közt nincs üres sor): [[sorindex, …], …]."""
    out: list = []
    for i in para:
        if not out or LIST_RE.match(lines[i]["s"]):
            out.append([])
        out[-1].append(i)
    return out


def pair_paragraphs(wa: list, wb: list) -> list:
    """Bekezdéspárok a szavaik hasonlósága szerint, sorrendtartóan (`pair_lines`)."""
    psim = [[0.0] * len(wb) for _ in wa]
    if len(wa) * len(wb) <= PAIR_MAX_CELLS:
        for x, ws in enumerate(wa):
            sm = difflib.SequenceMatcher(None, autojunk=False)
            sm.set_seq2(ws)
            for y, wt in enumerate(wb):
                sm.set_seq1(wt)
                if sm.real_quick_ratio() >= PARA_MIN_RATIO and sm.quick_ratio() >= PARA_MIN_RATIO:
                    r = sm.ratio()
                    psim[x][y] = r if r >= PARA_MIN_RATIO else 0.0
    return pair_lines(wa, wb, psim)


def by_items(dels: list, adds: list, pa: list, pb: list, words) -> list:
    """A pár nélküli bekezdések listaelemenként párosítva: [(törölt sorok, hozzáadott sorok), …].

    Egy listában az elemek közé szúrt új elemek a bekezdést annyira
    megváltoztatják, hogy nincs párja; az elemei viszont párosodnak.
    """
    ia = [it for p in pa for it in list_items(dels, p)]
    ib = [it for p in pb for it in list_items(adds, p)]
    pairs = pair_paragraphs([words(0, it) for it in ia], [words(1, it) for it in ib])
    return [(ia[x], ib[y]) for x, y in pairs]


def mark_prose(dels: list, adds: list) -> list | None:
    """Szöveges fájl cserélt blokkja bekezdésenként, szó-szinten: a sortörés csak szóköz.

    Előbb a bekezdések párosodnak (a szavaik hasonlósága szerint, sorrendtartóan,
    mint a `pair_lines`) — így egy átszámozás vagy egy törölt bekezdés nem
    csúsztatja el a többit; a pár nélküli bekezdések listaelemenként is
    (`by_items`) —, aztán a párok szavai illeszkednek (`match_blocks`).
    Egy bekezdés újratördelése így nem változás: csak a valóban cserélt szavak
    kapnak `hl`-t, soronként; a pár nélküli bekezdés, és amelyik sorból egy szó
    sem maradt, egészében változott (nincs `hl`). A visszaadott mátrix a
    sorpárok közös (nem szóköz) karaktereinek száma: ebből párosít a
    `pair_lines`. Túl nagy blokknál `None` (marad a soronkénti összevetés).
    """
    ta, tb = [TOKEN_RE.findall(line["s"]) for line in dels], [TOKEN_RE.findall(line["s"]) for line in adds]
    if sum(map(len, ta + tb)) > 2 * PROSE_MAX_TOKENS:
        return None

    def tokens(found: list, idx: list) -> tuple:
        toks, line_of, pos, row = [], [], [], []
        for r, i in enumerate(idx):
            if r:
                toks.append("\n")
                line_of.append(None)
                pos.append(None)
                row.append(r - 1)           # a sortörés az előző sor vége
            at = 0
            for n, t in enumerate(found[i]):
                if r and not n and t.isspace():  # a folytatósor behúzása a sortöréshez tartozik
                    at += len(t)
                    continue
                toks.append(t)
                line_of.append(i)
                pos.append(at)
                row.append(r)
                at += len(t)
        return toks, line_of, pos, row

    def mark(lines: list, line_of: list, pos: list, toks: list, i1: int, i2: int) -> None:
        for k in range(i1, i2):
            if line_of[k] is None:
                continue
            hl, end = lines[line_of[k]]["hl"], pos[k] + len(toks[k])
            if hl and hl[-1][1] == pos[k]:
                hl[-1][1] = end
            else:
                hl.append([pos[k], end])

    norm = lambda toks: [" " if t.isspace() else t for t in toks]   # noqa: E731
    for line in dels + adds:
        line["hl"] = []
    sim = [[0] * len(adds) for _ in dels]
    pa, pb = paragraphs(dels), paragraphs(adds)
    side = (ta, tb)
    words = lambda s, idx: [t for i in idx for t in side[s][i] if not t.isspace()]  # noqa: E731
    pairs = pair_paragraphs([words(0, p) for p in pa], [words(1, p) for p in pb])
    units = [(pa[x], pb[y]) for x, y in pairs]
    done_a, done_b = {x for x, _ in pairs}, {y for _, y in pairs}
    left_a = [p for x, p in enumerate(pa) if x not in done_a]
    left_b = [p for y, p in enumerate(pb) if y not in done_b]
    if left_a and left_b:
        units += by_items(dels, adds, left_a, left_b, words)
    for ua, ub in units:
        a, line_a, pos_a, row_a = tokens(ta, ua)
        b, line_b, pos_b, row_b = tokens(tb, ub)
        for op, i1, i2, j1, j2 in opcodes(match_blocks(norm(a), norm(b), row_a, row_b), len(a), len(b)):
            if op == "equal":
                for k in range(i2 - i1):
                    if not a[i1 + k].isspace():
                        sim[line_a[i1 + k]][line_b[j1 + k]] += len(a[i1 + k])
                continue
            mark(dels, line_a, pos_a, a, i1, i2)
            mark(adds, line_b, pos_b, b, j1, j2)
    # amelyik sorból egy szó sem maradt meg (vagy a bekezdése pár nélküli), az
    # egészében változott: nincs `hl`-je; az üres sor nem változás
    for d, line in enumerate(dels):
        if not any(sim[d]) and line["s"].strip():
            del line["hl"]
    for j, line in enumerate(adds):
        if not any(row[j] for row in sim) and line["s"].strip():
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


def join_runs(lines: list) -> list:
    """Szöveges fájlban a csak üres sorokkal elválasztott változások egybe.

    A git az üres sorok mentén apró darabokra vágja a változást; egy átszámozott
    vagy átrendezett szövegnél így a bekezdés és a párja más darabba kerül. Az
    összevont darab: előbb a régi oldal (a köztes üres sor törölt), aztán az új
    (ugyanaz az üres sor hozzáadott) — ezen párosodnak a bekezdések.
    """
    out, i = [], 0
    while i < len(lines):
        if lines[i]["t"] == " ":
            out.append(lines[i])
            i += 1
            continue
        j = end = i
        while j < len(lines) and (lines[j]["t"] != " " or not lines[j]["s"].strip()):
            j += 1
            if lines[j - 1]["t"] != " ":
                end = j                       # a záró üres sorok környezetek maradnak
        seg = lines[i:end]
        if any(ln["t"] == " " for ln in seg):
            seg = ([ln if ln["t"] == "-" else {"t": "-", "n": ln["o"], "s": ln["s"]} for ln in seg if ln["t"] != "+"]
                   + [ln if ln["t"] == "+" else {"t": "+", "n": ln["n"], "s": ln["s"]} for ln in seg if ln["t"] != "-"])
        out += seg
        i = end
    return out


def parse_diff(raw: str, prose: bool = False, md: bool = False) -> dict:
    """Egyfájlos unified diff → hunkok soronként, a lap ebből rajzol.

    Sor: `t` (` `/`+`/`-`), `n` (a törölt sornál a régi, máskor az új sorszám),
    `s` (szöveg), cserélt sorpárnál `p` (a párja indexe a hunkban, mindkét
    irányban) és `hl` (a változott szakaszok), változott sornál `w` (az
    állapota, `mark_state`) és `v` (a megjelenése, `mark_looks`). A hunk `old`
    kezdete adja a lapon a kihagyott („unmodified") sorok számát. `prose`:
    szöveges fájl: a csak üres sorral elválasztott változások egyben
    (`join_runs`), a bekezdések és a szavaik a `mark_prose` szerint. `md`: a
    renderelt markdown-nézetnek, a sorok a blokkok sorrendjében (`md_order`).
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
        if prose and tag == " ":
            hunks[-1]["lines"][-1]["o"] = old_no - 1      # a régi sorszám (`join_runs`-nak)

    if prose:
        for h in hunks:
            h["lines"] = join_runs(h["lines"])
            for ln in h["lines"]:
                ln.pop("o", None)

    # Egy törölt blokk és a rá következő hozzáadott blokk sorait párba állítjuk
    # (`pair_lines`): a pár a side-by-side nézetben egy sorba kerül (`p`: a
    # párja indexe a hunkban), és szó-szinten vetjük össze.
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
                lines[i + d]["p"], lines[j + a]["p"] = j + a, i + d
                if sim is None:
                    mark_words(lines[i + d], lines[j + a])
            i = k
        for line in lines:
            mark_state(line)
        mark_looks(lines)
        if md:
            h["lines"] = md_order(lines)
    return {"hunks": hunks, "binary": binary, "truncated": truncated}


def runs(lines: list) -> list:
    """A változások: [(i, j, k), …] — a `lines[i:j]` törölt, a `lines[j:k]` hozzáadott sorok
    (bármelyik üres lehet), két változatlan sor között."""
    out, i = [], 0
    while i < len(lines):
        if lines[i]["t"] == " ":
            i += 1
            continue
        j = i
        while j < len(lines) and lines[j]["t"] == "-":
            j += 1
        k = j
        while k < len(lines) and lines[k]["t"] == "+":
            k += 1
        out.append((i, j, k))
        i = k
    return out


def mark_looks(lines: list) -> None:
    """A változott sorok megjelenése a lapon (`v`): `drop` — érintetlen (a szavai mind
    megvannak a másik oldalon), egymás alatt kimarad, side-by-side-ban változatlanként
    látszik; `only` — a párja érintetlen: semleges háttér, csak a változott szavai
    színesek; `same` — maga sem változott (újratördelés), változatlanként látszik.
    Egy változásban: ha az egyik oldala egészében érintetlen (csak beszúrás / csak
    törlés, vagy mindkettő: tiszta újratördelés), az az oldal; különben páronként
    (pl. egy táblázat egyetlen sorában csak törlés, a többiben csere). Az egészében
    új / törölt sor (`whole`) teljes színű marad (nincs `v`-je)."""
    kept = {"words": "only", "same": "same"}
    for i, j, k in runs(lines):
        if i == j or j == k:
            continue
        drop = ("-" if all(ln["w"] == "same" for ln in lines[i:j])
                else "+" if all(ln["w"] == "same" for ln in lines[j:k]) else None)
        if drop:
            for ln in lines[i:k]:
                v = "drop" if ln["t"] == drop else kept.get(ln["w"])
                if v:
                    ln["v"] = v
            continue
        for d in range(i, j):
            if "p" not in lines[d]:
                continue
            old, new = lines[d], lines[lines[d]["p"]]
            x, y = (old, new) if old["w"] == "same" else (new, old) if new["w"] == "same" else (None, None)
            if x:
                x["v"] = "drop"
                if y["w"] in kept:
                    y["v"] = kept[y["w"]]


def md_starts(lines: list) -> set:
    """A törölt oldal markdown-blokkjainak első sorai (a lap `mdBlocks`-a szerint): az üres
    sor utáni, a kerítés, a címsor, a vonal, a listaelem, és ahol a sor fajtája
    (táblázat, idézet, szöveg) vált; a kódblokk belseje nem."""
    out: set = set()
    fence, prev = None, None
    for i, ln in enumerate(lines):
        s = ln["s"]
        if ln["t"] == "+":
            continue
        if fence:
            if s.strip().startswith(fence):
                fence = None
            continue
        if not s.strip():
            prev = None
            continue
        m = MD_KIND_RE.match(s)
        kind = "table" if m and m[1] else "quote" if m else "text"
        fence = (MD_FENCE_RE.match(s) or [None, None])[1]
        head = MD_HEAD_RE.match(s)
        if (prev in (None, "head") or fence or head or LIST_RE.match(s)
                or kind != prev and not (prev == "quote" and kind == "text")):
            out.add(i)
        prev = "head" if head else kind
    return out


def md_order(lines: list) -> list:
    """A sorok a renderelt markdown blokkjainak sorrendjében. Egy változásban előbb az
    összes törölt, aztán az összes hozzáadott sor jön (`join_runs`; egy átrendezett
    szövegnél sok bekezdésnyi): itt minden törölt blokk (`md_starts`: bekezdés,
    listaelem, címsor, …) után jönnek a párjai, az előttük álló pár nélküli új sorok
    pedig a blokk elé — így a pár nélküli új blokk a helyén marad (a köztes törölt
    blokkok után), nem csúszik a törölt rész végére. A `p` az új sorrendhez igazodik."""
    starts, order, done = md_starts(lines), [], 0
    for i, j, k in runs(lines):
        order += range(done, i)
        a, p = j, i
        while p < j:                     # törölt blokk: a sorai, utána az üres sorok
            q = p + 1
            while q < j and lines[q]["s"].strip() and q not in starts:
                q += 1
            while q < j and not lines[q]["s"].strip():
                q += 1
            paired = [lines[x]["p"] for x in range(p, q) if lines[x].get("p", -1) >= a]
            if paired:
                lo, hi = min(paired), max(paired) + 1
                order += [*range(a, lo), *range(p, q), *range(lo, hi)]
                a = hi
            else:
                order += range(p, q)
            p = q
        order += range(a, k)
        done = k
    order += range(done, len(lines))
    at = {old: new for new, old in enumerate(order)}
    out = [lines[x] for x in order]
    for ln in out:
        if "p" in ln:
            ln["p"] = at[ln["p"]]
    return out


def mark_state(line: dict) -> None:
    """A változott sor állapota a lapnak (`w`): `same` — a szavai mind megvannak a
    másik oldalon (vagy üres sor), `words` — szavai változtak (`hl`), `whole` —
    egészében új / törölt (pár és közös szó nélkül)."""
    if line["t"] != " ":
        line["w"] = ("same" if not line["s"].strip() or line.get("hl") == []
                     else "words" if line.get("hl") else "whole")


def untracked_diff(root: Path, path: str) -> dict:
    """Követetlen fájl: a git nem diffeli, minden sora hozzáadott."""
    try:
        text = (root / path).read_bytes()[:2_000_000].decode("utf-8")
    except UnicodeDecodeError:
        return {"hunks": [], "binary": True, "truncated": False}
    lines = text.splitlines()
    truncated = len(lines) > DIFF_MAX_LINES
    rows = [{"t": "+", "n": i + 1, "s": s} for i, s in enumerate(lines[:DIFF_MAX_LINES])]
    for row in rows:
        mark_state(row)
    return {"hunks": [{"old": 0, "lines": rows}] if rows else [], "binary": False,
            "truncated": truncated}


def renamed_diff(root: Path, old: str, new: str, full: bool) -> dict | None:
    """Még nem stage-elt átnevezés (az indexbeli `old` → követetlen `new`, ahogy a WIP-sor
    párosította): a két tartalom különbsége, a `difflib`-bel — a git ezt index nélkül
    nem diffeli. Ha a pár nem áll (nincs az indexben, vagy bináris): `None`."""
    a, b = head_lines(root, "", old), read_lines(root / new)
    if a is None or b is None:
        return None
    raw = "\n".join(difflib.unified_diff(a, b, lineterm="", n=1000000 if full else 3))
    prose = Path(new).suffix.lower() in PROSE_SUFFIXES
    return parse_diff(raw, prose, full and prose)


def file_diff(sha: str, path: str, full: bool = False) -> dict:
    """Egy fájl diffje a commitban, vagy egy WIP ál-sorban: a nem stage-elté az indexhez,
    a stage-elté (`*staged:<slug>`) a HEAD-hez képest.

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
        kind, slug = pending[1], pending[2]
        root = next((wt["path"] for wt in worktree_list()
                     if slug in (None, slug_for(wt["path"]))), None)
        if root is None:
            raise ValueError(f"nincs ilyen worktree: {slug}")
        if kind == "staged":
            raw = git("diff", "--no-color", "--no-ext-diff", "-M", *context, "--cached", "--", old, new,
                      repo=root)
        else:
            untracked = git("ls-files", "--others", "--exclude-standard", "--", new, repo=root).splitlines()
            if old != new and new in untracked:
                paired = renamed_diff(root, old, new, full)
                if paired is not None:
                    return paired
            raw = git("diff", "--no-color", "--no-ext-diff", "-M", *context, "--", old, new, repo=root)
            if not raw.strip() and path in untracked:
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
    prose = Path(path).suffix.lower() in PROSE_SUFFIXES
    return parse_diff(raw, prose, full and prose)

