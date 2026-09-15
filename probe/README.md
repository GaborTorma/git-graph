# probe — a `host:` blokkoló újratesztelése

Eldobható mérőeszköz. Egyetlen kérdést dönt el:

> Elér-e egy publikált Artifact oldal `host:<név>` hivatkozással egy MCP
> szervert a saját gépeden?

**2026-08-25-i állás: nem** — a deploy `422 capabilities.mcp: unavailable`-lel
elutasítja. Részletek és kontroll-mérések:
[../docs/artifact-findings.md](../docs/artifact-findings.md).

Ez a mappa azért maradt meg, hogy a kérdés **egy publikálásból** újramérhető
legyen, ha a platform változik.

## Felépítés

| Fájl | Mi |
| --- | --- |
| `server.py` | MCP szerver egyetlen `ping` toollal. A nevét és „eredetét" env-ből kapja (`PROBE_NAME`, `PROBE_ORIGIN`), így két példány futhat — a válaszból derül ki, melyik ér el a lapig. A `ping` hívásonként növekvő számlálót ad vissza, tehát a cache-elt és a friss válasz megkülönböztethető. |
| `probe.html` | A mérőoldal: lépésenként mutatja, hol akad el (`window.claude` → `use("mcp")` → `listTools()` → `callTool`), és kiírja a nyers hibakódokat. |

## Újramérés

```sh
# 1. venv (a GUI-ból indított folyamathoz abszolút python-út kell)
cd probe && uv venv && uv pip install mcp

# 2. regisztráció mindkét helyre, külön néven
claude mcp add gg-probe-code \
  -e PROBE_NAME=gg-probe-code -e PROBE_ORIGIN=claude-code \
  -- "$PWD/.venv/bin/python" "$PWD/server.py"

# a Claude Desktop configjába (~/Library/Application Support/Claude/
# claude_desktop_config.json) az mcpServers alá:
#   "gg-probe-app": {
#     "command": "<abszolút>/.venv/bin/python",
#     "args": ["<abszolút>/server.py"],
#     "env": {"PROBE_NAME": "gg-probe-app", "PROBE_ORIGIN": "claude-desktop"}
#   }
# — előtte másold le a configot, és az app újraindítás után veszi fel
```

Utána a `probe.html`-t publikáld Artifactként ezzel a manifesttel:

```json
{"mcp": {"servers": [
  {"server": "host:gg-probe-code", "tools": ["ping"]},
  {"server": "host:gg-probe-app",  "tools": ["ping"]}
]}}
```

- **A deploy elutasítja** → a blokkoló megvan, nincs változás.
- **Átmegy** → nyisd meg a Claude appban, az oldal megmondja, melyik
  regisztráció érhető el. Innentől a [../docs/mcp-plan.md](../docs/mcp-plan.md)
  folytatható.

## Takarítás

```sh
claude mcp remove gg-probe-code
# + a gg-probe-app bejegyzés törlése a Desktop configból
```

A `.venv/` gitignore-olt.
