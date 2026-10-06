"""A lap: a publikált betöltő és a `page_code`-dal adott élő kód, fájltípus-ikonok."""
from __future__ import annotations

import functools
import html
import json

from . import MCP_NAME, ROOT
from .gitio import numstat_new_path, repo_name

# Az Artifactként publikált lap csak egy betöltő (`page/loader.html`): a rajzoló
# kódot (`page/head.html`, `page.css`, `body.html`, `page.js`) a `page_code`
# toollal a gépen futó `git-graph --mcp`-ből kéri, és `import(blob:)`-bal
# futtatja (az Artifact CSP-je engedi — mérve, docs/artifact-findings.md). Így
# egy kódfrissítés az app újraindításával él, újrapublikálás nélkül: a betöltő
# csak a saját változásakor, repónév- vagy capability-változáskor publikálandó.

LOADER_API = 1   # a betöltő és a `page_code` szerződése — csak a betöltővel együtt lép

# A lap fájljai a kód mellett: a pluginban, a working tree-ben és a stabil
# másolatnál (`install_copy`) is `<gyökér>/page/`.
PAGE_DIR = ROOT / "page"
PAGE_FILES = ("loader.html", "head.html", "page.css", "body.html", "page.js", "file-icons.json")
_PAGE: dict[str, str] = {}
_FILE_ICONS: dict | None = None


def page_file(name: str) -> str:
    """A lap egy fájlja — folyamatonként egyszer olvasva.

    A futó `git-graph --mcp` így a saját verziójához tartozó kódot adja akkor
    is, ha a hook közben már újabbat másolt a stabil helyre (`mcp_serve` az
    induláskor mindet beolvassa).
    """
    if name not in _PAGE:
        _PAGE[name] = (PAGE_DIR / name).read_text(encoding="utf-8")
    return _PAGE[name]


def file_icons() -> dict:
    """A fájltípus-ikonok készlete (`page/file-icons.json`, scripts/file-icons.py).

    Ha hiányzik vagy hibás, üres: a lap az általános fájlikont mutatja.
    """
    global _FILE_ICONS
    if _FILE_ICONS is None:
        try:
            _FILE_ICONS = json.loads(page_file("file-icons.json"))
        except (OSError, ValueError):
            _FILE_ICONS = {}
    return _FILE_ICONS


@functools.cache   # a készlet statikus; minden graph_data az egész történetet bejárja
def file_icon(path: str) -> str | None:
    """Az út ikonjának neve: előbb a teljes fájlnév, aztán a leghosszabb kiterjesztés."""
    icons = file_icons()
    if not icons:
        return None
    name = numstat_new_path(path).rsplit("/", 1)[-1].lower()
    icon = icons["names"].get(name)
    parts = name.split(".")
    for i in range(1, len(parts)):
        if icon:
            break
        icon = icons["exts"].get(".".join(parts[i:]))
    return icon if icon in icons["icons"] else "_file"


def attach_icons(stats: dict[str, dict]) -> dict[str, str]:
    """A fájlokhoz az ikon neve (`icon`); vissza a használt ikonok SVG-je."""
    used: dict[str, str] = {}
    svgs = file_icons().get("icons", {})
    for st in stats.values():
        for f in st["files"]:
            icon = file_icon(f["path"])
            if icon:
                f["icon"] = icon
                used[icon] = svgs[icon]
    return used


def page_api_mismatch(api: object) -> str | None:
    """Ha a lap betöltője más szerződést vár, mint amit ez a git-graph ad: a teendő."""
    if api == LOADER_API:
        return None
    todo = ("írj egy üzenetet a repó Claude sessionjébe, az újrapublikálja a lapot"
            if isinstance(api, int) and api < LOADER_API else "indítsd újra a Claude appot")
    return (f"a lap betöltője (api {api}) és a gépen futó git-graph (api {LOADER_API}) "
            f"nem illik össze — {todo}")


def page_code() -> dict:
    """A lap élő kódja a betöltőnek (`page_code` tool): head-elemek, body, JS-modul."""
    return {"head": page_file("head.html") + "<style>\n" + page_file("page.css") + "</style>\n",
            "body": page_file("body.html"), "js": page_file("page.js")}


def embed(payload: dict) -> str:
    r"""A `<script>`-be ágyazható JSON.

    Egy commit-üzenetben előfordulhat `</script>` (láttuk: „JSON-LD
    </script>-escape") — az a script blokkot korán lezárja, és a maradék JSON
    szövegként ömlik a lapra. A `<\/` JSON-szinten ugyanaz a karakterlánc, a
    HTML-parszer viszont nem látja benne a záró taget. A sorelválasztók (U+2028,
    U+2029) ugyanezt a kárt tudják okozni régebbi JS-motorokon.
    """
    raw = json.dumps(payload, ensure_ascii=False)
    return (raw.replace("</", "<\\/")
               .replace("\u2028", "\\u2028")
               .replace("\u2029", "\\u2029"))


def build(title: str, slug: str) -> str:
    """Az Artifact lapja: a betöltő — sem adat, sem rajzoló kód nincs benne."""
    ctx = {"slug": slug, "repo": repo_name(), "server": f"host:{MCP_NAME}", "api": LOADER_API}
    return page_file("loader.html").replace("__CTX__", embed(ctx)).replace("__TITLE__", html.escape(title))

