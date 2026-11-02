"""A WIP sor szerkesztése (#56): csak az Uncommitted sor szöveges fájlja, dupla kattintással, a nézet
ugrása nélkül; automatikus mentés, a lemez változásának befésülése, a hunk elvetése."""
from __future__ import annotations

import unittest
from pathlib import Path

from harness import PageTestCase, git_in

LINES = [f"sor_{i:02d} = 'egy hosszabb szoveg a sorban'" for i in range(1, 81)]


def text(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def changed(drop: int | None = None, **at: str) -> str:
    """A `LINES` másolata: a `drop`. sor törölve, az `at` sorai (`s<n>`) cserélve."""
    out = [at.get(f"s{i}", line) for i, line in enumerate(LINES, 1)]
    return text(out) if drop is None else text(out[:drop - 1] + out[drop:])


SPREAD = {f"s{i}": f"sor_{i:02d} = 'valtozott'" for i in (2, 20, 38, 56, 74)}   # a 40. és a 72. sor körül nincs rés


# fájl → (commitolt, munkakönyvtár); minden teszt a saját fájlját szerkeszti
FILES = {
    "kezd.py": (text(LINES), changed(drop=41, s38="sor_38 = 'valtozott'")),
    "elo.py": (text(LINES), changed(**SPREAD)),
    "auto.py": (text(LINES), changed(**SPREAD)),
    "azonnal.py": (text(LINES), changed(**SPREAD)),
    "kilep.py": (text(LINES), changed(**SPREAD)),
    "katt.py": (text(LINES), changed(**SPREAD)),
    "kereso.py": (text(LINES), changed(**SPREAD)),
    "kulso.py": (text(LINES), changed(**SPREAD)),
    "utkozes.py": (text(LINES), changed(**SPREAD)),
    "elvet.py": (text(LINES), changed(s40="sor_40 = 'uj valtozat'")),
    "elvet2.py": (text(LINES), changed(s40="sor_40 = 'uj valtozat'")),
    "keret.py": (text(LINES), changed(**SPREAD)),
    "app.py": ("a = 1\n", "a = 2\n"),
    "README.md": ("# Cím\n", "# Új cím\n"),
    "leiras.md": ("# Leírás\n\nElső bekezdés.\n", "# Leírás\n\nMásodik bekezdés.\n"),
    "dump.sql": ("-- régi\n" + "x" * 3_000_000 + "\n", "-- új\n" + "x" * 3_000_000 + "\n"),
    "bin/git-graph": ("#!/usr/bin/env python3\nprint('git-graph')\n", None),
}
PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000")

VIEW = "CM.EditorView.findFromDOM(document.querySelector(sel + ' .cm-content').closest('.cm-editor'))"
CURSOR = f"""sel => {{ const v = {VIEW}, h = v.state.selection.main.head, l = v.state.doc.lineAt(h);
  return [l.number, h - l.from, v.contentDOM.contentEditable]; }}"""
COORDS = f"""([sel, line, col]) => {{ const v = {VIEW}, p = v.state.doc.line(line).from + col;
  const c = v.coordsAtPos(p); return [c.left + 1, (c.top + c.bottom) / 2]; }}"""


class EditTest(PageTestCase):
    WIDTH, HEIGHT = 900, 800

    @classmethod
    def prepare(cls, repo: Path) -> None:
        for name, (old, _new) in FILES.items():
            (repo / name).parent.mkdir(parents=True, exist_ok=True)
            (repo / name).write_text(old, encoding="utf-8")
        (repo / "logo.png").write_bytes(PNG + b"\0regi")
        git_in(repo, "add", ".")
        git_in(repo, "commit", "-qm", "szerk: alap")
        (repo / "app.py").write_text("a = 3\n", encoding="utf-8")
        git_in(repo, "commit", "-qam", "szerk: app módosítva")
        for name, (_old, new) in FILES.items():
            if new is not None:
                (repo / name).write_text(new, encoding="utf-8")
        (repo / "logo.png").write_bytes(PNG + b"\0uj")
        git_in(repo, "add", "app.py")                       # a Stage-elt sor fájlja
        (repo / "app.py").write_text("a = 4\n", encoding="utf-8")

    def disk(self, name: str) -> str:
        return (self.repo / name).read_text(encoding="utf-8")

    def wip(self, subject: str = "Nem commitolt") -> None:
        row = self.page.locator(".row.uncommitted", has_text=subject)
        if row.get_attribute("aria-expanded") != "true":
            row.click()
            self.settle()

    def diff_of(self, name: str, subject: str = "Nem commitolt") -> str:
        """A WIP sor `name` fájlja lenyitva; vissza a diffje szelektora."""
        self.wip(subject)
        self.page.locator(f'.details .file[data-path="{name}"]').click()
        sel = f'.details .file[data-path="{name}"] + .diff'
        self.page.wait_for_selector(f"{sel} .cm-editor")
        self.settle()
        return sel

    def dblclick(self, sel: str, line: int, col: int) -> None:
        x, y = self.page.evaluate(f"({COORDS})", [sel, line, col])
        self.page.mouse.dblclick(x, y)

    def start(self, name: str, line: int = 20, col: int = 0) -> str:
        sel = self.diff_of(name)
        self.dblclick(sel, line, col)
        self.page.wait_for_function(f"({CURSOR})({sel!r})[2] === 'true'")
        return sel

    def full_view(self) -> None:
        self.page.locator("#fullBtn").click()
        self.page.wait_for_selector(".fv")
        self.settle()

    # ── Szerkesztés kezdete ──
    def test_start_at_click(self) -> None:
        """A 40. sor 12. karakterére duplán kattintva a kurzor ott áll, a nézet egy pixelt sem mozdul."""
        sel = self.diff_of("kezd.py")
        top = lambda: self.page.locator(sel).bounding_box()["y"]   # noqa: E731
        before = top()
        self.dblclick(sel, 40, 11)
        self.page.wait_for_function(f"({CURSOR})({sel!r})[2] === 'true'")
        self.assertEqual(self.page.evaluate(f"({CURSOR})", sel)[:2], [40, 11])
        self.assertEqual(top(), before)
        self.page.keyboard.press("Escape")

    def test_dblclick_old_line(self) -> None:
        """A 40. és 41. új sor közti törölt sorra duplán kattintva a kurzor a 41. új sor elején áll."""
        sel = self.diff_of("kezd.py")
        old = self.page.locator(f"{sel} .cm-deletedChunk", has_text="sor_41").bounding_box()
        self.page.mouse.dblclick(old["x"] + 40, old["y"] + old["height"] / 2)
        self.page.wait_for_function(f"({CURSOR})({sel!r})[2] === 'true'")
        self.assertEqual(self.page.evaluate(f"({CURSOR})", sel)[:2], [41, 0])
        self.page.keyboard.press("Escape")

    def test_unchanged_file_editable(self) -> None:
        """A WIP sor összes fájl nézetében a nem módosult bin/git-graph dupla kattintásra szerkeszthető."""
        self.wip()
        self.full_view()
        self.page.locator(".fv-diff").click()
        self.page.wait_for_selector('.fv-row[data-dir="bin"]')
        self.page.locator('.fv-row[data-dir="bin"]').click()
        self.page.locator('.fv-file[data-path="bin/git-graph"]').click()
        self.page.wait_for_selector(".fv-path:has-text('bin/git-graph')")
        self.page.wait_for_selector(".fv-box .cm-editor")
        self.settle()
        self.dblclick(".fv-box", 2, 2)
        self.page.wait_for_function(f"({CURSOR})('.fv-box')[2] === 'true'")
        self.page.keyboard.press("Escape")

    def test_not_editable(self) -> None:
        """A Stage-elt sor, a commit sor, az Uncommitted sor renderelt markdownja, képe és 3 MB-os fájlja nem
        szerkeszthető."""
        cases = [("Stage-elt", "app.py"), ("Nem commitolt", "dump.sql")]
        for subject, name in cases:
            with self.subTest(f"{subject} {name}"):
                sel = self.diff_of(name, subject)
                self.dblclick(sel, 1, 1)
                self.page.wait_for_timeout(200)
                self.assertNotEqual(self.page.evaluate(f"({CURSOR})", sel)[2], "true")
                if name == "dump.sql":
                    self.assertIn("a diff túl hosszú", self.page.locator(sel).inner_text())
        with self.subTest("egy commit sor app.py"):
            self.page.locator("#rows .row", has_text="szerk: app módosítva").click()
            self.settle()
            self.page.locator('#rows .details .file[data-path="app.py"]').click()
            sel = '#rows .details .file[data-path="app.py"] + .diff'
            self.page.wait_for_selector(f"{sel} .cm-editor")
            self.dblclick(sel, 1, 1)
            self.page.wait_for_timeout(200)
            self.assertNotEqual(self.page.evaluate(f"({CURSOR})", sel)[2], "true")
        for name in ("README.md", "logo.png"):
            with self.subTest(f"Uncommitted {name}"):
                self.wip()
                self.page.locator(f'.details .file[data-path="{name}"]').click()
                box = self.page.locator(f'.details .file[data-path="{name}"] + .diff')
                self.page.wait_for_timeout(500)
                box.dblclick()
                self.assertEqual(box.locator("[contenteditable=true]").count(), 0)

    def test_markdown_source(self) -> None:
        """A markdown forrása a nyers nézetben dupla kattintásra szerkeszthető, és a mentés a lemezre kerül."""
        with self.subTest("Adott az Uncommitted sor leiras.md-je nyers nézetben"):
            self.wip()
            self.page.locator('.details .file[data-path="leiras.md"]').click()
            self.page.wait_for_selector('.details .file[data-path="leiras.md"] + .diff .md-doc')
            self.page.locator('.details .file[data-path="leiras.md"] + .diff [data-md-mode="raw"]').click()
            sel = '.details .file[data-path="leiras.md"] + .diff'
            self.page.wait_for_selector(f"{sel} .cm-editor")
            self.settle()
        with self.subTest("Ha a forrás 3. sorára duplán kattint és gépel"):
            self.dblclick(sel, 3, 0)
            self.page.wait_for_function(f"({CURSOR})({sel!r})[2] === 'true'")
            self.page.keyboard.type("Szerkesztve. ")
            self.page.keyboard.press("Escape")
        with self.subTest("Akkor a szöveg a lemezen"):
            self.page.wait_for_function(f"({CURSOR})({sel!r})[2] !== 'true'")
            self.page.wait_for_timeout(300)
            self.assertIn("Szerkesztve. Második bekezdés.", self.disk("leiras.md"))

    def test_live_marking(self) -> None:
        """Egy változatlan sorba gépelt szó a sort gépelés közben változottként jelöli."""
        sel = self.start("elo.py", 39, 0)
        self.page.keyboard.type("szo ")
        line = self.page.locator(f"{sel} .cm-line", has_text="szo sor_39")
        self.assertIn("cm-changedLine", line.get_attribute("class"))

    def test_escape_in_full_view(self) -> None:
        """A teljes nézetbeli szerkesztésből Esc-re kilép, a függő mentés lefut, a nézet nyitva marad."""
        self.wip()
        self.page.locator('.details .file[data-path="kilep.py"]').click()
        self.settle()
        self.full_view()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()
        self.dblclick(".fv-box", 20, 0)
        self.page.wait_for_function(f"({CURSOR})('.fv-box')[2] === 'true'")
        self.page.keyboard.type("esc ")
        self.page.keyboard.press("Escape")
        self.page.wait_for_function(f"({CURSOR})('.fv-box')[2] !== 'true'")
        self.assertEqual(self.page.locator(".fv").count(), 1)
        self.page.wait_for_timeout(300)
        self.assertIn("esc sor_20", self.disk("kilep.py"))

    def test_leave_by_click(self) -> None:
        """A fában egy másik fájlra kattintva a szerkesztés véget ér, és a függő mentés lefut."""
        self.wip()
        self.page.locator('.details .file[data-path="katt.py"]').click()
        self.settle()
        self.full_view()
        self.page.wait_for_selector(".fv .fv-box .cm-editor")
        self.settle()
        self.dblclick(".fv-box", 20, 0)
        self.page.wait_for_function(f"({CURSOR})('.fv-box')[2] === 'true'")
        self.page.keyboard.type("katt ")
        self.page.locator('.fv-file[data-path="elvet.py"]').click()
        self.page.wait_for_timeout(400)
        self.assertIn("katt sor_20", self.disk("katt.py"))

    def test_find(self) -> None:
        """Szerkesztés közben a ⌘F a CodeMirror keresőjét nyitja."""
        sel = self.start("kereso.py")
        self.page.keyboard.press("ControlOrMeta+f")
        self.page.wait_for_selector(f"{sel} .cm-search")

    # ── Mentés ──
    def test_autosave(self) -> None:
        """Gépelés, majd 1 s csend után a fájl a lemezre íródik."""
        self.start("auto.py")
        self.page.keyboard.type("auto ")
        self.page.wait_for_timeout(300)
        self.assertNotIn("auto sor_20", self.disk("auto.py"))
        self.page.wait_for_timeout(1300)
        self.assertIn("auto sor_20", self.disk("auto.py"))

    def test_save_now(self) -> None:
        """A ⌘S azonnal a lemezre írja a fájlt."""
        self.start("azonnal.py")
        self.page.keyboard.type("most ")
        self.page.keyboard.press("ControlOrMeta+s")
        self.page.wait_for_timeout(300)
        self.assertIn("most sor_20", self.disk("azonnal.py"))

    def test_external_change(self) -> None:
        """A 40. sor szerkesztése közben a lemezen módosult 200. (itt: 72.) sor a nézetben frissül, kéken
        felvillan, a Fejlesztő szerkesztése megmarad."""
        sel = self.start("kulso.py", 40, 0)
        self.page.keyboard.type("enyem ")
        disk = self.disk("kulso.py").replace("sor_72 = 'egy", "sor_72 = 'kivulrol egy")
        (self.repo / "kulso.py").write_text(disk, encoding="utf-8")
        self.page.evaluate("window.__poke()")
        line = self.page.locator(f"{sel} .cm-line", has_text="kivulrol")
        line.wait_for()
        self.assertIn("cm-flash", line.get_attribute("class"))
        self.assertEqual(self.page.locator(f"{sel} .cm-line", has_text="enyem sor_40").count(), 1)
        self.page.wait_for_timeout(1500)
        on_disk = self.disk("kulso.py")
        self.assertIn("enyem sor_40", on_disk)
        self.assertIn("kivulrol", on_disk)

    def test_conflict(self) -> None:
        """A nem mentett 40. sort a lemezen is átírták: mindkét változat a két gombbal, és amíg a
        Fejlesztő nem választ, nem íródik semmi."""
        sel = self.start("utkozes.py", 40, 0)
        self.page.keyboard.type("enyem ")
        disk = self.disk("utkozes.py").replace("sor_40 = 'egy", "sor_40 = 'lemezen egy")
        (self.repo / "utkozes.py").write_text(disk, encoding="utf-8")
        self.page.keyboard.press("ControlOrMeta+s")
        box = self.page.locator(f"{sel} .cm-conflict")
        box.wait_for()
        self.assertIn("enyem sor_40", box.inner_text())
        self.assertIn("lemezen egy", box.inner_text())
        self.assertEqual(box.locator("button").all_inner_texts(), ["Az enyém marad", "A lemezen lévőt veszem"])
        self.page.keyboard.type("meg ")
        self.page.wait_for_timeout(1500)
        self.assertEqual(self.disk("utkozes.py"), disk)
        box.locator("button", has_text="Az enyém marad").click()
        self.page.wait_for_timeout(400)
        self.assertIn("enyem meg sor_40", self.disk("utkozes.py"))

    # ── Elvetés ──
    def test_reject_and_undo(self) -> None:
        """A hunk „Elvetés” gombja a régi változatra állítja vissza és menti; a ⌘Z visszahozza és menti."""
        sel = self.diff_of("elvet.py")
        btn = self.page.locator(f"{sel} .cm-reject").first
        line = self.page.locator(f"{sel} .cm-line").first.bounding_box()["height"]
        box = btn.bounding_box()
        self.assertLessEqual(box["height"], line)                          # ikon, egy sornyi
        self.assertEqual(btn.get_attribute("aria-label"), "Elvetés")
        self.assertEqual(btn.locator("svg").count(), 1)
        self.assertNotEqual(btn.evaluate("b => getComputedStyle(b).color"), "rgb(255, 255, 255)")   # az ikon látszik
        self.assertEqual(btn.evaluate("b => getComputedStyle(b).backgroundColor"), "rgba(0, 0, 0, 0)")  # háttér csak hoverre
        chunk = btn.locator("xpath=ancestor::div[contains(@class, 'cm-deletedChunk')]").bounding_box()
        self.assertAlmostEqual(box["y"] + box["height"] / 2, chunk["y"] + line / 2, delta=1.5)       # az első sor közepén
        right = self.page.locator(f"{sel} .cm-content").bounding_box()
        self.assertLessEqual(right["x"] + right["width"] - (box["x"] + box["width"]), 2)
        btn.click()
        self.page.wait_for_timeout(1500)
        self.assertNotIn("uj valtozat", self.disk("elvet.py"))
        self.page.keyboard.press("ControlOrMeta+z")
        self.page.wait_for_timeout(1500)
        self.assertIn("uj valtozat", self.disk("elvet.py"))

    def test_reject_side_by_side(self) -> None:
        """Egymás mellett a két oldal közti ikongomb veti el a változásblokkot, és a mentés a lemezre írja."""
        self.resize(1300)
        sel = self.diff_of("elvet2.py")
        btn = self.page.locator(f"{sel} .cm-merge-revert .cm-reject").first
        self.assertTrue(btn.is_visible())
        btn.click()
        self.page.wait_for_timeout(1500)
        self.assertNotIn("uj valtozat", self.disk("elvet2.py"))

    def test_edit_frame(self) -> None:
        """A szerkesztés kék keretén belül van hely (a tartalom nem lóg rá), és a sorszámok után nincs
        kék fókuszvonal."""
        sel = self.start("keret.py", 39, 0)
        frame = self.page.locator(f"{sel} .cm-diff").bounding_box()
        content = self.page.locator(f"{sel} .cm-editor").bounding_box()
        self.assertGreaterEqual(content["x"] - frame["x"], 3)
        self.assertGreaterEqual(frame["x"] + frame["width"] - (content["x"] + content["width"]), 3)
        ring = self.page.locator(f"{sel} .cm-content").evaluate("e => getComputedStyle(e).boxShadow")
        self.assertEqual(ring, "none")


class CleanEditTest(PageTestCase):
    """Tiszta worktree-ben (nincs WIP sor) a HEAD-commit fájlja szerkeszthető; az első mentéstől a
    fájl a WIP soré, a teljes nézet átvált rá."""

    def test_edit_from_head(self) -> None:
        # Adott: nincs nem commitolt változás, egy commit sincs lenyitva
        self.assertEqual(self.page.locator(".row.uncommitted").count(), 0)
        self.page.locator("#fullBtn").click()
        self.page.wait_for_selector('.fv-file[data-path="main-0-0.txt"]')
        self.page.locator('.fv-file[data-path="main-0-0.txt"]').click()
        self.page.wait_for_selector(".fv-box .cm-editor")
        self.settle()
        # Ha a Fejlesztő duplán kattint, gépel és ment
        x, y = self.page.evaluate(f"({COORDS})", [".fv-box", 1, 0])
        self.page.mouse.dblclick(x, y)
        self.page.wait_for_function(f"({CURSOR})('.fv-box')[2] === 'true'")
        self.page.keyboard.type("elso ")
        self.page.keyboard.press("ControlOrMeta+s")
        self.page.wait_for_timeout(300)
        self.assertEqual((self.repo / "main-0-0.txt").read_text(encoding="utf-8"), "elso main-0-0\n")
        # Akkor megjelenik a WIP sor, a nézet átvált rá, a szerkesztés folytatható
        self.poke()
        self.assertEqual(self.page.locator(".row.uncommitted").count(), 1)
        self.assertEqual(self.page.locator(".fv-subject").inner_text(), "Nem commitolt változások")
        self.assertEqual(self.page.evaluate(f"({CURSOR})('.fv-box')")[2], "true")
        self.page.keyboard.type("masodik ")
        self.page.keyboard.press("ControlOrMeta+s")
        self.page.wait_for_timeout(300)
        self.assertEqual((self.repo / "main-0-0.txt").read_text(encoding="utf-8"), "elso masodik main-0-0\n")


if __name__ == "__main__":
    unittest.main()
