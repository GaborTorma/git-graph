"""Publikálás: a betöltő kiírása, a session teendői, és a publikált lap nyilvántartása."""
from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path

from . import gitio
from .gitio import config_get, remember_artifact, repo_name
from .page import build
from .registry import register, slug_for
from .state import STATE_DIR, place, read_json

SETTINGS = STATE_DIR / "settings.json"   # a gép beállításai (a lap fogaskerék-menüje írja)


def page_title(name: str) -> str:
    """A lap és az Artifact neve. „Git Graph” elöl, a repó zárójelben — repónként
    egy Artifact van, a worktree-k közösen látják."""
    return f"Git Graph ({name})"


def artifact_path(repo: Path) -> Path:
    """Az Artifact vékony lapja: `~/.git-graph/<slug>/artifact.html` — innen publikál a session."""
    return STATE_DIR / slug_for(repo) / "artifact.html"


# A lap runtime-contractja (a `window.claude` API verziója): minden repó lapja
# ezzel publikálódik, rögzítve. Újabb contractra csak egyeztetés után váltunk
# (.claude/memory/artifact-contract.md); a váltás minden lapot újrapublikáltat.
PUBLISH_CONTRACT = "0.2.96"

# A lap ezen át éri el a gépen futó git-graph --mcp-t (enélkül use("mcp") null).
PUBLISH_CAPS = {"mcp": {"servers": [{"server": "host:git-graph",
                                     "tools": ["changes", "graph_data", "file_diff",
                                               "file_tree", "write_file", "page_code",
                                               "settings"]}]}}


def page_digest(html_page: str) -> str:
    """A publikált lap hashe (`git-graph.artifactHash`) — a capability-lista és a contract is része:
    a három egy publish-hívásban megy fel, és ha bármelyik változik, újra kell."""
    return hashlib.sha256((html_page + json.dumps(PUBLISH_CAPS) + PUBLISH_CONTRACT).encode()).hexdigest()


def prepare_publish() -> dict | None:
    """Az Artifact vékony lapja: kiírja, ha eltér a legutóbb publikálttól.

    Adat nincs benne — a lap a Claude appban a gép `git-graph --mcp`-jéből kéri —,
    így csak sablon- (kód-) vagy repónév-változáskor kell újra feltölteni.
    None, ha van már Artifact, és a hashe (lap, capability-lista, contract) egyezik.
    """
    html_page = build(page_title(repo_name()), register(gitio.REPO))
    url = config_get("artifact")
    if url and page_digest(html_page) == config_get("artifactHash"):
        return None
    page = artifact_path(gitio.REPO)
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html_page, encoding="utf-8")
    return {"page": page, "url": url, "title": page_title(repo_name())}


def publish_steps(job: dict) -> str:
    """A session teendője a lap kézi publikálásához — a `git-graph --publish` és az `--open-url` adja
    a modellnek (az automatikusat a mod végzi: `mod_plan`).

    Az Artifact API-t csak a modell éri el, ezért a publikálást a session
    végzi (mérve, .claude/memory/publish-from-session.md), a beépített `Artifact`
    eszközzel. A lap a `~/.git-graph`-ból megy fel (a telepítés a session mappái
    közé veszi: `install_read_dir`), a capability-lista ugyanabban a hívásban,
    teljes halmazként, a rögzített contracttal (`PUBLISH_CONTRACT`) — így a
    deklaráció nem csúszhat el a nyilvántartott hashtől.
    Meglévő lapra a publish csak egy `read` után megy. Az URL-t és a hasht a
    `--published` írja vissza — a Python a publikálás eredményét nem látja. A
    `git-graph` a plugin `bin/`-jéből a Bash eszköz PATH-ján van (egy
    `Bash(git-graph:*)` engedéllyel nem kérdez).
    """
    publish = (f'Artifact, action: "publish", file_path: {json.dumps(str(job["page"]))}, '
               f"capabilities: {json.dumps(PUBLISH_CAPS)}, contract: {json.dumps(PUBLISH_CONTRACT)}")
    record = (f"Bash: git-graph {shlex.quote(str(gitio.REPO))} --published <URL> "
              "(az URL a publish eredményéből)")
    # A publikálás magától nem nyitja meg a panelt (mérve: csak a kártya jelent
    # meg) — a hook pedig ebben a sessionben már nem kéri (`shown_in_session`).
    show = 'mcp__ccd_view__show_pane, pane: "artifact"'
    # Az újabb contractra váltás egyeztetés után, a kódban (`PUBLISH_CONTRACT`).
    newer = (" Ha a publish eredménye újabb contractot jelez („newest …”), egy mondatban jelezd "
             "a Fejlesztőnek; a contract értékét ne változtasd.")
    if job["url"]:
        return (f'1) Artifact, action: "read", url: {job["url"]}; '
                f"2) {publish}, url: {job['url']}; 3) {record}; 4) {show}.{newer}")
    return (f'1) {publish}, title: {json.dumps(job["title"])}, icon: "branch"; '
            f"2) {record}; 3) {show}.{newer}")


def auto_open() -> bool:
    """A repó Artifactja a session indulásakor magától megnyílik, és ha elavult,
    frissül (`git-graph.autoOpen`, alap: igen)."""
    return config_get("autoOpen") != "false"


def auto_publish() -> bool:
    """Artifact nélküli repóban a session publikáltasson-e (a gépen, minden repóra; alap: igen)."""
    return (read_json(SETTINGS) or {}).get("autoPublish") is not False


def collapse_merges() -> bool:
    """A beolvasztott commitok a merge alá csukódnak a lapon (`git-graph.collapseMerges`, alap: igen)."""
    return config_get("collapseMerges") != "false"


def settings(changes: dict) -> dict:
    """A lap beállítás-menüje (`settings` tool): a megadott kulcsokat írja, és mindet adja."""
    for key in ("autoOpen", "collapseMerges"):      # a repóé: a `.git/config`-ban
        if isinstance(changes.get(key), bool):
            gitio.git("config", "--local", f"git-graph.{key}", str(changes[key]).lower())
    if isinstance(changes.get("autoPublish"), bool):
        data = read_json(SETTINGS) or {}
        data["autoPublish"] = changes["autoPublish"]
        place((json.dumps(data, indent=2) + "\n").encode(), SETTINGS, 0o644)
    return {"autoOpen": auto_open(), "autoPublish": auto_publish(), "collapseMerges": collapse_merges()}


def config_unset(key: str) -> None:
    if config_get(key):
        gitio.git("config", "--local", "--unset", f"git-graph.{key}")


def mark_published(url: str) -> None:
    """A publikálás után: az URL és a feltöltött lap hashe (a deklarált capability-listával
    és contracttal) a `.git/config`-ba. Az új
    Artifact (a `--forget` után is) bekapcsolt automatikus megnyitással indul; a
    meglévő frissítése a beállítást nem érinti.
    """
    page = artifact_path(gitio.REPO)
    if not page.exists():
        raise SystemExit("HIBA: nincs kiírt Artifact-lap — előbb: git-graph --publish")
    fresh = not config_get("artifact")
    remember_artifact(url, page_digest(page.read_text(encoding="utf-8")))
    if fresh:
        config_unset("autoOpen")
    register(gitio.REPO)

