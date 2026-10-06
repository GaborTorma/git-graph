"""A `changes` long-poll (`watch`): az állapot-hash és a nyitva tartott hívás."""
from __future__ import annotations

import os
import time

from helpers import HomeTestCase, focus_line, git_in


class WatchTest(HomeTestCase):
    def test_repo_state(self) -> None:
        """Az állapot-hash: egy már módosított fájl újabb szerkesztése, új fájl és ágváltás is változás."""
        repo = self.plain_repo("state")
        gg = self.load()
        states = [gg.watch.repo_state(repo)]
        (repo / "a.txt").write_text("2", encoding="utf-8")
        states.append(gg.watch.repo_state(repo))
        os.utime(repo / "a.txt", ns=(1, time.time_ns() + 10**9))     # ugyanaz a státusz, újabb mtime
        states.append(gg.watch.repo_state(repo))
        (repo / "b.txt").write_text("x", encoding="utf-8")
        states.append(gg.watch.repo_state(repo))
        git_in(repo, "switch", "-q", "-c", "feat")
        states.append(gg.watch.repo_state(repo))
        self.assertEqual(len(set(states)), len(states))
        self.assertEqual(gg.watch.repo_state(repo), states[-1])

    def test_wait_changes(self) -> None:
        """Üres since-re azonnal; a since óta jött session-váltásra és repóváltozásra a határidő
        előtt, különben a határidőre válaszol."""
        main, _ = self.make_repo()
        gg = self.load()
        log = gg.claude_app.APP_LOG
        log.parent.mkdir(parents=True)
        log.write_text("", encoding="utf-8")
        first = gg.watch.wait_changes(main, "", 5)
        self.assertTrue({"since", "state", "focus", "version", "installed"} <= set(first))
        since = first["since"]
        t0 = time.monotonic()
        self.assertEqual(gg.watch.wait_changes(main, since, 0.1)["since"], since)
        self.assertLess(time.monotonic() - t0, 1)
        with log.open("a", encoding="utf-8") as f:
            f.write(focus_line("local_a"))
        t0 = time.monotonic()
        after = gg.watch.wait_changes(main, since, 5)
        self.assertNotEqual(after["since"], since)
        self.assertEqual(after["state"], since.partition(".")[0])           # csak a fókusz
        (main / "uj.txt").write_text("x", encoding="utf-8")
        changed = gg.watch.wait_changes(main, after["since"], 5)
        self.assertNotEqual(changed["state"], after["state"])
        self.assertLess(time.monotonic() - t0, 4)

    def test_wake(self) -> None:
        """Újraindulás előtt (`WAKE`) a várakozó hívás azonnal válaszol."""
        repo = self.plain_repo()
        gg = self.load()
        since = gg.watch.wait_changes(repo, "", 0)["since"]
        gg.watch.WAKE.set()
        t0 = time.monotonic()
        gg.watch.wait_changes(repo, since, 5)
        self.assertLess(time.monotonic() - t0, 1)

    def test_git_signal(self) -> None:
        """Egy git-művelet (commit) a stat-előszűrőn át gyorsan jön, nem a 2 s-os teljes körrel."""
        repo = self.plain_repo()
        gg = self.load()
        paths = gg.watch.stamp_paths(repo)
        before = gg.watch.file_stamp(paths)
        git_in(repo, "commit", "-q", "--allow-empty", "-m", "x")
        self.assertNotEqual(gg.watch.file_stamp(paths), before)
