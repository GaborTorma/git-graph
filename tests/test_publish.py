"""Publikálás (`publish`): a betöltő kiírása és a publikált lap hashe."""
from __future__ import annotations

from helpers import HomeTestCase


class PublishTest(HomeTestCase):
    def test_flow(self) -> None:
        """Nincs Artifact → a lap kiírva, címmel; publikálva → naprakész; capability-változás → újra kell,
        az élő URL-lel."""
        gg = self.load()
        repo = self.plain_repo()
        gg.gitio.set_repo(repo)
        job = gg.publish.prepare_publish()
        self.assertEqual((job["url"], job["title"]), ("", "Git Graph (plain)"))
        self.assertEqual(job["page"], gg.publish.artifact_path(repo))
        self.assertIn("<title>Git Graph (plain)</title>", job["page"].read_text(encoding="utf-8"))
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertEqual(gg.gitio.config_get("artifact"), "https://claude.ai/artifact/x")
        self.assertIsNone(gg.publish.prepare_publish())
        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].append("uj_tool")
        self.assertEqual(gg.publish.prepare_publish()["url"], "https://claude.ai/artifact/x")

    def test_caps_tools(self) -> None:
        """A lap capability-je a fájlfa és az író tool hívását is engedi."""
        # Adott a publikálás capability-deklarációja
        gg = self.load()
        # Ha a lap toolai közt keresünk
        tools = gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"]
        # Akkor az MCP szerver minden toolja benne van
        self.assertEqual(set(tools), {t["name"] for t in gg.mcp.MCP_TOOLS})

    def test_declaration_in_hash(self) -> None:
        """A lap hashe a capability-listát és a contractot is tartalmazza: ha bármelyik változik, a
        lap elavult; a publikálás után újra naprakész; a kézi URL ismeretlen hasht jelent."""
        # Adott egy publikált lap
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        gg.publish.prepare_publish()
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertIsNone(gg.publish.prepare_publish())
        # Ha a capability-lista változik, akkor elavult
        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].append("uj_tool")
        self.assertIsNotNone(gg.publish.prepare_publish())
        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].pop()
        self.assertIsNone(gg.publish.prepare_publish())
        # Ha a rögzített contract változik, akkor is, a publikálás után már nem
        gg.publish.PUBLISH_CONTRACT = "9.9.9"
        self.assertIsNotNone(gg.publish.prepare_publish())
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertIsNone(gg.publish.prepare_publish())
        # Ha kézzel adják meg az URL-t, akkor újra kell publikálni
        gg.gitio.remember_artifact("https://claude.ai/artifact/y")
        self.assertIsNotNone(gg.publish.prepare_publish())

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
        self.assertEqual(gg.publish.settings({}), {"autoOpen": True, "autoPublish": True, "collapseMerges": True})
        self.assertEqual(gg.publish.settings({"autoOpen": False, "autoPublish": False}),
                         {"autoOpen": False, "autoPublish": False, "collapseMerges": True})
        self.assertEqual(gg.gitio.config_get("autoOpen"), "false")
        gg.gitio.set_repo(other)
        self.assertEqual(gg.publish.settings({"autoOpen": "nem bool"}),
                         {"autoOpen": True, "autoPublish": False, "collapseMerges": True})

    def test_collapse_merges_default(self) -> None:
        """Hiányzó `git-graph.collapseMerges` kulcsnál a merge-ek összecsukása bekapcsolva."""
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        self.assertIs(gg.publish.settings({})["collapseMerges"], True)

    def test_collapse_merges_off(self) -> None:
        """A `collapseMerges: false` a repó `.git/config`-jába kerül, és a válasz is ezt adja."""
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        self.assertIs(gg.publish.settings({"collapseMerges": False})["collapseMerges"], False)
        self.assertEqual(gg.gitio.config_get("collapseMerges"), "false")

    def test_set_artifact_drops_hash(self) -> None:
        """Kézi URL (`--set-artifact`): a régi hash már nem érvényes."""
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        gg.publish.prepare_publish()
        gg.publish.mark_published("https://claude.ai/artifact/x")
        gg.gitio.remember_artifact("https://claude.ai/artifact/y")
        self.assertEqual(gg.gitio.config_get("artifactHash"), "")
        self.assertIsNotNone(gg.publish.prepare_publish())
