"""Fájl-diff (`diff`): hunkok, sorpárok, szószintű kiemelés, a lapról jövő bemenet szűrése."""
from __future__ import annotations

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


class DiffTest(HomeTestCase):
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
        lines = gg.diff.parse_diff(raw, prose=True)["hunks"][0]["lines"]
        hl = [[ln["s"][a:b] for a, b in ln["hl"]] for ln in lines]
        self.assertEqual(hl, [[], [], ["Egyszerűen fogalmazz. "], []])
        self.assertEqual([ln.get("p") for ln in lines[:2]], [2, 3])
        # kódban marad a soronkénti összevetés
        self.assertNotEqual(gg.diff.parse_diff(raw)["hunks"][0]["lines"][0]["hl"], [])

    def test_prose_repeated_word(self) -> None:
        """Az ismétlődő szó a vele egy sorban álló párjához illeszkedik, nem az első előfordulásához."""
        gg = self.load()
        raw = ("@@ -1,2 +1,2 @@\n"
               "-`commit` (`ARGS`), majd `push`.\n"
               "-Ha a `commit` megállt, a `push` elmarad.\n"
               "+1. `commit` (`ARGS`)\n"
               "+2. `push`\n")
        lines = gg.diff.parse_diff(raw, prose=True)["hunks"][0]["lines"]
        kept = [[ln["s"][a:b] for a, b in zip([0] + [e for _, e in ln["hl"]], [s for s, _ in ln["hl"]] + [len(ln["s"])])]
                for ln in lines]
        self.assertEqual("".join(kept[0]).strip(), "`commit` (`ARGS`)")
        self.assertEqual("".join(kept[1]).strip(), "`push`")
        self.assertEqual([ln.get("p") for ln in lines[:2]], [2, 3])

    def test_prose_paragraphs(self) -> None:
        """Az üres sor bekezdéshatár: más bekezdés szavai nem illeszkednek, a közös szó nélküli sor nem pár."""
        gg = self.load()
        raw = ("@@ -1,5 +1,2 @@\n"
               "-A `commit` és a `push` lépés.\n"
               "-Második sor.\n"
               "-\n"
               "-## 1. Merge\n"
               "-`release` után.\n"
               "+1. `commit`\n"
               "+2. `push`\n")
        lines = gg.diff.parse_diff(raw, prose=True)["hunks"][0]["lines"]
        self.assertEqual([ln.get("p") for ln in lines[:5]], [5, None, None, None, None])
        first = lines[0]
        self.assertEqual([first["s"][a:b] for a, b in first["hl"]], ["A", "és a", " lépés."])
        for ln in lines[1:5]:
            if ln["s"]:                                  # az üres sor nem változás
                self.assertNotIn("hl", ln)               # egészében törölt: nincs szó-kiemelés
        second = lines[6]
        self.assertEqual([second["s"][a:b] for a, b in second["hl"]], ["2."])   # a `push` az első bekezdésből

    def test_prose_renumbered(self) -> None:
        """A csak üres sorral elválasztott változások egyben: az átszámozott címsor a párjára talál."""
        gg = self.load()
        raw = ("@@ -1,3 +1,3 @@\n"
               "-## 4. Issue\n"
               "+Új bekezdés itt.\n"
               " \n"
               "-Az üzenet formája.\n"
               "+## 3. Issue\n")
        lines = gg.diff.parse_diff(raw, prose=True)["hunks"][0]["lines"]
        self.assertEqual([(ln["t"], ln["n"], ln["s"]) for ln in lines], [
            ("-", 1, "## 4. Issue"), ("-", 2, ""), ("-", 3, "Az üzenet formája."),
            ("+", 1, "Új bekezdés itt."), ("+", 2, ""), ("+", 3, "## 3. Issue")])
        self.assertEqual(lines[0]["p"], 5)
        self.assertEqual([lines[5]["s"][a:b] for a, b in lines[5]["hl"]], ["3"])
        self.assertNotIn("o", lines[1])

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
        self.assertEqual(gg.diff.file_diff(first, "a.txt")["hunks"][0]["lines"], [{"t": "+", "n": 1, "s": "1"}])
        (repo / "uj.txt").write_text("x\ny\n", encoding="utf-8")
        (repo / "mappa").mkdir()
        (repo / "mappa" / "f.txt").write_text("z\n", encoding="utf-8")
        wip = f"*uncommitted:{gg.registry.slug_for(repo)}"
        self.assertEqual(len(gg.diff.file_diff(wip, "uj.txt")["hunks"][0]["lines"]), 2)
        self.assertEqual(gg.diff.file_diff(wip, "mappa/f.txt")["hunks"][0]["lines"], [{"t": "+", "n": 1, "s": "z"}])
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

    def test_untracked_binary(self) -> None:
        gg = self.load()
        (self.home / "kep.bin").write_bytes(b"\xff\xfe\x00")
        self.assertTrue(gg.diff.untracked_diff(self.home, "kep.bin")["binary"])
