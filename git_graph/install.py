"""Plugin-telepítés (SessionStart hook), frissítés és leszerelés (`git-graph --mcp`)."""
from __future__ import annotations

import io
import json
import os
import shutil
import sys
import threading
import time
import zipfile
from pathlib import Path

from . import MCP_NAME, ROOT
from .page import PAGE_FILES
from .state import STATE_DIR, log, place, read_json, write_json

# A Claude Code pluginnak nincs install/update/uninstall eseménye. Ami a gépen
# túl van a pluginon (a stabil másolat és a Claude app MCP-configja), azt a
# SessionStart hook állítja be — idempotensen, csak változáskor írva —, a
# leszerelést pedig az app által indított `git-graph --mcp` végzi, amikor a plugin
# eltűnik a Claude Code nyilvántartásából.

PLUGIN_ID = "git-graph@"     # bármelyik marketplace-ből telepítve
INSTALLED_PLUGINS = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
# A plugin útvonala verziónként más (…/cache/<marketplace>/git-graph/<verzió>/),
# a régi verzió mappája el is tűnhet — az app ezt a másolatot futtatja.
BIN_DIR = STATE_DIR / "bin"
STABLE = BIN_DIR / "git-graph"
# A stabil másolat belépője: a zip gyökerén, a csomag mellett (`stable_bundle`).
STABLE_MAIN = "import sys\n\nfrom git_graph.cli import main\n\nsys.exit(main())\n"
# A verzió egyetlen forrása; a kód gyökerében (`ROOT`) keressük — a pluginban, a
# working tree-ben és a stabil másolat mellett (`install_copy`) is ott van.
MANIFEST = Path(".claude-plugin") / "plugin.json"
# Az Artifact `host:git-graph` hívásai csak az innen indított szervert érik el
# (a `claude mcp add`-os nem számít — mérve).
APP_CONFIG = (Path.home() / "Library" / "Application Support" / "Claude"
              / "claude_desktop_config.json")
# A rendszer Pythonja: az app minimális környezetében is megvan, és nem tűnik
# el egy homebrew-frissítéssel.
SYSTEM_PYTHON = "/usr/bin/python3"
PLUGIN_POLL_S = 60           # a nyilvántartás figyelése: leszerelés és frissítés
STABLE_POLL_S = 15           # a stabil hely figyelése: a --dev-install gyorsan éljen
UPDATED = threading.Event()  # a figyelőszál jelzi: a főszál két kérés között újraindul
UNINSTALL_MISSES = 2         # frissítés közben a nyilvántartás egy pillanatra hiányos lehet


def manifest_version(root: Path) -> str | None:
    """A `<root>` manifestjének verziója; None, ha nincs vagy olvashatatlan."""
    data = read_json(root / MANIFEST)
    version = data.get("version") if data else None
    return version if isinstance(version, str) else None


# Induláskor rögzítve: a futó `git-graph --mcp` ezt a kódot futtatja, akkor is,
# ha közben a hook már újabbat másolt a stabil helyre.
RUNNING_VERSION = manifest_version(ROOT)


def registry_plugins() -> dict | None:
    """A Claude Code plugin-nyilvántartása (`plugins`); None, ha nem dönthető el.

    Az `installed_plugins.json` a Claude Code belső fájlja — ismeretlen
    formátumnál inkább nem döntünk, mint hogy tévesen leszereljünk.
    """
    data = read_json(INSTALLED_PLUGINS)
    if not data or data.get("version") != 2 or not isinstance(data.get("plugins"), dict):
        return None
    return data["plugins"]


def installed_entry() -> dict | None:
    """A plugin bejegyzése a Claude Code nyilvántartásában; None, ha nem dönthető el."""
    for key, entries in (registry_plugins() or {}).items():
        if key.startswith(PLUGIN_ID) and isinstance(entries, list) and entries:
            return entries[0] if isinstance(entries[0], dict) else None
    return None


def installed_version() -> str | None:
    """A Claude Code nyilvántartása szerint telepített verzió; None, ha nem dönthető el."""
    version = (installed_entry() or {}).get("version")
    return version if isinstance(version, str) else None


def stable_version() -> str | None:
    """A stabil másolat mellé tett manifest verziója — amit egy újraindulás futtatna."""
    return manifest_version(STATE_DIR)


def stable_bundle(root: Path) -> bytes:
    """A stabil másolat: a `git_graph` csomag egyetlen futtatható zipben (`python3 <zip>`).

    Egy fájl, így atomi cserével (`place`) kerül a helyére: egy épp induló
    szerver sosem lát félig új csomagot. Tömörítés és időbélyeg nélkül — változatlan
    forrásból bájtra ugyanaz, a `place` így csak változáskor ír.
    """
    files = [("__main__.py", STABLE_MAIN.encode())]
    files += [(p.relative_to(root).as_posix(), p.read_bytes()) for p in sorted((root / "git_graph").rglob("*.py"))]
    buf = io.BytesIO()
    buf.write(b"#!/usr/bin/env python3\n")    # kézzel is futtatható; a zip a végéről olvas
    with zipfile.ZipFile(buf, "a") as zf:
        for name, data in files:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return buf.getvalue()


def install_copy(root: Path | None = None, manifest: bytes | None = None) -> None:
    """A csomag, a lap fájljai és a manifest másolata a stabil helyre — a futóé, vagy egy plugin-mappáé.

    Előbb a lap fájljai, aztán a csomag (`stable_bundle`), végül a manifest (a
    `manifest`, ha adott, különben a `root`-é); mind atomi cserével,
    folyamatonként saját ideiglenes fájlból (több `git-graph --mcp` is másolhat
    egyszerre). Az újraindulás a manifest verzióján múlik: mire az új verziót
    mondja, a kód és a lap is a helyén van — a stabil zip a verzióját ebből a
    manifestből olvassa, egy korábbi újraindulás tehát az új verziót hinné a
    régi kódról.
    """
    root = root or ROOT
    for name in PAGE_FILES:
        if (root / "page" / name).exists():
            place((root / "page" / name).read_bytes(), STATE_DIR / "page" / name, 0o644)
    if (root / "git_graph").is_dir():
        place(stable_bundle(root), STABLE, 0o755)
    if manifest is None and (root / MANIFEST).exists():
        manifest = (root / MANIFEST).read_bytes()
    if manifest is not None:
        place(manifest, STATE_DIR / MANIFEST, 0o644)


DEV_MARK = "+dev"   # SemVer build-metaadat: a working treeből telepített, fejlesztői példány
DEV_TTL = 12 * 3600  # ennyi ideig védett a fejlesztői példány a hook visszamásolásától


def dev_active() -> bool:
    """Friss `--dev-install` van a stabil helyen (`<verzió>+dev.<időbélyeg>`, DEV_TTL-en belül).

    Ilyenkor a hook nem másolja vissza a telepített plugint — különben egy
    másik session indulása egy percen belül
    visszaállítaná. A védelem lejár, így egy elfelejtett dev-példány nem
    ragad be a frissítések elé.
    """
    version = stable_version() or ""
    if DEV_MARK not in version:
        return False
    stamp = version.rsplit(".", 1)[-1]
    return stamp.isdigit() and time.time() - int(stamp) < DEV_TTL


def dev_install() -> int:
    """A working tree a stabil helyre, `+dev` verzióval — a lap élő kipróbálásához.

    A futó szerver a verzióváltáson 15 s-on belül újraindul erre a kódra,
    a lap pedig újratölt. A fejlesztői példány nem frissít vissza a
    telepített pluginra (`pull_update`), és DEV_TTL-ig a hook
    (`ensure_installed`) sem másolja vissza a telepítettet (`dev_active`) —
    ezt a védelmet csak a már ezzel a kóddal telepített plugin hookja tartja.
    """
    if ROOT.resolve() == STATE_DIR.resolve():
        log("git-graph: a --dev-install a working treeből futtatandó (python3 bin/git-graph)")
        return 1
    manifest = read_json(ROOT / MANIFEST) or {}
    version = f"{manifest.get('version', '0')}{DEV_MARK}.{int(time.time())}"
    manifest["version"] = version
    install_copy(ROOT, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode())
    print(f"✓ fejlesztői példány: {version} — a futó git-graph 15 s-on belül átvált, a lap újratölt")
    return 0


def pull_update() -> bool:
    """Igaz, ha a futó szerver alatt frissült a git-graph (újra kell indulnia).

    Ha a nyilvántartás más verziót mond, mint ami fut, a plugin mappájából maga
    másolja a stabil helyre — a `claude plugin update` után így sem
    app-újraindítás, sem új session nem kell. A hook ugyanígy cserélheti alatta.
    A fejlesztői példány (`--dev-install`) nem másol vissza, csak a stabil hely
    változására indul újra.
    """
    entry = installed_entry() or {}
    version, path = entry.get("version"), entry.get("installPath")
    dev = DEV_MARK in (RUNNING_VERSION or "")
    if (isinstance(version, str) and version != RUNNING_VERSION and isinstance(path, str)
            and not dev):
        root = Path(path)
        manifest = read_json(root / MANIFEST)
        complete = all((root / "page" / name).exists() for name in PAGE_FILES)
        if (manifest and manifest.get("version") == version and complete
                and (root / "git_graph" / "cli.py").exists()):
            install_copy(root)
    return stable_version() not in (None, RUNNING_VERSION)


def install_app_mcp() -> bool:
    """A git-graph MCP a Claude app configjában; True, ha most került be / változott."""
    if not APP_CONFIG.parent.is_dir():   # nincs Claude app ezen a gépen
        return False
    data = read_json(APP_CONFIG)
    if data is None:
        log(f"git-graph: {APP_CONFIG} nem érvényes JSON — kézzel kell javítani")
        return False
    servers = data.setdefault("mcpServers", {})
    entry = {"command": SYSTEM_PYTHON, "args": [str(STABLE), "--mcp"]}
    if servers.get(MCP_NAME) == entry:
        return False
    servers[MCP_NAME] = entry
    write_json(APP_CONFIG, data)
    return True


def ensure_installed() -> str | None:
    """Pluginból futva a gépi rész beállítása; a modellnek szóló üzenet, ha van.

    Csak a plugin hookjából fut (a kód a CLAUDE_PLUGIN_ROOT-ból): egy kézi
    `git-graph --session-hook` ne telepítsen.
    """
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not root or Path(root).resolve() != ROOT.resolve():
        return None
    if not dev_active():                 # a friss --dev-install-t nem írja felül
        install_copy()
    if sys.platform != "darwin":
        return None
    if not install_app_mcp():
        return None
    # Mérve: a futó app a beállítások mentésekor a memóriabeli configgal
    # felülírja a fájlt — az újraindításig a bejegyzés elveszhet.
    return ("A git-graph plugin most vette fel a git-graph MCP-t a Claude app configjába. "
            "Mondd meg a Fejlesztőnek egy mondatban: a Claude appot most újra kell indítani "
            "(Cmd+Q, majd indítás) — enélkül az Artifact nem kap élő adatot.")


def plugin_installed() -> bool | None:
    """Telepítve van-e a plugin; None, ha a nyilvántartásból nem dönthető el (`registry_plugins`)."""
    plugins = registry_plugins()
    return None if plugins is None else any(key.startswith(PLUGIN_ID) for key in plugins)


def uninstall() -> None:
    """Minden, amit az `ensure_installed` a gépre tett."""
    data = read_json(APP_CONFIG) if APP_CONFIG.exists() else None
    servers = (data or {}).get("mcpServers")
    if isinstance(servers, dict) and MCP_NAME in servers:
        servers.pop(MCP_NAME)
        if not servers:
            data.pop("mcpServers")
        write_json(APP_CONFIG, data)
    shutil.rmtree(STATE_DIR, ignore_errors=True)


def watch_plugin() -> None:
    """A `git-graph --mcp` szála: leszerelés, ha a plugint eltávolították; frissítés, ha újult.

    Az app minden indításkor elindítja a `git-graph --mcp`-t, és a folyamat az app
    futásáig él — így a leszerelés legkésőbb a következő app-indítás után
    megtörténik. Frissüléskor (`pull_update`) jelez a főszálnak, az két kérés
    között újraindul (`restart`). Csak a plugin telepítette példányban (a
    stabil másolat) fut. Több példány is futhat (az app és minden Code-session
    indít egyet): a leszerelés és a másolás idempotens.
    """
    if Path(sys.argv[0]).resolve() != STABLE.resolve():
        return
    misses, due = 0, 0.0
    while True:
        if time.monotonic() >= due:
            due = time.monotonic() + PLUGIN_POLL_S
            installed = plugin_installed()
            misses = misses + 1 if installed is False else 0
            if misses >= UNINSTALL_MISSES:
                log("A git-graph plugin nincs telepítve — leszerelés.")
                uninstall()
                return
            if installed and pull_update():
                UPDATED.set()
                return
        # Közben csak a stabil manifestet nézi (olcsó): egy `--dev-install` így
        # negyedperc alatt él. A manifest íródik utolsóként, a csomag már teljes.
        elif stable_version() not in (None, RUNNING_VERSION):
            UPDATED.set()
            return
        time.sleep(min(STABLE_POLL_S, PLUGIN_POLL_S))

