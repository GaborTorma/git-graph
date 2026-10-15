"""A lap: a publikált betöltő és a `page_code`-dal adott élő kód, fájltípus-ikonok."""
from __future__ import annotations

import functools
import html
import json
import re
from pathlib import Path

from . import MCP_NAME, ROOT
from .gitio import numstat_new_path, repo_name

# Az Artifactként publikált lap csak egy betöltő (`page/loader.html`): a rajzoló
# kódot (`page/head.html`, `page.css`, `body.html` és a `page/js/` ES-moduljai) a
# `page_code` toollal a gépen futó `git-graph --mcp`-ből kéri, és `import(blob:)`-bal
# futtatja (az Artifact CSP-je engedi — mérve, docs/artifact-findings.md). Így
# egy kódfrissítés az app újraindításával él, újrapublikálás nélkül: a betöltő
# csak a saját változásakor, repónév- vagy capability-változáskor publikálandó.

LOADER_API = 1   # a betöltő és a `page_code` szerződése — csak a betöltővel együtt lép

# A lap fájljai a kód mellett: a pluginban, a working tree-ben és a stabil
# másolatnál (`install_copy`) is `<gyökér>/page/`.
PAGE_DIR = ROOT / "page"
PAGE_FILES = ("loader.html", "head.html", "page.css", "body.html", "file-icons.json",
              "vendor/mermaid.min.js")
PAGE_ENTRY = "js/main.js"   # a lap belépő modulja; a többit ez húzza be
# A Mermaid (11.17.2, MIT, `vendor/mermaid.LICENSE`) egyfájlos buildje: a lap lustán,
# csak diagramos markdown-diffnél kéri (`page_code` `part: "mermaid"`), blobból futtatja.
PAGE_PARTS = {"mermaid": "vendor/mermaid.min.js"}
_PAGE: dict[str, str] = {}


def page_files(root: Path = ROOT) -> list[str]:
    """A lap fájljai a `root/page` alatt: az állandók és a JS-modulok (`js/*.js`)."""
    return [*PAGE_FILES, *sorted(f"js/{p.name}" for p in (root / "page" / "js").glob("*.js"))]
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


# Egy modul importja: `import … from './x.js'` vagy `import './x.js'` a sor elején. A
# blob-URL-hez relatív út nem oldható fel, ezért a lapon a már betöltött modul URL-je
# kerül a helyére (`PAGE_BOOT`); más alakú relatív import nem köthető össze.
IMPORT_RE = re.compile(r"^import\s+(?:[\w$*{},\s]+?\s+from\s+)?('\./([\w-]+\.js)')", re.M)
RELATIVE_RE = re.compile(r"""['"]\./[\w-]+\.js['"]""")
PAGE_BOOT = r"""// A lap ES-moduljai blob-URL-en, a függőségeik sorrendjében: egy modul importjai a már
// betöltöttek URL-jére mutatnak. A `sourceURL` a fejlesztői eszközökben és a hibák
// helyén a modul nevét adja.
const MODULES = __MODULES__;
const url = {};
for (const [name, parts, deps] of MODULES) {
  const code = parts.reduce((out, part, i) => out + JSON.stringify(url[deps[i - 1]]) + part);
  url[name] = URL.createObjectURL(new Blob([`${code}\n//# sourceURL=git-graph/${name}`], { type: 'text/javascript' }));
}
await import(url[MODULES.at(-1)[0]]);
"""


def page_modules() -> list[tuple[str, list[str], list[str]]]:
    """A belépőből elérhető modulok, előbb amit importálnak: (név, szakaszok, függőségek).

    A szakaszok a forrás az import-utak mentén vágva: a lap a függőség URL-jét teszi
    közéjük. Körkörös import nem lehet (a modul URL-je csak a függőségei után áll elő),
    és amit a belépő nem ér el, az nem kerül a lapra (pl. egy törölt modul régi másolata).
    """
    order: list[tuple[str, list[str], list[str]]] = []
    done: dict[str, bool] = {}            # név → kész-e (False: a bejárás még benne jár)

    def visit(name: str, path: list[str]) -> None:
        if done.get(name):
            return
        if name in done:
            raise ValueError("körkörös import a lapon: " + " → ".join([*path, name]))
        done[name] = False
        src = page_file(f"js/{name}")
        parts, deps, last = [], [], 0
        for m in IMPORT_RE.finditer(src):
            parts.append(src[last:m.start(1)])
            deps.append(m.group(2))
            last = m.end(1)
        parts.append(src[last:])
        if any(RELATIVE_RE.search(p) for p in parts):
            raise ValueError(f"js/{name}: relatív út csak a sor eleji `import … './x.js'`-ben lehet")
        for dep in deps:
            visit(dep, [*path, name])
        done[name] = True
        order.append((name, parts, deps))

    visit(PAGE_ENTRY.split("/")[-1], [])
    return order


def page_code(part: str | None = None) -> dict:
    """A lap élő kódja a betöltőnek (`page_code` tool): head-elemek, body, JS-modul.

    A `part` egy lustán kért darab (`PAGE_PARTS`): akkor csak annak a JS-e.
    """
    if part is not None:
        if part not in PAGE_PARTS:
            raise ValueError(f"ismeretlen part: {part}")
        return {"js": page_file(PAGE_PARTS[part])}
    return {"head": page_file("head.html") + "<style>\n" + page_file("page.css") + "</style>\n",
            "body": page_file("body.html"),
            "js": PAGE_BOOT.replace("__MODULES__", json.dumps(page_modules(), ensure_ascii=False))}


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

