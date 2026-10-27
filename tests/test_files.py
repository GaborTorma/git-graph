"""A teljes nézet fájlfája és a WIP sor mentése (`files`): fájllista, tartalomkeresés, `write_file`."""
from __future__ import annotations

import hashlib
import os
import subprocess
import time
from pathlib import Path

from helpers import HomeTestCase, git_in


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bulk_commit(repo, count: int, per_dir: int = 1000) -> str:
    """Egy commit `count` fájllal (`d000/f0000.py` …), egyetlen blobbal, az indexen át —
    fájlok kiírása nélkül; vissza a commit sha-ja."""
    blob = subprocess.run(["git", "-C", str(repo), "hash-object", "-w", "--stdin"], input=b"x = 1\n",
                          capture_output=True, check=True).stdout.decode().strip()
    lines = "".join(f"100644 {blob}\td{i // per_dir:03d}/f{i % per_dir:04d}.py\n" for i in range(count))
    subprocess.run(["git", "-C", str(repo), "update-index", "--index-info"], input=lines.encode(),
                   check=True)
    git_in(repo, "commit", "-qm", "sok fájl")
    return git_in(repo, "rev-parse", "HEAD").strip()


class FilesCase(HomeTestCase):
    def repo(self):
        """Egycommitos repó betöltött csomaggal: (repó, gg, a WIP sor sha-ja)."""
        repo = self.plain_repo()
        gg = self.load()
        gg.gitio.set_repo(repo)
        return repo, gg, f"*uncommitted:{gg.registry.slug_for(repo)}"


class FileTreeTest(FilesCase):
    def test_commit_files(self) -> None:
        """A commit állapotának minden fájlja, ikonnal, a használt ikonok SVG-jével."""
        # Adott egy commit két fájllal
        repo, gg, _ = self.repo()
        (repo / "src").mkdir()
        (repo / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "app")
        sha = git_in(repo, "rev-parse", "HEAD").strip()
        # Ha a lap a fájllistát kéri
        tree = gg.files.file_tree(sha)
        # Akkor mindkét fájl benne van, lusta mód nélkül
        self.assertNotIn("lazy", tree)
        self.assertEqual([f["path"] for f in tree["files"]], ["a.txt", "src/app.py"])
        icons = {f["icon"] for f in tree["files"]}
        self.assertEqual(icons, set(tree["fileIcons"]))
        self.assertTrue(all(svg.startswith("<svg") for svg in tree["fileIcons"].values()))

    def test_worktree_files(self) -> None:
        """WIP soron a worktree fájljai: a követett és a nem ignorált követetlen; stage-elt soron az indexé."""
        # Adott egy követetlen és egy ignorált fájl
        repo, gg, wip = self.repo()
        (repo / ".gitignore").write_text("titok.txt\n", encoding="utf-8")
        (repo / "uj.txt").write_text("új\n", encoding="utf-8")
        (repo / "titok.txt").write_text("x\n", encoding="utf-8")
        # Ha a lap az Uncommitted és a Stage-elt sor fájljait kéri
        wip_paths = [f["path"] for f in gg.files.file_tree(wip)["files"]]
        staged = [f["path"] for f in gg.files.file_tree(wip.replace("uncommitted", "staged"))["files"]]
        # Akkor az ignorált kimarad, a követetlen csak a munkakönyvtárban van
        self.assertEqual(wip_paths, [".gitignore", "a.txt", "uj.txt"])
        self.assertEqual(staged, ["a.txt"])

    def test_invalid_sha(self) -> None:
        """A lapról jövő sha csak hex vagy élő worktree ál-sora lehet; a repón kívüli mappa hiba."""
        # Adott egy repó
        _, gg, _ = self.repo()
        # Ha a sha opció, nem létező worktree, vagy a mappa kifelé mutat
        # Akkor hiba
        for sha in ("--output=/tmp/x", "HEAD", "*uncommitted:nincs-ilyen"):
            with self.assertRaises(ValueError, msg=sha):
                gg.files.file_tree(sha)
        with self.assertRaises(ValueError):
            gg.files.file_tree("*uncommitted", "../kint")


class BigRepoTest(FilesCase):
    def test_lazy_levels(self) -> None:
        """Egy 25 000 fájlos commitnál a szerver a gyökér szintjét adja, a mappák tartalmát mappánként."""
        # Adott egy commit 25 000 fájllal
        repo, gg, _ = self.repo()
        sha = bulk_commit(repo, 25000)
        # Ha a lap az összes fájl listáját kéri
        root = gg.files.file_tree(sha)
        # Akkor a gyökér szintjét kapja
        self.assertTrue(root["lazy"])
        self.assertEqual(root["dir"], "")
        self.assertEqual(root["dirs"], [f"d{i:03d}" for i in range(25)])
        self.assertEqual([f["path"] for f in root["files"]], ["a.txt"])
        # Ha egy mappát kinyit
        sub = gg.files.file_tree(sha, "d007")
        # Akkor annak a tartalmát, a fájlok teljes útjával
        self.assertEqual((sub["dir"], sub["dirs"], len(sub["files"])), ("d007", [], 1000))
        self.assertEqual(sub["files"][0]["path"], "d007/f0000.py")
        self.assertEqual(set(sub["fileIcons"]), {sub["files"][0]["icon"]})

    def test_worktree_lazy(self) -> None:
        """A WIP soron is mappánként jön a nagy fa (a munkakönyvtár listájából)."""
        # Adott egy 25 000 fájlos worktree
        repo, gg, wip = self.repo()
        bulk_commit(repo, 25000)
        git_in(repo, "checkout", "-q", "--", ".")
        (repo / "d003" / "uj.txt").write_text("új\n", encoding="utf-8")
        # Ha a lap a fát, majd egy mappát kér
        root, sub = gg.files.file_tree(wip), gg.files.file_tree(wip, "d003/")
        # Akkor a gyökér szintje lusta, a mappában a követetlen fájl is ott van
        self.assertTrue(root["lazy"])
        self.assertEqual(len(root["dirs"]), 25)
        self.assertEqual(len(sub["files"]), 1001)
        self.assertIn("d003/uj.txt", [f["path"] for f in sub["files"]])

    def test_speed(self) -> None:
        """20 000 fájl egy válaszban, 300 ms alatt."""
        # Adott egy commit 20 000 fájllal
        repo, gg, _ = self.repo()
        git_in(repo, "rm", "-q", "a.txt")
        sha = bulk_commit(repo, 20000)
        gg.files.file_tree(sha)                         # az ikonkészlet betöltése
        # Ha a lap a teljes listát kéri
        start = time.perf_counter()
        tree = gg.files.file_tree(sha)
        took = time.perf_counter() - start
        # Akkor egy válaszban jön, 300 ms alatt
        self.assertNotIn("lazy", tree)
        self.assertEqual(len(tree["files"]), 20000)
        self.assertLess(took, 0.3)


class ContentSearchTest(FilesCase):
    def search_repo(self):
        repo, gg, wip = self.repo()
        (repo / "git_graph").mkdir()
        (repo / "git_graph" / "diff.py").write_text("DIFF_MAX_LINES = 3000\n", encoding="utf-8")
        (repo / "git_graph" / "graph.py").write_text("x = 1\n", encoding="utf-8")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "kód")
        return repo, gg, wip, git_in(repo, "rev-parse", "HEAD").strip()

    def test_commit(self) -> None:
        """A commiton csak azok a fájlok jönnek, amelyekben a szöveg szerepel (kis-nagybetűtől függetlenül)."""
        # Adott a "git_graph/diff.py" egy sora "DIFF_MAX_LINES"
        _, gg, _, sha = self.search_repo()
        # Ha a lap rákeres
        found = gg.files.file_tree(sha, grep="diff_max_lines")
        # Akkor csak az a fájl jön
        self.assertEqual([f["path"] for f in found["files"]], ["git_graph/diff.py"])
        self.assertFalse(found["more"])
        self.assertIn(found["files"][0]["icon"], found["fileIcons"])

    def test_worktree(self) -> None:
        """WIP soron a munkakönyvtárban keres, a követetlen fájlban is; stage-elt soron az indexben."""
        # Adott egy követetlen fájl a szöveggel, és a diff.py-ból a sor a lemezen kitörölve
        repo, gg, wip, _ = self.search_repo()
        (repo / "uj.py").write_text("# DIFF_MAX_LINES\n", encoding="utf-8")
        (repo / "git_graph" / "diff.py").write_text("x = 2\n", encoding="utf-8")
        # Ha a lap a WIP sorokon keres
        wip_found = gg.files.file_tree(wip, grep="DIFF_MAX_LINES")
        staged = gg.files.file_tree(wip.replace("uncommitted", "staged"), grep="DIFF_MAX_LINES")
        # Akkor a munkakönyvtár, illetve az index állapota szerint talál
        self.assertEqual([f["path"] for f in wip_found["files"]], ["uj.py"])
        self.assertEqual([f["path"] for f in staged["files"]], ["git_graph/diff.py"])

    def test_no_match(self) -> None:
        """Találat nélkül üres lista, nem hiba; az opciónak látszó szöveg is csak szöveg."""
        # Adott egy commit
        _, gg, _, sha = self.search_repo()
        # Ha a lap olyat keres, ami nincs, vagy ami opciónak látszik
        # Akkor üres a lista
        for needle in ("nincs ilyen szöveg", "--output=/tmp/x"):
            self.assertEqual(gg.files.file_tree(sha, grep=needle)["files"], [], needle)

    def test_limit(self) -> None:
        """Legfeljebb 2000 találat, a többit a `more` jelzi."""
        # Adott 2001 fájl a szöveggel
        repo, gg, _ = self.repo()
        sha = bulk_commit(repo, 2001)
        # Ha a lap rákeres
        found = gg.files.file_tree(sha, grep="x = 1")
        # Akkor 2000 jön, és `more`
        self.assertEqual((len(found["files"]), found["more"]), (2000, True))


class WriteFileTest(FilesCase):
    def test_write(self) -> None:
        """A WIP sor fájlja a lemezre íródik, a jogosultsága marad; az új hash jön vissza."""
        # Adott egy futtatható fájl
        repo, gg, wip = self.repo()
        script = repo / "run.sh"
        script.write_text("echo 1\n", encoding="utf-8")
        os.chmod(script, 0o755)
        base = gg.diff.file_diff(wip, "run.sh", side="new")["hash"]
        # Ha a lap ment
        out = gg.files.write_file(wip, "run.sh", "echo 2\n", base)
        # Akkor a fájl az új tartalmú, futtatható marad
        self.assertEqual(out, {"ok": True, "hash": sha256(b"echo 2\n")})
        self.assertEqual(script.read_bytes(), b"echo 2\n")
        self.assertEqual(script.stat().st_mode & 0o777, 0o755)

    def test_only_uncommitted(self) -> None:
        """Csak az Uncommitted sor fájlja írható: commit és Stage-elt sor nem."""
        # Adott egy repó
        repo, gg, wip = self.repo()
        sha = git_in(repo, "rev-parse", "HEAD").strip()
        base = sha256((repo / "a.txt").read_bytes())
        # Ha a lap commitra vagy a Stage-elt sorra ment
        # Akkor hiba, a fájl nem változik
        for target in (sha, wip.replace("uncommitted", "staged")):
            with self.assertRaises(ValueError, msg=target):
                gg.files.write_file(target, "a.txt", "x\n", base)
        self.assertEqual((repo / "a.txt").read_text(encoding="utf-8"), "1\n")


class WriteConflictTest(FilesCase):
    def test_conflict(self) -> None:
        """Régebbi hash-re mentve nem ír, és a lemezen lévőt adja."""
        # Adott a lap a fájl egy régebbi hash-ét ismeri, közben a lemezen változott
        repo, gg, wip = self.repo()
        old = sha256((repo / "a.txt").read_bytes())
        (repo / "a.txt").write_text("lemez\n", encoding="utf-8")
        # Ha az író tool összeveti a lemezen lévővel
        out = gg.files.write_file(wip, "a.txt", "enyém\n", old)
        # Akkor nem ír, és az eltérést jelzi
        self.assertEqual(out, {"ok": False, "conflict": True, "hash": sha256(b"lemez\n"), "text": "lemez\n"})
        self.assertEqual((repo / "a.txt").read_text(encoding="utf-8"), "lemez\n")


class ForbiddenPathTest(FilesCase):
    def assert_refused(self, path: str, target) -> None:
        repo, gg, wip = self.repo()
        before = target(repo).read_bytes()
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            gg.files.write_file(wip, path, "feltört\n", sha256(before))
        self.assertEqual(target(repo).read_bytes(), before)

    def test_git_dir(self) -> None:
        """A `.git/config` nem írható."""
        # Adott a repó git-configja
        # Ha a lap a `.git/config`-ot írná
        # Akkor hiba, a config nem változik
        self.assert_refused(".git/config", lambda repo: repo / ".git" / "config")

    def test_parent(self) -> None:
        """A `../masik-repo/app.py` nem írható."""
        # Adott egy másik repó a szomszéd mappában
        other = self.home / "masik-repo"
        other.mkdir()
        (other / "app.py").write_text("print(1)\n", encoding="utf-8")
        # Ha a lap `..`-tal írna bele
        # Akkor hiba, a fájl nem változik
        self.assert_refused("../masik-repo/app.py", lambda repo: other / "app.py")

    def test_symlink_outside(self) -> None:
        """A repón kívüli mappára mutató symlinken át nem írható."""
        # Adott egy symlink a repón kívüli mappára
        outside = self.home / "kint"
        outside.mkdir()
        (outside / "x.txt").write_text("kint\n", encoding="utf-8")
        repo, gg, wip = self.repo()
        (repo / "link-a-repon-kivulre").symlink_to(outside)
        # Ha a lap a symlinken át írna
        with self.assertRaises(ValueError):
            gg.files.write_file(wip, "link-a-repon-kivulre/x.txt", "feltört\n", sha256(b"kint\n"))
        # Akkor hiba, a kinti fájl nem változik
        self.assertEqual((outside / "x.txt").read_text(encoding="utf-8"), "kint\n")

    def test_symlink_file_outside(self) -> None:
        """A repón kívüli fájlra mutató, követetlen symlinken át sem írható."""
        # Adott egy követetlen symlink egy kinti fájlra
        outside = self.home / "kint.txt"
        outside.write_text("kint\n", encoding="utf-8")
        repo, gg, wip = self.repo()
        (repo / "link.txt").symlink_to(outside)
        # Ha a lap a symlinkre írna
        with self.assertRaises(ValueError):
            gg.files.write_file(wip, "link.txt", "feltört\n", sha256(b"kint\n"))
        # Akkor a kinti fájl nem változik
        self.assertEqual(outside.read_text(encoding="utf-8"), "kint\n")

    def test_absolute(self) -> None:
        """Az abszolút út (`/etc/hosts`) nem írható."""
        # Adott a rendszer hosts-fájlja
        # Ha a lap abszolút úttal írna
        # Akkor hiba, a fájl nem változik
        self.assert_refused("/etc/hosts", lambda repo: Path("/etc/hosts"))

    def test_ignored(self) -> None:
        """A git által nem ismert (ignorált) fájl nem írható."""
        # Adott egy ignorált fájl
        repo, gg, wip = self.repo()
        (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        (repo / ".env").write_text("TITOK=1\n", encoding="utf-8")
        # Ha a lap írná
        with self.assertRaises(ValueError):
            gg.files.write_file(wip, ".env", "TITOK=2\n", sha256(b"TITOK=1\n"))
        # Akkor nem változik
        self.assertEqual((repo / ".env").read_text(encoding="utf-8"), "TITOK=1\n")

    def test_missing(self) -> None:
        """Nem létező fájl és mappa nem írható (új fájlt nem hoz létre)."""
        # Adott egy repó
        repo, gg, wip = self.repo()
        (repo / "mappa").mkdir()
        (repo / "mappa" / "x.txt").write_text("x\n", encoding="utf-8")
        # Ha a lap nem létező fájlt vagy mappát írna
        # Akkor hiba, nem jön létre semmi
        for path in ("nincs.txt", "mappa"):
            with self.assertRaises(ValueError, msg=path):
                gg.files.write_file(wip, path, "x\n", sha256(b""))
        self.assertFalse((repo / "nincs.txt").exists())


class LineEndingTest(FilesCase):
    def test_crlf(self) -> None:
        """A CRLF sorvégű, záró újsor nélküli fájl egy sor átírása után is CRLF, záró újsor nélkül."""
        # Adott egy CRLF sorvégű, záró újsor nélküli "win.txt"
        repo, gg, wip = self.repo()
        (repo / "win.txt").write_bytes(b"egy\r\nketto\r\nharom")
        base = gg.diff.file_diff(wip, "win.txt", side="new")["hash"]
        # Ha a lap (`\n`-nel) egy sort átír és ment
        out = gg.files.write_file(wip, "win.txt", "egy\nKETTO\nharom", base)
        # Akkor a fájl CRLF sorvégű marad, záró újsor nélkül
        self.assertEqual((repo / "win.txt").read_bytes(), b"egy\r\nKETTO\r\nharom")
        self.assertEqual(out["hash"], sha256(b"egy\r\nKETTO\r\nharom"))

    def test_lf(self) -> None:
        """Az LF-es fájl LF marad, a záró újsor a szöveg szerint."""
        # Adott egy LF-es fájl
        repo, gg, wip = self.repo()
        base = sha256((repo / "a.txt").read_bytes())
        # Ha a lap ment
        gg.files.write_file(wip, "a.txt", "1\n2\n", base)
        # Akkor LF-fel íródik
        self.assertEqual((repo / "a.txt").read_bytes(), b"1\n2\n")


class NonTextTest(FilesCase):
    def test_binary(self) -> None:
        """A lemezen lévő bináris (NUL-os) fájl nem íródik."""
        # Adott egy bináris fájl
        repo, gg, wip = self.repo()
        (repo / "x.bin").write_bytes(b"a\0b")
        # Ha a lap írná
        with self.assertRaises(ValueError):
            gg.files.write_file(wip, "x.bin", "ab", sha256(b"a\0b"))
        # Akkor nem változik
        self.assertEqual((repo / "x.bin").read_bytes(), b"a\0b")

    def test_not_utf8(self) -> None:
        """A nem UTF-8 fájl nem íródik."""
        # Adott egy Latin-2 fájl
        repo, gg, wip = self.repo()
        (repo / "l2.txt").write_bytes("árvíztűrő\n".encode("iso-8859-2"))
        before = (repo / "l2.txt").read_bytes()
        # Ha a lap írná
        with self.assertRaises(ValueError):
            gg.files.write_file(wip, "l2.txt", "x\n", sha256(before))
        # Akkor nem változik
        self.assertEqual((repo / "l2.txt").read_bytes(), before)

    def test_nul_text(self) -> None:
        """A NUL-t tartalmazó és a túl nagy szöveg nem íródik."""
        # Adott egy szöveges fájl
        repo, gg, wip = self.repo()
        base = sha256(b"1\n")
        # Ha a lap NUL-os vagy 2 MB fölötti szöveget küld
        # Akkor hiba, a fájl nem változik
        for text in ("a\0b", "x" * (gg.diff.TEXT_MAX + 1)):
            with self.assertRaises(ValueError):
                gg.files.write_file(wip, "a.txt", text, base)
        self.assertEqual((repo / "a.txt").read_bytes(), b"1\n")

