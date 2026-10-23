"""Fájl-diff (`diff`): hunkok, sorpárok, szószintű kiemelés, a lapról jövő bemenet szűrése."""
from __future__ import annotations

import json

from helpers import HomeTestCase, git_in

RAW = """diff --git a/x b/x
--- a/x
+++ b/x
@@ -3,4 +3,4 @@ fej
 marad
-régi sor egy
+új sor egy
 marad2
\\ No newline at end of file
"""


def marks(line: dict) -> list:
    """A sor kiemelt (`hl`) szakaszai szövegként."""
    return [line["s"][a:b] for a, b in line["hl"]]


class DiffTest(HomeTestCase):
    def prose_lines(self, raw: str) -> list:
        """Egy szöveges fájl egyhunkos diffjének sorai."""
        return self.load().diff.parse_diff(raw, prose=True)["hunks"][0]["lines"]

    def test_parse_diff(self) -> None:
        """Sorszámok, a cserélt sorpár (`p`) és a szó-szintű különbség (`hl`)."""
        gg = self.load()
        out = gg.diff.parse_diff(RAW)
        self.assertFalse(out["binary"] or out["truncated"])
        (hunk,) = out["hunks"]
        self.assertEqual(hunk["old"], 3)
        self.assertEqual([(ln["t"], ln["n"]) for ln in hunk["lines"]], [(" ", 3), ("-", 4), ("+", 4), (" ", 5)])
        old, new = hunk["lines"][1], hunk["lines"][2]
        self.assertEqual(old["p"], 2)
        self.assertEqual(old["hl"], [[0, 4]])                         # „régi” → „új”
        self.assertEqual(new["hl"], [[0, 2]])
        self.assertEqual([ln.get("w") for ln in hunk["lines"]], [None, "words", "words", None])

    def test_binary_and_truncated(self) -> None:
        gg = self.load()
        self.assertTrue(gg.diff.parse_diff("Binary files a/x and b/x differ\n")["binary"])
        many = "@@ -1,0 +1,5000 @@\n" + "".join(f"+{i}\n" for i in range(5000))
        out = gg.diff.parse_diff(many)
        self.assertTrue(out["truncated"])
        self.assertEqual(len(out["hunks"][0]["lines"]), gg.diff.DIFF_MAX_LINES)

    def test_pair_lines(self) -> None:
        """A beszúrt sor nem csúsztatja el a párokat: a hasonló sorok illeszkednek."""
        gg = self.load()
        dels = [{"s": "alma = 1"}, {"s": "körte = 2"}]
        adds = [{"s": "új sor"}, {"s": "alma = 10"}, {"s": "körte = 20"}]
        self.assertEqual(gg.diff.pair_lines(dels, adds), [(0, 1), (1, 2)])
        self.assertEqual(gg.diff.pair_lines([{"s": "a"}], [{"s": "zzz"}]), [(0, 0)])   # pozíció szerint
        self.assertEqual(gg.diff.pair_lines([], [{"s": "x"}]), [])

    def test_prose_rewrap(self) -> None:
        """Szöveges fájlban az újratördelés nem változás: csak az új mondat kiemelt, a sorok pozíció szerint párosak."""
        gg = self.load()
        raw = ("@@ -1,2 +1,2 @@\n"
               "-Tömör válaszok. A felesleges udvariaskodás és záró\n"
               "-összefoglaló nélkül.\n"
               "+Egyszerűen fogalmazz. Tömör válaszok.\n"
               "+A felesleges udvariaskodás és záró összefoglaló nélkül.\n")
        lines = self.prose_lines(raw)
        hl = [marks(ln) for ln in lines]
        self.assertEqual(hl, [[], [], ["Egyszerűen fogalmazz. "], []])
        self.assertEqual([ln.get("p") for ln in lines[:2]], [2, 3])
        # kódban marad a soronkénti összevetés
        self.assertNotEqual(gg.diff.parse_diff(raw)["hunks"][0]["lines"][0]["hl"], [])

    def test_prose_repeated_word(self) -> None:
        """Az ismétlődő szó a vele egy sorban álló párjához illeszkedik, nem az első előfordulásához."""
        raw = ("@@ -1,2 +1,2 @@\n"
               "-`commit` (`ARGS`), majd `push`.\n"
               "-Ha a `commit` megállt, a `push` elmarad.\n"
               "+1. `commit` (`ARGS`)\n"
               "+2. `push`\n")
        lines = self.prose_lines(raw)
        kept = [[ln["s"][a:b] for a, b in zip([0] + [e for _, e in ln["hl"]], [s for s, _ in ln["hl"]] + [len(ln["s"])])]
                for ln in lines]
        self.assertEqual("".join(kept[0]).strip(), "`commit` (`ARGS`)")
        self.assertEqual("".join(kept[1]).strip(), "`push`")
        self.assertEqual([ln.get("p") for ln in lines[:2]], [2, 3])

    def test_prose_paragraphs(self) -> None:
        """Az üres sor bekezdéshatár: más bekezdés szavai nem illeszkednek, a közös szó nélküli sor nem pár."""
        raw = ("@@ -1,5 +1,2 @@\n"
               "-A `commit` és a `push` lépés.\n"
               "-Második sor.\n"
               "-\n"
               "-## 1. Merge\n"
               "-`release` után.\n"
               "+1. `commit`\n"
               "+2. `push`\n")
        lines = self.prose_lines(raw)
        self.assertEqual([ln.get("p") for ln in lines[:5]], [5, None, None, None, None])
        first = lines[0]
        self.assertEqual(marks(first), ["A", "és a", " lépés."])
        for ln in lines[1:5]:
            if ln["s"]:                                  # az üres sor nem változás
                self.assertNotIn("hl", ln)               # egészében törölt: nincs szó-kiemelés
        second = lines[6]
        self.assertEqual(marks(second), ["2."])   # a `push` az első bekezdésből

    def test_prose_renumbered(self) -> None:
        """A csak üres sorral elválasztott változások egyben: az átszámozott címsor a párjára talál."""
        raw = ("@@ -1,3 +1,3 @@\n"
               "-## 4. Issue\n"
               "+Új bekezdés itt.\n"
               " \n"
               "-Az üzenet formája.\n"
               "+## 3. Issue\n")
        lines = self.prose_lines(raw)
        self.assertEqual([(ln["t"], ln["n"], ln["s"]) for ln in lines], [
            ("-", 1, "## 4. Issue"), ("-", 2, ""), ("-", 3, "Az üzenet formája."),
            ("+", 1, "Új bekezdés itt."), ("+", 2, ""), ("+", 3, "## 3. Issue")])
        self.assertEqual(lines[0]["p"], 5)
        self.assertEqual(marks(lines[5]), ["3"])
        self.assertNotIn("o", lines[1])

    def test_prose_indented_continuation(self) -> None:
        """A listaelem folytatósorának behúzása a sortöréshez tartozik: az átkerült szó nem változás."""
        raw = ("@@ -1,2 +1,2 @@\n"
               "-- **Forma**: egy rövid bekezdés (max. 3 sor); ~72 karakteres sorok.\n"
               "-  Ennél hosszabb csak indokolt esetben.\n"
               "+- **Forma**: egy rövid bekezdés (max. 200 karakter). Ennél\n"
               "+  hosszabb csak indokolt esetben.\n")
        lines = self.prose_lines(raw)
        self.assertEqual([marks(ln) for ln in lines],
                         [["3", "sor", "; ~72 karakteres sorok"], [], ["200", "karakter"], []])

    def test_prose_list_items(self) -> None:
        """A listaelem saját bekezdés: a közéjük szúrt hosszú új elem mellett is a párjukra találnak."""
        raw = ("@@ -1,4 +1,20 @@\n"
               "-- **`## STOP`** — hiba: ha egy sora teljesül, mutasd, amit a nyíl után ír, és **állj meg**.\n"
               "-- **`## SKIP`** — nincs dolga, nem hiba: ha egy sora teljesül, **állj meg**; önállóan futva\n"
               "-  mutasd, amit a nyíl után ír, láncban nincs válasza. A `## STOP` után áll, és utána is\n"
               "-  értékelődik. Menet közben kiderülő kihagyás: `→ SKIP` (a szöveg, ha van, utána).\n"
               "+- **`## STOP`** — hiba: ha egy sora teljesül, mutasd, amit a nyíl után ír, és **STOP**: a futás véget ér.\n"
               "+- **`## ASK`** — hiányzó előfeltétel, a *Fejlesztő* dönt: ha egy sora teljesül, kérdezz\n"
               "+  `AskUserQuestion`-nel (a nyíl utáni helyzet a kérdés, az alatta álló számozott sorok az\n"
               "+  opciók, az első az ajánlott), és a válasz szerint folytasd. A teljesülő sorok egy hívásban,\n"
               "+  soronként egy kérdés; ha több sor ugyanazt az előző lépést ajánlja, csak az első kérdez. A\n"
               "+  `## STOP` után áll, a `## SKIP` előtt: az előző lépés új munkát hozhat.\n"
               "+  - **Opció**: egy előző lépés commandja — lefut, utána a command folytatódik; „<valami>\n"
               "+    nélküle” — továbbmegy; `STOP` — mint a `## STOP`. Az utolsó opció mindig `STOP`.\n"
               "+  - **Előző lépés után** a konstansok elavultak: amire a további feltételek épülnek, annak a\n"
               "+    parancsát futtasd újra.\n"
               "+  - **Ajánlott út egyszer**: ha a *Fejlesztő* az ajánlott opcióval egy előző lépést hívat, a\n"
               "+    hívott lépés ASK-jai ugyanebben a futásban kérdés nélkül az ajánlottal mennek — de csak\n"
               "+    azok a sorok, amelyek ajánlott opciója is egy előző lépés; a „nélküle” vagy `STOP`\n"
               "+    ajánlású sor ilyenkor is kérdez.\n"
               "+  - **Előre jóváhagyva**: ha a hívó ezt írja (gomb, command, amelynek a hívása maga a\n"
               "+    jóváhagyás), az ASK-ok ugyanígy mennek.\n"
               "+  - Menet közben kiderülő kérdés: `→ ASK` (a helyzet és az opciók utána).\n"
               "+- **`## SKIP`** — nincs dolga, nem hiba: ha egy sora teljesül, **STOP**; önállóan futva\n"
               "+  mutasd, amit a nyíl után ír, láncban nincs válasza. A `## STOP` és a `## ASK` után áll,\n"
               "+  és utánuk is értékelődik. Menet közben kiderülő kihagyás: `→ SKIP` (a szöveg, ha van, utána).\n")
        lines = self.prose_lines(raw)
        self.assertEqual([ln.get("p") for ln in lines[:4]], [4, 21, 22, 23])
        self.assertEqual(marks(lines[0]), ["állj meg"])
        self.assertEqual(marks(lines[4]), ["STOP", ": a futás véget ér"])
        self.assertEqual(marks(lines[21]), ["STOP"])
        self.assertEqual({ln.get("w") for ln in lines[5:21]}, {"whole"})

    def test_prose_indent_not_marked(self) -> None:
        """A sor eleji behúzás (a listaelem szintje) nem szó: az al-elemmé vált sornál nincs kiemelve."""
        raw = ("@@ -1,2 +1,1 @@\n"
               "-- **Projektfüggetlen tudás** (más repóban is érvényes) nem memória, hanem rule vagy skill\n"
               "-  (→ `/learn:capture`).\n"
               "+  - **Rule vagy skill** — ami más repóban is érvényes, `/learn:capture`-rel.\n")
        lines = self.prose_lines(raw)
        self.assertEqual(marks(lines[2]), ["Rule", "vagy skill", "— ami ", "-rel"])

    def test_line_state(self) -> None:
        """A változott sor állapota (`w`): változatlan szavak, változott szavak, egészében új / üres."""
        raw = ("@@ -1,2 +1,3 @@\n"
               "-Egy mondat itt,\n"
               "-ami folytatódik.\n"
               "+Egy mondat itt, ami folytatódik.\n"
               "+\n"
               "+Teljesen más tartalom.\n")
        lines = self.prose_lines(raw)
        self.assertEqual([ln["w"] for ln in lines], ["same", "same", "same", "same", "whole"])

    def test_line_looks(self) -> None:
        """A sorok megjelenése (`v`): csak beszúrás, tiszta újratördelés, és páronként egy vegyes változásban."""
        gg = self.load()
        looks = lambda raw, prose=False: [(ln["t"], ln.get("v")) for ln in gg.diff.parse_diff(raw, prose)["hunks"][0]["lines"]]  # noqa: E731
        # csak beszúrás: a régi sor kimarad, az új semleges; az egészében új sor teljes színű
        self.assertEqual(looks("@@ -1,1 +1,2 @@\n-x = f(a)\n+x = f(a, b)\n+y = 2\n"),
                         [("-", "drop"), ("+", "only"), ("+", None)])
        # tiszta újratördelés: a régi kimarad, az új változatlan
        self.assertEqual(looks("@@ -1,2 +1,1 @@\n-Egy mondat\n-itt.\n+Egy mondat itt.\n", prose=True),
                         [("-", "drop"), ("-", "drop"), ("+", "same")])
        # vegyes változás: az első pár csak törlés, a második csere
        self.assertEqual(looks("@@ -1,2 +1,2 @@\n-| s2 | sor szövege |\n-| s3 | régi |\n+| s2 | sor |\n+| s3 | új |\n"),
                         [("-", "only"), ("-", None), ("+", "drop"), ("+", None)])

    def test_pair_both_ways(self) -> None:
        """A pár mindkét irányban (`p`): a törölt sor az újra, az új a törölt sorra mutat."""
        gg = self.load()
        lines = gg.diff.parse_diff("@@ -1,2 +1,2 @@\n-a = 1\n-b = 2\n+a = 10\n+b = 20\n")["hunks"][0]["lines"]
        self.assertEqual([ln["p"] for ln in lines], [2, 3, 0, 1])

    def test_md_order(self) -> None:
        """A markdown-nézet adata (`md`) a blokkok sorrendjében: a törölt bekezdés után a párja, a pár nélküli
        új bekezdés a helyén — a `p` az új sorrendhez igazodik; a nyers nézeté változatlan."""
        gg = self.load()
        raw = ("@@ -1,7 +1,7 @@\n"
               "-## 1. Alfa szakasz\n-\n-Régi egy szöveg.\n-\n-## 2. Béta szakasz\n-\n-Régi kettő szöveg.\n"
               "+## 1. Alfa szakasz!\n+\n+Új első tartalom.\n+\n+## 2. Béta szakasz!\n+\n+Új második tartalom.\n")
        md = gg.diff.parse_diff(raw, prose=True, md=True)["hunks"][0]["lines"]
        self.assertEqual([(ln["t"], ln["s"]) for ln in md if ln["s"]], [
            ("-", "## 1. Alfa szakasz"), ("+", "## 1. Alfa szakasz!"),
            ("-", "Régi egy szöveg."), ("+", "Új első tartalom."),
            ("-", "## 2. Béta szakasz"), ("+", "## 2. Béta szakasz!"),
            ("-", "Régi kettő szöveg."), ("+", "Új második tartalom."),
        ])
        for i, ln in enumerate(md):
            if "p" in ln:
                self.assertEqual(md[ln["p"]]["p"], i)
        raw_view = gg.diff.parse_diff(raw, prose=True)["hunks"][0]["lines"]
        self.assertEqual([ln["t"] for ln in raw_view], ["-"] * 7 + ["+"] * 7)

    def test_md_starts(self) -> None:
        """A törölt oldal blokkjai, mint a lapon: listaelem, címsor, táblázat külön; a kódblokk egyben."""
        gg = self.load()
        src = ["Bekezdés", "folytatás.", "- elem", "  folytatás", "- elem", "## Cím", "| a |", "| b |", "Szöveg",
               "", "```", "- nem elem", "", "kód", "```", "> idézet", "lusta folytatás"]
        lines = [{"t": "-", "s": s} for s in src] + [{"t": "+", "s": "- új"}]
        self.assertEqual(sorted(gg.diff.md_starts(lines)), [0, 2, 4, 5, 6, 8, 10, 15])

    def test_numstat_paths(self) -> None:
        """Átnevezés-alakok: `a => b` és `x/{a => b}/y`, az üres oldallal is."""
        gg = self.load()
        old, new = gg.gitio.numstat_old_path, gg.gitio.numstat_new_path
        self.assertEqual((old("a => b"), new("a => b")), ("a", "b"))
        self.assertEqual((old("src/{a => b}/m.py"), new("src/{a => b}/m.py")), ("src/a/m.py", "src/b/m.py"))
        self.assertEqual((old("src/{ => sub}/m.py"), new("src/{ => sub}/m.py")), ("src/m.py", "src/sub/m.py"))
        self.assertEqual(new("sima.txt"), "sima.txt")

    def test_file_diff_inputs(self) -> None:
        """Commitban, átnevezve, követetlen fájlra; érvénytelen sha és ismeretlen worktree: hiba."""
        repo = self.plain_repo()
        git_in(repo, "mv", "a.txt", "b.txt")
        git_in(repo, "commit", "-qm", "mv")
        gg = self.load()
        gg.gitio.set_repo(repo)
        sha = git_in(repo, "rev-parse", "HEAD").strip()
        self.assertEqual(gg.diff.file_diff(sha, "a.txt => b.txt")["hunks"], [])   # tiszta átnevezés
        first = git_in(repo, "rev-parse", "HEAD~1").strip()
        self.assertEqual(gg.diff.file_diff(first, "a.txt")["hunks"][0]["lines"], [{"t": "+", "n": 1, "s": "1", "w": "whole"}])
        (repo / "uj.txt").write_text("x\ny\n", encoding="utf-8")
        (repo / "mappa").mkdir()
        (repo / "mappa" / "f.txt").write_text("z\n", encoding="utf-8")
        wip = f"*uncommitted:{gg.registry.slug_for(repo)}"
        self.assertEqual(len(gg.diff.file_diff(wip, "uj.txt")["hunks"][0]["lines"]), 2)
        self.assertEqual(gg.diff.file_diff(wip, "mappa/f.txt")["hunks"][0]["lines"], [{"t": "+", "n": 1, "s": "z", "w": "whole"}])
        self.assertEqual(gg.diff.file_diff(wip, "nincs.txt")["hunks"], [])         # nem olvas tetszőleges fájlt
        for bad in ("--output=/tmp/x", "HEAD", "*uncommitted:nincs-ilyen-000000"):
            with self.assertRaises(ValueError, msg=bad):
                gg.diff.file_diff(bad, "a.txt")

    def test_file_diff_full(self) -> None:
        """`full`: a teljes fájl egy hunkban, a változatlan sorokkal — commitban és WIP-ben."""
        repo = self.plain_repo()
        lines = [f"sor {i}" for i in range(30)]
        (repo / "doc.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        git_in(repo, "add", "doc.md")
        git_in(repo, "commit", "-qm", "doc")
        lines[15] = "módosított sor"
        (repo / "doc.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        gg = self.load()
        gg.gitio.set_repo(repo)
        wip = f"*uncommitted:{gg.registry.slug_for(repo)}"
        (hunk,) = gg.diff.file_diff(wip, "doc.md", full=True)["hunks"]
        self.assertEqual(len(hunk["lines"]), 31)                 # 29 változatlan + törölt + hozzáadott
        self.assertEqual(hunk["old"], 1)
        self.assertEqual(len(gg.diff.file_diff(wip, "doc.md")["hunks"][0]["lines"]), 8)   # 3+3 környezet
        git_in(repo, "commit", "-qam", "mod")
        sha = git_in(repo, "rev-parse", "HEAD").strip()
        (hunk,) = gg.diff.file_diff(sha, "doc.md", full=True)["hunks"]
        self.assertEqual(len(hunk["lines"]), 31)

    def test_file_diff_unstaged_rename(self) -> None:
        """A WIP-sor párosított átnevezése: a HEAD-beli régi és a követetlen új fájl különbsége."""
        repo = self.plain_repo()
        (repo / "regi.txt").write_text("".join(f"sor {i}\n" for i in range(10)), encoding="utf-8")
        git_in(repo, "add", "regi.txt")
        git_in(repo, "commit", "-qm", "alap")
        (repo / "regi.txt").unlink()
        (repo / "uj.txt").write_text("".join(f"sor {i}\n" for i in range(10)).replace("sor 5", "öt"), encoding="utf-8")
        gg = self.load()
        gg.gitio.set_repo(repo)
        wip = f"*uncommitted:{gg.registry.slug_for(repo)}"
        (hunk,) = gg.diff.file_diff(wip, "regi.txt => uj.txt")["hunks"]
        self.assertEqual([(ln["t"], ln["s"]) for ln in hunk["lines"] if ln["t"] != " "], [("-", "sor 5"), ("+", "öt")])
        self.assertEqual(len(gg.diff.file_diff(wip, "regi.txt => uj.txt", full=True)["hunks"][0]["lines"]), 11)

    def test_untracked_binary(self) -> None:
        gg = self.load()
        (self.home / "kep.bin").write_bytes(b"\xff\xfe\x00")
        self.assertTrue(gg.diff.untracked_diff(self.home, "kep.bin")["binary"])

    def test_untracked_symlink(self) -> None:
        """Követetlen symlink (mappára is): mint a gitben, egyetlen sor, a link célja — nem a cél tartalma."""
        gg = self.load()
        repo = self.plain_repo()
        (repo / "skills" / "neon").mkdir(parents=True)
        (repo / "link").symlink_to("skills/neon")
        gg.gitio.set_repo(repo)
        sha = gg.graph.collect_payload(None)["commits"][0]["sha"]
        diff = gg.diff.file_diff(sha, "link")
        self.assertEqual([ln["s"] for h in diff["hunks"] for ln in h["lines"]], ["skills/neon"])
        self.assertEqual(gg.worktrees.untracked_lines(repo / "link"), 1)

    def image_repo(self) -> tuple:
        """Repó egy képpel két commitban (régi, új), és a betöltött csomag: (repó, gg, szülő, commit)."""
        repo = self.plain_repo()
        (repo / "docs" / "img").mkdir(parents=True)
        (repo / "docs" / "img" / "graph.png").write_bytes(b"\x89PNG\0-regi")
        (repo / "logo.svg").write_text("<svg/>\n", encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "kép")
        (repo / "docs" / "img" / "graph.png").write_bytes(b"\x89PNG\0-uj")
        git_in(repo, "commit", "-qam", "kép: módosítva")
        gg = self.load()
        gg.gitio.set_repo(repo)
        return repo, gg, *(git_in(repo, "rev-parse", r).strip() for r in ("HEAD~1", "HEAD"))

    def sides(self, gg, sha: str, path: str, image: str | None = None) -> dict:
        """A kép két oldala, oldalanként külön `file_diff` hívással (`side`)."""
        return {s: gg.diff.file_diff(sha, path, image=image, side=s) for s in ("old", "new")}

    def test_image_file_sides(self) -> None:
        """R-1 — A képfájl két oldala data URI-ként, oldalanként külön: commitnál szülő ↔ commit,
        a Stage-elt sornál HEAD ↔ index, az Uncommitted sornál index ↔ lemez, követetlennél csak
        a lemez. A diff maga a két oldal méretét adja, kép nélkül."""
        repo, gg, parent, sha = self.image_repo()
        png = "data:image/png;base64,"
        b64 = lambda b: png + __import__("base64").b64encode(b).decode()   # noqa: E731
        self.assertEqual(gg.diff.file_diff(sha, "docs/img/graph.png")["image"], {"old": {"size": 10}, "new": {"size": 8}})
        img = self.sides(gg, sha, "docs/img/graph.png")
        self.assertEqual((img["old"]["uri"], img["new"]["uri"]), (b64(b"\x89PNG\0-regi"), b64(b"\x89PNG\0-uj")))
        self.assertEqual(img["new"]["size"], 8)
        img = self.sides(gg, parent, "docs/img/graph.png")
        self.assertIsNone(img["old"])                                          # új fájl
        self.assertTrue(gg.diff.file_diff(parent, "logo.svg")["hunks"])        # az SVG szöveges diffje is
        (repo / "docs" / "img" / "graph.png").write_bytes(b"\x89PNG\0-index")
        git_in(repo, "add", ".")
        (repo / "docs" / "img" / "graph.png").write_bytes(b"\x89PNG\0-lemez")
        (repo / "uj.png").write_bytes(b"\x89PNG\0-kovetetlen")
        slug = gg.registry.slug_for(repo)
        staged = self.sides(gg, f"*staged:{slug}", "docs/img/graph.png")
        self.assertEqual((staged["old"]["uri"], staged["new"]["uri"]), (b64(b"\x89PNG\0-uj"), b64(b"\x89PNG\0-index")))
        wip = self.sides(gg, f"*uncommitted:{slug}", "docs/img/graph.png")
        self.assertEqual((wip["old"]["uri"], wip["new"]["uri"]), (b64(b"\x89PNG\0-index"), b64(b"\x89PNG\0-lemez")))
        wip = self.sides(gg, f"*uncommitted:{slug}", "uj.png")
        self.assertEqual((wip["old"], wip["new"]["uri"]), (None, b64(b"\x89PNG\0-kovetetlen")))
        self.assertNotIn("image", gg.diff.file_diff(sha, "a.txt"))

    def test_image_too_big(self) -> None:
        """R-2 — Az `IMAGE_MAX` fölötti kép csak a méretét adja, tartalom nélkül."""
        repo, gg, _, _ = self.image_repo()
        big = b"\0" * (gg.diff.IMAGE_MAX + 1)
        (repo / "nagy.jpg").write_bytes(big)
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "nagy")
        sha = git_in(repo, "rev-parse", "HEAD").strip()
        self.assertEqual(gg.diff.file_diff(sha, "nagy.jpg", side="new"), {"size": len(big)})
        (repo / "nagy2.jpg").write_bytes(big)
        wip = f"*uncommitted:{gg.registry.slug_for(repo)}"
        self.assertEqual(gg.diff.file_diff(wip, "nagy2.jpg", side="new"), {"size": len(big)})

    def test_image_side_response(self) -> None:
        """A limit (2 950 000 bájt) alatti kép egy oldala külön válaszban, a host-híd ~4 000 000
        karakteres határa alatt; a pár így két válasz."""
        repo, gg, _, _ = self.image_repo()
        self.assertEqual(gg.diff.IMAGE_MAX, 2_950_000)
        for name, fill in (("a.png", b"\1"), ("b.png", b"\2")):
            (repo / name).write_bytes(fill * gg.diff.IMAGE_MAX)
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "nagy pár")
        sha = git_in(repo, "rev-parse", "HEAD").strip()
        side = gg.diff.file_diff(sha, "a.png", side="new")
        self.assertIn("uri", side)
        self.assertLess(len(json.dumps(side)), 3_999_000)
        self.assertNotIn("uri", gg.diff.file_diff(sha, "a.png")["image"]["new"])

    def test_image_ref(self) -> None:
        """R-4 — A markdown-kép útja: a md-fájl mappájához képest, a `/…` a repó gyökeréből; a
        külső és a repón kívülre mutató út hiba."""
        gg = self.load()
        ref = gg.diff.image_ref
        self.assertEqual(ref("docs/README.md", "img/graph.png"), "docs/img/graph.png")
        self.assertEqual(ref("docs/README.md", "../logo.svg"), "logo.svg")
        self.assertEqual(ref("docs/README.md", "/docs/img/graph.png"), "docs/img/graph.png")
        self.assertEqual(ref("README.md", "<img/a b.png>"), "img/a b.png")
        self.assertEqual(ref("README.md", "img/a%20b.png?raw=1#x"), "img/a b.png")
        for bad in ("https://img.shields.io/badge/x-y-green", "//host/x.png", "data:image/png;base64,AA",
                    "../kint.png", "/../kint.png", ""):
            with self.assertRaises(ValueError, msg=bad):
                ref("README.md", bad)

    def test_markdown_image(self) -> None:
        """R-4 — A markdown-kép oldalanként a saját változatából; hiányzó oldal: `None`; a nem
        képfájl, a hibás sha és a repón kívüli út hiba; a lemezről csak a git által ismert fájl."""
        repo, gg, parent, sha = self.image_repo()
        img = self.sides(gg, sha, "docs/README.md", "img/graph.png")
        self.assertTrue(img["old"]["uri"].endswith(__import__("base64").b64encode(b"\x89PNG\0-regi").decode()))
        self.assertNotEqual(img["old"]["uri"], img["new"]["uri"])
        self.assertIsNone(gg.diff.file_diff(parent, "docs/README.md", image="img/graph.png", side="old"))
        self.assertIsNone(gg.diff.file_diff(sha, "docs/README.md", image="img/nincs.png", side="new"))
        self.assertEqual(gg.diff.file_diff(sha, "docs/README.md", image="../logo.svg", side="new")["uri"][:26],
                         "data:image/svg+xml;base64,")
        (repo / ".gitignore").write_text("titok.png\n", encoding="utf-8")
        (repo / "titok.png").write_bytes(b"\x89PNG\0")
        wip = f"*uncommitted:{gg.registry.slug_for(repo)}"
        self.assertIsNone(gg.diff.file_diff(wip, "README.md", image="titok.png", side="new"))    # ignorált
        self.assertTrue(gg.diff.file_diff(wip, "README.md", image="docs/img/graph.png", side="new")["uri"])
        for bad_sha, bad_ref in (("--output=/tmp/x", "a.png"), ("HEAD", "a.png"), (sha, "a.txt"),
                                 (sha, "../../kint.png"), (sha, "https://x.hu/a.png")):
            with self.assertRaises(ValueError, msg=bad_ref):
                gg.diff.file_diff(bad_sha, "docs/README.md", image=bad_ref, side="new")
        with self.assertRaises(ValueError):
            gg.diff.file_diff(sha, "docs/img/graph.png", side="mind")
