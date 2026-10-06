"""Telepítés, frissítés, leszerelés (`install`) — kamu HOME-mal, a valódi apphoz nem nyúl."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from helpers import PYTHON, ROOT, HomeTestCase


class InstallTest(HomeTestCase):
    def manifest(self) -> Path:
        return self.state / ".claude-plugin" / "plugin.json"

    def registry(self, plugins: dict) -> None:
        path = self.home / ".claude" / "plugins" / "installed_plugins.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"version": 2, "plugins": plugins}), encoding="utf-8")

    def fake_plugin(self, version: str, *, complete: bool = True) -> Path:
        """Egy telepített plugin mappája (a working tree másolata) a megadott verzióval."""
        root = self.home / "cache" / version
        shutil.copytree(ROOT / "page", root / "page")
        if complete:
            shutil.copytree(ROOT / "git_graph", root / "git_graph",
                            ignore=shutil.ignore_patterns("__pycache__"))
        (root / ".claude-plugin").mkdir()
        (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"version": version}), encoding="utf-8")
        return root

    def test_stable_bundle(self) -> None:
        """A zip determinisztikus, minden modult visz, és magában futtatható."""
        gg = self.load()
        bundle = gg.install.stable_bundle(ROOT)
        self.assertEqual(bundle, gg.install.stable_bundle(ROOT))
        self.assertTrue(bundle.startswith(b"#!"))
        target = self.home / "gg.zip"
        target.write_bytes(bundle)
        names = set(zipfile.ZipFile(target).namelist())
        modules = {f"git_graph/{p.name}" for p in (ROOT / "git_graph").glob("*.py")}
        self.assertEqual(names, {"__main__.py"} | modules)
        out = subprocess.run([PYTHON, str(target), "--help"], capture_output=True, text=True,
                             env={**os.environ, "HOME": str(self.home)})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("--mcp", out.stdout)

    def test_install_copy(self) -> None:
        """A stabil hely: lap, manifest, zip; változatlan forrásnál nem ír újra."""
        gg = self.load()
        gg.install.install_copy(ROOT)
        stable = gg.install.STABLE
        self.assertEqual(gg.install.stable_version(), gg.install.RUNNING_VERSION)
        os.utime(stable, (1, 1))
        gg.install.install_copy(ROOT)
        self.assertEqual(stable.stat().st_mtime, 1)

    def test_dev_active(self) -> None:
        """A friss dev-példányt a hook nem írja felül, a lejártat igen."""
        gg = self.load()
        manifest = self.manifest()
        manifest.parent.mkdir(parents=True)
        now = int(gg.install.time.time())
        for version, active in ((f"0.11.0+dev.{now}", True),
                                (f"0.11.0+dev.{now - gg.install.DEV_TTL - 60}", False),
                                ("0.11.0", False)):
            manifest.write_text(json.dumps({"version": version}), encoding="utf-8")
            self.assertEqual(gg.install.dev_active(), active, version)

    def test_pull_update(self) -> None:
        """Újabb telepített verzió: a futó szerver maga másolja a stabil helyre, és újraindulna;
        hiányos plugin-mappából és fejlesztői példányban nem másol."""
        gg = self.load()
        self.registry({"git-graph@git-graph": [{"version": "9.9.9", "installPath": str(self.fake_plugin(
            "9.9.9", complete=False))}]})
        self.assertFalse(gg.install.pull_update())
        self.assertFalse(gg.install.STABLE.exists())
        self.registry({"git-graph@git-graph": [{"version": "9.9.8", "installPath": str(self.fake_plugin(
            "9.9.8"))}]})
        gg.install.RUNNING_VERSION = "0.1.0+dev.1"
        self.assertFalse(gg.install.pull_update())
        gg.install.RUNNING_VERSION = "0.1.0"
        self.assertTrue(gg.install.pull_update())
        self.assertEqual(gg.install.stable_version(), "9.9.8")
        self.assertTrue(gg.install.STABLE.is_file())

    def test_plugin_installed(self) -> None:
        """Ismeretlen formátumnál nem dönt (None) — nehogy tévesen leszereljen."""
        gg = self.load()
        self.assertIsNone(gg.install.plugin_installed())                # nincs nyilvántartás
        self.registry({"mas@x": []})
        self.assertFalse(gg.install.plugin_installed())
        self.registry({"git-graph@git-graph": [{"version": "1"}]})
        self.assertTrue(gg.install.plugin_installed())
        self.assertEqual(gg.install.installed_version(), "1")
        path = self.home / ".claude" / "plugins" / "installed_plugins.json"
        path.write_text(json.dumps({"version": 3, "plugins": {}}), encoding="utf-8")
        self.assertIsNone(gg.install.plugin_installed())

    def test_app_config(self) -> None:
        """Az app configja: felvétel mentéssel, a többi szerver marad; leszereléskor ki, a
        `~/.git-graph` is törlődik. Hibás JSON-hoz nem nyúl."""
        gg = self.load()
        config = gg.install.APP_CONFIG
        self.assertFalse(gg.install.install_app_mcp())                  # nincs app a gépen
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"mcpServers": {"mas": {"command": "x"}}, "egyeb": 1}), encoding="utf-8")
        self.assertTrue(gg.install.install_app_mcp())
        self.assertFalse(gg.install.install_app_mcp())                  # változatlan: nem ír
        data = json.loads(config.read_text(encoding="utf-8"))
        self.assertEqual(data["mcpServers"]["git-graph"],
                         {"command": "/usr/bin/python3", "args": [str(gg.install.STABLE), "--mcp"]})
        self.assertIn("mas", data["mcpServers"])
        self.assertTrue(list(config.parent.glob("claude_desktop_config.json.bak-*")))
        gg.install.uninstall()
        data = json.loads(config.read_text(encoding="utf-8"))
        self.assertEqual(data, {"mcpServers": {"mas": {"command": "x"}}, "egyeb": 1})
        self.assertFalse(self.state.exists())
        config.write_text("{", encoding="utf-8")
        self.assertFalse(gg.install.install_app_mcp())
        self.assertEqual(config.read_text(encoding="utf-8"), "{")

    def test_ensure_installed(self) -> None:
        """Csak a plugin hookjából (CLAUDE_PLUGIN_ROOT = a kód gyökere) telepít."""
        gg = self.load()
        old = os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
        try:
            self.assertIsNone(gg.install.ensure_installed())
            os.environ["CLAUDE_PLUGIN_ROOT"] = str(self.home)
            self.assertIsNone(gg.install.ensure_installed())
            self.assertFalse(gg.install.STABLE.exists())
            os.environ["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
            gg.install.APP_CONFIG.parent.mkdir(parents=True)
            notice = gg.install.ensure_installed()
            self.assertTrue(gg.install.STABLE.is_file())
            if sys.platform == "darwin":
                self.assertIn("újra kell indítani", notice)
                self.assertIsNone(gg.install.ensure_installed())        # már bent van
        finally:
            os.environ.pop("CLAUDE_PLUGIN_ROOT", None)
            if old is not None:
                os.environ["CLAUDE_PLUGIN_ROOT"] = old

    def test_watch_plugin_uninstall(self) -> None:
        """A stabil példány két egymást követő hiány után leszerel; másik példány nem figyel."""
        gg = self.load()
        gg.install.watch_plugin()                                       # nem a stabil példány: kilép
        self.assertTrue(self.state.exists())
        self.registry({"mas@x": []})
        gg.install.STABLE = Path(sys.argv[0]).resolve()
        gg.install.PLUGIN_POLL_S = 0
        gg.install.watch_plugin()
        self.assertFalse(self.state.exists())
