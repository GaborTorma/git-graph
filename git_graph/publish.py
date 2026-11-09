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


# A lap ezen át éri el a gépen futó git-graph --mcp-t (enélkül use("mcp") null).
PUBLISH_CAPS = {"mcp": {"servers": [{"server": "host:git-graph",
                                     "tools": ["changes", "graph_data", "file_diff",
                                               "file_tree", "write_file", "page_code",
                                               "settings"]}]}}


def caps_digest() -> str:
    """A capability-deklaráció hashe: a `git-graph.artifactCaps` ezt őrzi a legutóbbi
    deklarálásról. Amíg egyezik, a lap frissítéséhez nem kell modell (`mod_plan`)."""
    return hashlib.sha256(json.dumps(PUBLISH_CAPS, sort_keys=True).encode()).hexdigest()


def caps_current() -> bool:
    """Igaz, ha a repó Artifactján a mostani capability-lista van deklarálva.

    A nyilvántartás előtti Artifactnál (nincs `artifactCaps`) a lap hashe dönt: a
    capability is része, így egyezésnél a mostanival publikálták.
    """
    if not config_get("artifact"):
        return False
    declared = config_get("artifactCaps")
    if declared:
        return declared == caps_digest()
    html_page = build(page_title(repo_name()), register(gitio.REPO))
    return page_digest(html_page) == config_get("artifactHash")


def page_digest(html_page: str) -> str:
    """A publikált lap hashe — a capability-deklaráció is része: ha változik, újra kell."""
    return hashlib.sha256((html_page + json.dumps(PUBLISH_CAPS)).encode()).hexdigest()


def prepare_publish(force: bool = False) -> dict | None:
    """Az Artifact vékony lapja: kiírja, ha eltér a legutóbb publikálttól.

    Adat nincs benne — a lap a Claude appban a gép `git-graph --mcp`-jéből kéri —,
    így csak sablon- (kód-) vagy repónév-változáskor kell újra feltölteni.
    None, ha van már Artifact, a lap hashe egyezik, és a deklarált capability a
    mostani (egy elbukott deklarálás után nem az) — kivéve `force`-szal (a mod a
    megnyitáshoz újraküldi: `mod_plan`).
    """
    html_page = build(page_title(repo_name()), register(gitio.REPO))
    url = config_get("artifact")
    declared = config_get("artifactCaps")      # üres: a nyilvántartás előtti lap, a hash dönt
    if (not force and url and page_digest(html_page) == config_get("artifactHash")
            and declared in ("", caps_digest())):
        return None
    page = artifact_path(gitio.REPO)
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html_page, encoding="utf-8")
    return {"page": page, "url": url, "title": page_title(repo_name())}


def publish_steps(job: dict) -> str:
    """A session teendője a lap publikálásához — a hook és a `git-graph --publish` adja a modellnek.

    Az Artifact API-t csak a modell éri el, ezért a publikálást a session
    végzi (mérve, .claude/memory/publish-from-session.md), a beépített `Artifact`
    eszközzel. A lap a `~/.git-graph`-ból megy fel (a telepítés a session mappái
    közé veszi: `install_read_dir`), a capability-lista ugyanabban a hívásban,
    teljes halmazként — így a deklaráció nem csúszhat el a nyilvántartott hashtől.
    Meglévő lapra a publish csak egy `read` után megy. Az URL-t és a hasht a
    `--published` írja vissza — a hook a publikálás eredményét nem látja. A
    `git-graph` a plugin `bin/`-jéből a Bash eszköz PATH-ján van (egy
    `Bash(git-graph:*)` engedéllyel nem kérdez).
    """
    publish = (f'Artifact, action: "publish", file_path: {json.dumps(str(job["page"]))}, '
               f"capabilities: {json.dumps(PUBLISH_CAPS)}")
    record = (f"Bash: git-graph {shlex.quote(str(gitio.REPO))} --published <URL> "
              "(az URL a publish eredményéből)")
    # A publikálás magától nem nyitja meg a panelt (mérve: csak a kártya jelent
    # meg) — a hook pedig ebben a sessionben már nem kéri (`shown_in_session`).
    show = 'mcp__ccd_view__show_pane, pane: "artifact"'
    if job["url"]:
        return (f'1) Artifact, action: "read", url: {job["url"]}; '
                f"2) {publish}, url: {job['url']}; 3) {record}; 4) {show}.")
    return (f'1) {publish}, title: {json.dumps(job["title"])}, icon: "branch"; '
            f"2) {record}; 3) {show}.")


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


def mark_published(url: str, declared: bool = True) -> None:
    """A publikálás után: az URL és a feltöltött lap hashe a `.git/config`-ba.

    A session publikálása a capability-t is deklarálja (`declared`): annak hashe
    is bekerül (`artifactCaps`). A mod újraküldése (`--republished`) nem
    deklarál, a capability öröklődik — a hashe marad. Az új Artifact (a
    `--forget` után is) bekapcsolt automatikus megnyitással indul; a meglévő
    frissítése a beállítást nem érinti.
    """
    page = artifact_path(gitio.REPO)
    if not page.exists():
        raise SystemExit("HIBA: nincs kiírt Artifact-lap — előbb: git-graph --publish")
    fresh = not config_get("artifact")
    remember_artifact(url, page_digest(page.read_text(encoding="utf-8")))
    if declared:
        gitio.git("config", "--local", "git-graph.artifactCaps", caps_digest())
    if fresh:
        config_unset("autoOpen")
    register(gitio.REPO)

