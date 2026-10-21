---
name: host-bridge-limits
description: A host:git-graph híd korlátai — csak a Claude appban, tulajdonosnak, a claude_desktop_config.json szerverével; az app felülírja a configot; readOnlyHint; watchTool ≥30 s; hol látszanak a hívások
metadata:
  type: project
---

A lap `callTool("host:git-graph", …)`-lal éri el a gépen futó `git-graph --mcp`-t. 2026-09-30 óta
működik (contract 0.2.66); előtte a deploy `422: capabilities.mcp: unavailable`-lal utasította el, a
doksi pedig önmagának ellentmondott.

- Csak a Claude appban (böngészőfülben `server_not_connected`), csak a tulajdonosnak.
- Csak a Claude app configjában (`~/Library/Application Support/Claude/claude_desktop_config.json`)
  felvett szerver számít; a `claude mcp add`-os nem is deklarálható.
- Az app a configot csak induláskor olvassa, és futás közben felülírja a memóriabeli változattal
  (beállítás-mentéskor) — a közben beírt bejegyzés elveszett. Beírás után azonnal app-újraindítás.
- A lap capability-deklaráció nélkül nem kap MCP-t (`use("mcp")` → `null`), és azt hiszi, nem az
  appban fut. A deklaráció a session szervere nélkül is átmegy, csak figyelmeztet (*„no successful
  call to it was observed in this session”*).
- Nem read-only toolra az app hívásonként megerősítést kérhet → minden tool `readOnlyHint: true`, a
  `settings` is.
- A `watchTool` `refetchInterval`-ja ~30 s-ra padlózott → a lap `callTool`-lal hív
  ([[host-bridge-long-poll]]).
- A szerverfolyamatok app-szintűek (`cwd: /`, az app indulásakor indulnak); egy folyamat az app összes
  git-graph lapját szolgálja. A host a hívással csak a tool nevét és argumentumait küldi (se `_meta`,
  se session).
- Hibakeresés: az app MCP-naplója (`~/Library/Logs/Claude/mcp-server-git-graph.log`) a host-híd
  `tools/call`-jait **nem** naplózza. A fő napló (`main.log`) igen:
  `[ArtifactHostTools] call { tool, outcome, durationMs, confirm }`. A `not_in_manifest` ott sem
  látszik: azt a keret dobja.

**Why:** a CLAUDE.md „MCP és host-híd” gotchái ezekre a mérésekre épülnek.

**How to apply:** a lap működését a Claude appban nézd, a böngésző nem elég; configírás után
app-újraindítás. Új tool → [[tools-list-changed]]; nagy válasz → [[host-bridge-response-size]];
rejtett keret → [[host-bridge-hidden-frame]].
