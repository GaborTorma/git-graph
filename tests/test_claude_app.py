"""A Claude app belső fájljai (`claude_app`): az előtérben lévő session és az app worktree-inek ága."""
from __future__ import annotations

import json
import os

from helpers import HomeTestCase


class ClaudeAppTest(HomeTestCase):
    def test_focused_worktree(self) -> None:
        """A saját worktree a repóban dolgozó, legutóbb fókuszált desktop-sessioné."""
        main, extra = self.make_repo()
        gg = self.load()
        app = gg.claude_app
        folder = app.APP_SESSIONS / "acc" / "org"
        folder.mkdir(parents=True)

        def session(name: str, cwd, focused: float, **more: object) -> None:
            data = {"cwd": str(cwd), "lastFocusedAt": focused * 1000, **more}
            (folder / f"local_{name}.json").write_text(json.dumps(data), encoding="utf-8")

        wts = gg.gitio.worktree_list(main)
        self.assertEqual(app.focused_worktree(wts), {"worktree": None, "known": False})
        session("a", main, 100)
        session("b", extra / "sub", 200)
        session("c", self.home, 300)                                 # más repó: nem számít
        session("d", main, 400, isArchived=True)                     # archivált: nem számít
        (folder / "local_rossz.json").write_text("{", encoding="utf-8")   # olvashatatlan: kimarad
        self.assertEqual(app.focused_worktree(wts), {"worktree": gg.registry.slug_for(extra), "known": True})
        session("a", main, 500)                                      # visszaváltás a fő checkoutra
        os.utime(folder / "local_a.json", (1e9, 1e9))                # más mtime: újraolvassa
        self.assertEqual(app.focused_worktree(wts)["worktree"], gg.registry.slug_for(main))

        # Az app naplója a fájlnál előbb tudja a fókuszt; egy másodpercen belül a sorrend dönt.
        app.APP_LOG.parent.mkdir(parents=True)

        def focus(*ids: str, tail: str = "") -> None:
            with app.APP_LOG.open("a", encoding="utf-8") as f:
                for sid in ids:
                    f.write(f"2001-01-01 00:00:00 [info] [CCD] LocalSessions.setFocusedSession: sessionId={sid}\n")
                f.write(tail)

        focus("null", "local_b")
        self.assertEqual(app.focused_worktree(wts)["worktree"], gg.registry.slug_for(extra))
        focus("null", "local_a")
        self.assertEqual(app.focused_worktree(wts)["worktree"], gg.registry.slug_for(main))
        focus(tail="2001-01-01 00:00:00 [info] [CCD] LocalSessions.setFocusedSession: sessionId=local_b")
        self.assertEqual(app.focused_worktree(wts)["worktree"], gg.registry.slug_for(main))  # félbe írt sor
        focus(tail="\n")
        self.assertEqual(app.focused_worktree(wts)["worktree"], gg.registry.slug_for(extra))

    def test_log_rotation(self) -> None:
        """Forgatott napló (új fájl): az elejéről olvas tovább."""
        gg = self.load()
        app = gg.claude_app
        app.APP_LOG.parent.mkdir(parents=True)
        line = "2001-01-01 00:00:0{} [info] [CCD] LocalSessions.setFocusedSession: sessionId=local_{}\n"
        app.APP_LOG.write_text(line.format(0, "a") * 50, encoding="utf-8")
        self.assertIn("local_a", app.app_log_focus())
        app.APP_LOG.unlink()
        app.APP_LOG.write_text(line.format(1, "b"), encoding="utf-8")
        self.assertIn("local_b", app.app_log_focus())

    def test_worktree_of(self) -> None:
        """Egymásba ágyazott worktree-knél a legmélyebb nyer."""
        gg = self.load()
        outer, inner = self.home / "r", self.home / "r" / ".claude" / "worktrees" / "x"
        roots = [(outer, "kulso"), (inner, "belso")]
        self.assertEqual(gg.claude_app.worktree_of(str(inner / "src"), roots), "belso")
        self.assertEqual(gg.claude_app.worktree_of(str(outer / "src"), roots), "kulso")
        self.assertIsNone(gg.claude_app.worktree_of(str(self.home / "mas"), roots))

    def test_app_worktree_branches(self) -> None:
        """A leválasztott worktree ága a Claude app nyilvántartásából, a mappa szerint."""
        gg = self.load()
        app = gg.claude_app
        self.assertEqual(app.app_worktree_branches(), {})
        app.APP_WORKTREES.parent.mkdir(parents=True, exist_ok=True)
        folder = self.home / "wt"
        app.APP_WORKTREES.write_text(json.dumps({"worktrees": {
            "wt": {"path": str(folder), "branch": "claude/wt"}, "rossz": {"path": 1}}}), encoding="utf-8")
        self.assertEqual(app.app_worktree_branches(), {str(folder.resolve()): "claude/wt"})
