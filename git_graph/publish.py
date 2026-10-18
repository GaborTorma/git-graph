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
                                               "page_code", "settings"]}]}}


def page_digest(html_page: str) -> str:
    """A publikált lap hashe — a capability-deklaráció is része: ha változik, újra kell."""
    return hashlib.sha256((html_page + json.dumps(PUBLISH_CAPS)).encode()).hexdigest()


def is_current() -> bool:
    """Igaz, ha van Artifact, és a lapja egyezik a legutóbb publikálttal (nem ír semmit)."""
    html_page = build(page_title(repo_name()), register(gitio.REPO))
    return bool(config_get("artifact")) and page_digest(html_page) == config_get("artifactHash")


def prepare_publish() -> dict | None:
    """Az Artifact vékony lapja: kiírja, ha eltér a legutóbb publikálttól.

    Adat nincs benne — a lap a Claude appban a gép `git-graph --mcp`-jéből kéri —,
    így csak sablon- (kód-) vagy repónév-változáskor kell újra feltölteni.
    None, ha van már Artifact, és a lap hashe egyezik.
    """
    html_page = build(page_title(repo_name()), register(gitio.REPO))
    url = config_get("artifact")
    if url and page_digest(html_page) == config_get("artifactHash"):
        return None
    page = artifact_path(gitio.REPO)
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_text(html_page, encoding="utf-8")
    return {"page": page, "url": url}


def publish_steps(job: dict) -> str:
    """A session teendője a lap publikálásához — a hook és a `git-graph --publish` adja a modellnek.

    Az Artifact API-t csak a modell éri el, ezért a publikálást a session
    végzi (mérve, .claude/memory/publish-from-session.md): a `host:git-graph` akkor is
    deklarálható, ha a session nem látja a szervert; egy meglévő Artifactra
    viszont csak az élő verzió olvasása után publikálhat. Az URL-t és a hasht
    a `--published` írja vissza — a hook a publikálás eredményét nem látja.
    A `git-graph` a plugin `bin/`-jéből a Bash eszköz PATH-ján van (egy
    `Bash(git-graph:*)` engedéllyel nem kérdez).
    """
    caps = json.dumps(PUBLISH_CAPS)
    record = (f"Bash: git-graph {shlex.quote(str(gitio.REPO))} --published <URL> "
              "(az URL a publish eredményéből)")
    # A publikálás magától nem nyitja meg a lapot (mérve: csak a kártya jelent
    # meg) — a hook pedig ebben a sessionben már nem kéri (`shown_in_session`).
    show = "Artifact, action: \"open\", url: <URL>"
    if job["url"]:
        return (f"1) Artifact, action: \"read\", url: {job['url']}; 2) Artifact publish — url: "
                f"{job['url']}, file_path: {job['page']}, capabilities: {caps}; 3) {record}; "
                f"4) {show}.")
    return (f"1) Artifact publish — file_path: {job['page']}, icon: \"branch\", "
            f"capabilities: {caps}; 2) {record}; 3) {show}.")


def auto_open() -> bool:
    """A repó Artifactja a session indulásakor magától megnyílik, és ha elavult,
    frissül (`git-graph.autoOpen`, alap: igen)."""
    return config_get("autoOpen") != "false"


def auto_publish() -> bool:
    """Artifact nélküli repóban a session publikáltasson-e (a gépen, minden repóra; alap: igen)."""
    return (read_json(SETTINGS) or {}).get("autoPublish") is not False


def settings(changes: dict) -> dict:
    """A lap beállítás-menüje (`settings` tool): a megadott kulcsokat írja, és mindkettőt adja."""
    if isinstance(changes.get("autoOpen"), bool):
        gitio.git("config", "--local", "git-graph.autoOpen", str(changes["autoOpen"]).lower())
    if isinstance(changes.get("autoPublish"), bool):
        data = read_json(SETTINGS) or {}
        data["autoPublish"] = changes["autoPublish"]
        place((json.dumps(data, indent=2) + "\n").encode(), SETTINGS, 0o644)
    return {"autoOpen": auto_open(), "autoPublish": auto_publish()}


def config_unset(key: str) -> None:
    if config_get(key):
        gitio.git("config", "--local", "--unset", f"git-graph.{key}")


def mark_published(url: str) -> None:
    """A session publikálása után: az URL és a feltöltött lap hashe a `.git/config`-ba.

    Az új Artifact (a `--forget` után is) bekapcsolt automatikus megnyitással
    indul; a meglévő frissítése a beállítást nem érinti.
    """
    page = artifact_path(gitio.REPO)
    if not page.exists():
        raise SystemExit("HIBA: nincs kiírt Artifact-lap — előbb: git-graph --publish")
    fresh = not config_get("artifact")
    remember_artifact(url, page_digest(page.read_text(encoding="utf-8")))
    if fresh:
        config_unset("autoOpen")
    register(gitio.REPO)

