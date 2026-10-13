"""Sávkiosztás (`lanes`): merge, a trunk sávja, a worktree-csonkok."""
from __future__ import annotations

from helpers import HomeTestCase


class LanesTest(HomeTestCase):
    def test_assign_lanes(self) -> None:
        """Merge: az első szülő a sávban folytatódik, a második új sávot kap; az élek sorindexesek."""
        gg = self.load()
        commits = [{"sha": "m", "parents": ["a", "b"]},
                   {"sha": "b", "parents": ["a"]},
                   {"sha": "a", "parents": []}]
        edges = gg.lanes.assign_lanes(commits)
        self.assertEqual([c["lane"] for c in commits], [0, 1, 0])
        self.assertIn({"fromRow": 0, "fromLane": 0, "toRow": 1, "toLane": 1, "merge": True}, edges)
        self.assertIn({"fromRow": 1, "fromLane": 1, "toRow": 2, "toLane": 0, "merge": False}, edges)

    def test_assign_lanes_trunk(self) -> None:
        """A `trunk` a 0. sávot kapja akkor is, ha egy újabb commit előtte jön."""
        gg = self.load()
        commits = [{"sha": "f", "parents": ["a"]}, {"sha": "t", "parents": ["a"]}, {"sha": "a", "parents": []}]
        gg.lanes.assign_lanes(commits, trunk="t")
        self.assertEqual([c["lane"] for c in commits], [1, 0, 0])

    def test_worktree_stubs(self) -> None:
        """Saját commit és WIP nélküli worktree HEAD-je csonkot kap; a saját ág csúcsa nem."""
        gg = self.load()
        commits = [{"sha": "c", "parents": ["a"], "refs": []},   # feat: saját ág
                   {"sha": "b", "parents": ["a"], "refs": []},   # trunk
                   {"sha": "a", "parents": [], "refs": []}]
        edges = gg.lanes.assign_lanes(commits, "b")
        wt = lambda slug, head, main=False: {"slug": slug, "head": head, "main": main}  # noqa: E731
        gg.lanes.worktree_stubs(commits, edges, [wt("m", "b", True), wt("feat", "c"), wt("old", "a")])
        self.assertNotIn("stubs", commits[0])
        self.assertNotIn("stubs", commits[1])
        self.assertEqual(commits[2]["stubs"], [{"lane": 2, "worktree": "old"}])
