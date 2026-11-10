"""Publikálás (`publish`): a betöltő kiírása, a session lépései, a publikált lap hashe."""
from __future__ import annotations

from helpers import HomeTestCase


class PublishTest(HomeTestCase):
    def test_flow(self) -> None:
        """Nincs Artifact → lépések címmel, ikonnal, a lap fájljával és a capability-vel; publikálva →
        naprakész; capability-változás → frissítés az élő verzió olvasásával, a teljes listával."""
        gg = self.load()
        repo = self.plain_repo()
        gg.gitio.set_repo(repo)
        job = gg.publish.prepare_publish()
        self.assertEqual(job["url"], "")
        self.assertEqual(job["page"], gg.publish.artifact_path(repo))
        self.assertIn("<title>Git Graph (plain)</title>", job["page"].read_text(encoding="utf-8"))
        steps = gg.publish.publish_steps(job)
        self.assertIn('title: "Git Graph (plain)", icon: "branch"', steps)
        self.assertIn(f'action: "publish", file_path: "{job["page"]}"', steps)
        self.assertIn('capabilities: {"mcp"', steps)
        self.assertIn(f'contract: "{gg.publish.PUBLISH_CONTRACT}"', steps)
        self.assertIn("újabb contractot jelez", steps)
        self.assertIn("--published <URL>", steps)
        self.assertNotIn('"read"', steps)

        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertEqual(gg.gitio.config_get("artifact"), "https://claude.ai/artifact/x")
        self.assertIsNone(gg.publish.prepare_publish())

        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].append("uj_tool")
        job = gg.publish.prepare_publish()
        self.assertEqual(job["url"], "https://claude.ai/artifact/x")
        steps = gg.publish.publish_steps(job)
        self.assertTrue(steps.startswith('1) Artifact, action: "read", url: https://claude.ai/artifact/x'))
        self.assertIn("uj_tool", steps.split('action: "publish"')[1])
        self.assertIn("url: https://claude.ai/artifact/x; 3)", steps)

    def test_caps_tools(self) -> None:
        """A lap capability-je a fájlfa és az író tool hívását is engedi."""
        # Adott a publikálás capability-deklarációja
        gg = self.load()
        # Ha a lap toolai közt keresünk
        tools = gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"]
        # Akkor az MCP szerver minden toolja benne van
        self.assertEqual(set(tools), {t["name"] for t in gg.mcp.MCP_TOOLS})

    def test_caps_tracking(self) -> None:
        """A publikálás a capability-lista és a contract hashét is rögzíti; ha bármelyik változik,
        a lap elavult; a kézi URL ismeretlen deklarációt jelent."""
        # Adott egy kiírt lap
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        gg.publish.prepare_publish()
        # Ha a session publikál, akkor a mostani deklaráció a nyilvántartott
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertTrue(gg.publish.caps_current())
        self.assertIsNone(gg.publish.prepare_publish())
        # Ha a capability-lista változik, akkor már nem a deklarált
        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].append("uj_tool")
        self.assertFalse(gg.publish.caps_current())
        gg.publish.PUBLISH_CAPS["mcp"]["servers"][0]["tools"].pop()
        # Ha a rögzített contract változik, akkor is újra kell publikálni
        gg.publish.PUBLISH_CONTRACT = "9.9.9"
        self.assertFalse(gg.publish.caps_current())
        self.assertIsNotNone(gg.publish.prepare_publish())
        gg.publish.mark_published("https://claude.ai/artifact/x")
        self.assertTrue(gg.publish.caps_current())
        # Ha kézzel adják meg az URL-t, akkor ismeretlen
        gg.gitio.remember_artifact("https://claude.ai/artifact/y")
        self.assertFalse(gg.publish.caps_current())

    def test_legacy_without_caps_record(self) -> None:
        """A nyilvántartás előtti lapnál (nincs `artifactCaps`) a lap hashe dönt, és abban a
        contract is benne van: a régi contracttal publikált lap elavult."""
        # Adott egy publikált lap, a capability-nyilvántartás nélkül
        gg = self.load()
        gg.gitio.set_repo(self.plain_repo())
        gg.publish.prepare_publish()
        gg.publish.mark_published("https://claude.ai/artifact/x")
        gg.gitio.git("config", "--local", "--unset", "git-graph.artifactCaps")
        self.assertTrue(gg.publish.caps_current())
        # Ha a contract változik, akkor elavult
        gg.publish.PUBLISH_CONTRACT = "9.9.9"
        self.assertFalse(gg.publish.caps_current())

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
