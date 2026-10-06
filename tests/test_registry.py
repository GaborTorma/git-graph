"""A repók nyilvántartása (`registry`): slug, regiszter, sessionök, a nyomok törlése."""
from __future__ import annotations

import json
import time

from helpers import HomeTestCase, git_in


class RegistryTest(HomeTestCase):
    def test_slug_for(self) -> None:
        """Olvasható és egyértelmű: azonos mappanév, más út → más slug."""
        gg = self.load()
        a, b = gg.registry.slug_for(self.home / "x" / "My App"), gg.registry.slug_for(self.home / "y" / "My App")
        self.assertTrue(a.startswith("my-app-"))
        self.assertNotEqual(a, b)
        self.assertEqual(a, gg.registry.slug_for(self.home / "x" / "My App"))

    def test_register(self) -> None:
        gg = self.load()
        repo = self.plain_repo()
        slug = gg.registry.register(repo)
        self.assertEqual(gg.registry.repo_for_slug(slug), repo)
        self.assertIsNone(gg.registry.repo_for_slug("nincs"))
        self.assertIn(slug, gg.registry.registered_repos())

    def test_shown_in_session(self) -> None:
        """Sessionönként egyszer; a lejárt bejegyzés törlődik."""
        gg = self.load()
        sessions = gg.registry.SESSIONS
        sessions.write_text(json.dumps({"regi": {"x": time.time() - gg.registry.SESSION_TTL - 1}}),
                            encoding="utf-8")
        self.assertFalse(gg.registry.shown_in_session("s1", "x"))
        self.assertTrue(gg.registry.shown_in_session("s1", "x"))
        self.assertFalse(gg.registry.shown_in_session("s2", "x"))
        self.assertNotIn("regi", json.loads(sessions.read_text(encoding="utf-8")))
        sessions.write_text("[]", encoding="utf-8")                  # ismeretlen forma: újrakezdi
        self.assertFalse(gg.registry.shown_in_session("s1", "x"))

    def test_forget(self) -> None:
        """A config-szakasz, a helyi lap és a regiszterbejegyzés megy; a publikálás KI."""
        gg = self.load()
        repo = self.plain_repo()
        git_in(repo, "config", "git-graph.artifact", "https://claude.ai/artifact/x")
        slug = gg.registry.register(repo)
        (self.state / slug).mkdir()
        gg.registry.forget(repo)
        self.assertEqual(gg.gitio.config_get("artifact"), "")
        self.assertFalse((self.state / slug).exists())
        self.assertNotIn(slug, gg.registry.registered_repos())
        self.assertTrue(gg.registry.NO_AUTO_PUBLISH.exists())
        gg.registry.forget(repo)                                      # másodszor is lefut

    def test_list_artifacts(self) -> None:
        """A regisztrált repók és a szülőmappájuk többi repója; a worktree-k configja közös."""
        (self.state / "repos.json").write_text("{}", encoding="utf-8")     # csak a kamu repók
        gg = self.load()
        main, extra = self.make_repo()
        other = self.plain_repo("masik")                              # nincs regisztrálva
        git_in(main, "config", "git-graph.artifact", "https://claude.ai/artifact/a")
        git_in(other, "config", "git-graph.artifact", "https://claude.ai/artifact/b")
        self.plain_repo("ures")                                       # Artifact nélkül
        gg.registry.register(extra)
        self.assertEqual(sorted(gg.registry.list_artifacts()),
                         [(other, "https://claude.ai/artifact/b"), (main, "https://claude.ai/artifact/a")])
