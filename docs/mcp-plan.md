# Terv: élő, magától frissülő git-gráf

Ez a terv **blokkolva van** — de nem elavult. Ha a blokkoló feloldódik, innen
folytatható. A blokkoló méréseit lásd: [artifact-findings.md](artifact-findings.md).

## A cél

Ma: a `gg` HTML-t generál, a `/git-graph` publikálja. Az Artifact **pillanatkép**
— új commit után kézzel kell frissíteni.

Cél: az Artifact-ablakban **magától frissülő** gráf. Ehhez a lapnak élő adathoz
kell jutnia, amit egyedül az `mcp` capability tud megadni.

## A blokkoló

A `host:<név>` (helyi MCP szerver) deklarációt a deploy elutasítja:
`422 capabilities.mcp: unavailable`. Ez volt az eredeti, legkényelmesebb terv —
egyelőre nem járható.

**Újratesztelés**: a [`../probe/`](../probe/) mappa pontosan erre való, egy
publikálásból megmondja, változott-e.

## Két járható irány (ha a host: nem nyílik ki)

### A) GitHub konnektor — olcsó, de csak a remote-ot látja

claude.ai → Settings → Connectors → GitHub. Utána a lap `watchTool`-lal
pollozza. **Korlát**: csak a felpusholt állapot látszik; a lokális, pusholatlan
commitok nem. Aki sokat dolgozik push nélkül, annak félrevezető.

### B) Saját MCP szerver tunnellel, egyéni konnektorként — a lokális repót látja

A claude.ai konnektorok távoli, HTTP-n elérhető MCP szerverek. A helyi szervert
HTTP transporton futtatva + tunnellel (Cloudflare Tunnel / ngrok / Tailscale
Funnel) kitéve felvehető **egyéni konnektorként**, és onnantól a lap a
**tényleges lokális** állapotot látja.

**Ez egy repó-olvasó szolgáltatást tesz az internetre.** Kötelező:

- **bearer token auth** — a tunnel-URL önmagában nem védelem
- **engedélyezett repó-gyökerek whitelistje**, `Path.resolve()` + `is_relative_to`
  ellenőrzéssel (különben tetszőleges útvonal olvasható)
- kizárólag olvasó git-hívások
- a tunnelnek futnia kell; ha nem fut, a lap essen vissza a beágyazott
  pillanatképre

## Az MCP szerver terve

| Tool | Bemenet | Kimenet | Mire |
| --- | --- | --- | --- |
| `graph_fingerprint` | `repo` | `{repo, head, headSha, totalCommits, refsDigest, dirty}` | olcsó polling |
| `graph_data` | `repo`, `limit?` | a teljes 5-kulcsos payload | csak fingerprint-változásra |
| `list_repos` | — | az engedélyezett repók | repóválasztó |

A `refsDigest` a `git for-each-ref --format='%(objectname) %(refname)'` kimenetének
hash-e — így ág/tag mozgásra is változik, nem csak új commitra.

**Miért két tool**: a payload 122 commitnál **~140 KB**. Ezt 30 másodpercenként
átküldeni értelmetlen. A `watchTool` a pár száz bájtos fingerprintet figyeli, és
a handler csak változáskor kér `graph_data`-t.

## Az adatszerződés

A `gitgraph` ma ezt ágyazza be `const DATA = …`-ként. Az MCP szervernek
**ugyanezt** kell adnia, hogy a renderelő kód változatlan maradhasson:

```jsonc
{
  "commits": [{
    "sha": "b80f823c9593a6e64a2ec314c4b6c5cd724bb3ed",
    "short": "b80f823",
    "parents": ["d07d6608ce24d9fc0ad69abb2d6a747c65efd1b7"],
    "author": "Gábor Torma",
    "date": "2026-08-25T17:31:25+02:00",        // %aI
    "refs": [{"kind": "head", "name": "main"}],  // head|branch|remote|tag|detached
    "subject": "refactor(tooling): …",
    "body": "…",
    "lane": 0                                    // az assign_lanes tölti
  }],
  "edges":  [{"fromRow": 0, "fromLane": 0, "toRow": 1, "toLane": 0, "merge": false}],
  "stats":  { "<sha>": {"add": 3, "del": 3,
              "files": [{"path": "watchapp/CLAUDE.md", "add": 3, "del": 3, "bin": false}]} },
  "branches": [{"name": "main", "sha": "b80f823", "upstream": "origin/main",
                "track": "ahead 11", "date": "2026-08-25", "current": true}],
  "meta": { "repo": "WristBPM", "head": "main", "totalCommits": 122, "shown": 122,
            "dirty": 0, "generated": "…", "worktrees": ["…"] }
}
```

Az adatgyűjtő függvények készen vannak a [`../gitgraph`](../gitgraph) scriptben:
`collect_commits`, `parse_refs`, `collect_stats`, `assign_lanes`,
`collect_branches`, `repo_name`, `collect_meta`, `resolve_repo`.

> **Döntés kell**: a script `.py` kiterjesztés nélkül nem importálható. Vagy
> kiemeled ezeket rendes csomagba (és a `gitgraph` onnan függ), vagy másolod.
> Ne duplikáld csendben — döntsd el és írd le.

## Az oldal átalakítása

1. **Fallback-first**: a beágyazott `DATA` maradjon, és abból rendereljen
   azonnal. Ez a normál működés — az élő frissítés a ráépülő extra. MCP nélkül
   (`claude.use("mcp") === null`, böngészőfül, nem futó tunnel) az oldal
   ugyanúgy használható.
2. `claude.use("mcp")` sikere után `watchTool` a fingerprintre.
3. Változásnál `callTool("graph_data")` → a `DATA` cseréje → `render()`. A
   `render()` már ma is teljes újrarajzolás — ellenőrizni kell, hogy a nyitott
   commit-panel (`expanded`) és a szűrők túlélik-e.
4. Státusz a fejlécben: élő / statikus / hiba, frissesség a
   `result.cache.storedAt`-ből (**ne** `Date.now()`-ból).

## Kötelező a publikálás előtt

A capabilities-doksi kikötése: **nem publikálható olyan oldal, ami MCP-toolt hív
anélkül, hogy megfigyeltél volna rá egy valódi kérés-válasz párt.** Előbb
szerver, bekötés, valódi hívás — utána oldal.

## Lépések

1. Újratesztelés: `probe/` publikálása — kinyílt-e a `host:`?
2. Ha nem: döntés A) vagy B) között (lásd fent, B) biztonsági ára valós)
3. MCP szerver — az `anthropic-skills:mcp-builder` skill a váznak
4. Adatgyűjtés bekötése (lásd a fenti döntést a csomagról)
5. Bekötés + **valódi kérés-válasz megfigyelése** mindkét toolra
6. Az oldal átírása, fallback-first
7. Publikálás `capabilities` + `contract` megadásával

## Konvenciók

Python (stdlib-közeli), `uv`, `commitizen` + `pyproject.toml` `[project] version`,
Conventional Commits magyar body-val, kód-kommentek magyarul, `.env` minden
env-specifikus beállításnak (**a tokennek is**), `.env.example` commitolva.
