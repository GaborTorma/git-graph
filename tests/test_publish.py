"""Publikálás (`publish`): a betöltő kiírása, a session lépései, a publikált lap hashe."""
from __future__ import annotations

from helpers import HomeTestCase


class PublishTest(HomeTestCase):
    def test_flow(self) -> None:
        """Nincs Artifact → lépések ikonnal; publikálva → naprakész; capability-változás → frissítés."""
        gg = self.load()
        repo = self.plain_repo()
        gg.gitio.set_repo(repo)
        job = gg.publish.prepare_publish()
        self.assertEqual(job["url"], "")
        self.assertEqual(job["page"], gg.publish.artifact_path(repo))
        self.assertIn("<title>Git Graph (plain)</title>", job["page"].read_text(encoding="utf-8"))
        steps = gg.publish.publish_steps(job)
        self.assertIn('icon: "branch"', steps)
        self.assertIn("--published <URL>", steps)
        self.assertNotIn('action: "read"', steps)

        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertEqual(gg.gitio.config_get("artifact"), "https://claude.ai/artifact/x")
        self.assertIsNone(gg.publish.prepare_publish())

        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].append("uj_tool")
        job = gg.publish.prepare_publish()
        self.assertEqual(job["url"], "https://claude.ai/artifact/x")
        steps = gg.publish.publish_steps(job)
        self.assertTrue(steps.startswith('1) Artifact, action: "read", url: https://claude.ai/artifact/x'))
        self.assertIn("uj_tool", steps)

    def test_mark_published_needs_page(self) -> None:
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        with self.assertRaises(SystemExit):
            gg.publish.mark_published("https://claude.ai/artifact/x")

    def test_mark_published_enables_auto(self) -> None:
        """Az új Artifact (a `--forget` után is) bekapcsolt automatikus megnyitással indul;
        a meglévő frissítése a kikapcsoltat nem kapcsolja vissza."""
        gg = self.load()
        repo = self.plain_repo()
        gg.registry.forget(repo)
        gg.publish.prepare_publish()
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertTrue(gg.publish.auto_open())
        gg.publish.settings({"autoOpen": False})
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertFalse(gg.publish.auto_open())

    def test_settings(self) -> None:
        """Alapból mindkettő be; a megnyitás a repóé, a publikálás a gépé."""
        gg = self.load()
        repo, other = self.plain_repo(), self.plain_repo("other")
        gg.gitio.set_repo(repo)
        self.assertEqual(gg.publish.settings({}), {"autoOpen": True, "autoPublish": True})
        self.assertEqual(gg.publish.settings({"autoOpen": False, "autoPublish": False}),
                         {"autoOpen": False, "autoPublish": False})
        self.assertEqual(gg.gitio.config_get("autoOpen"), "false")
        gg.gitio.set_repo(other)
        self.assertEqual(gg.publish.settings({"autoOpen": "nem bool"}), {"autoOpen": True, "autoPublish": False})

    def test_set_artifact_drops_hash(self) -> None:
        """Kézi URL (`--set-artifact`): a régi hash már nem érvényes."""
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        gg.publish.prepare_publish()
        gg.publish.mark_published("https://claude.ai/artifact/x")
        gg.gitio.remember_artifact("https://claude.ai/artifact/y")
        self.assertEqual(gg.gitio.config_get("artifactHash"), "")
        self.assertIsNotNone(gg.publish.prepare_publish())
