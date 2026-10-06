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
        self.assertIn("note", gg.diff.file_diff(wip, "mappa/"))
        self.assertEqual(gg.diff.file_diff(wip, "nincs.txt")["hunks"], [])         # nem olvas tetszőleges fájlt
        for bad in ("--output=/tmp/x", "HEAD", "*uncommitted:nincs-ilyen-000000"):
            with self.assertRaises(ValueError, msg=bad):
                gg.diff.file_diff(bad, "a.txt")

    def test_untracked_binary(self) -> None:
        gg = self.load()
        (self.home / "kep.bin").write_bytes(b"\xff\xfe\x00")
        self.assertTrue(gg.diff.untracked_diff(self.home, "kep.bin")["binary"])
