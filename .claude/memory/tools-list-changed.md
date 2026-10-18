---
name: tools-list-changed
description: Az app a szerver tool-listáját a kapcsolódáskor gyorstárazza — restart után az új tool not_in_manifest, amíg nem jön notifications/tools/list_changed
metadata:
  type: project
---

Mérve 2026-10-12-én (contract 0.2.66): a `settings` tool `restart`-tal (`os.execv`) került a futó
szerverbe, a betöltő az új tool-listával publikálva, a lap hívása mégis elbukott:

```
not_in_manifest: host:git-graph does not offer a tool named "settings" on this device
```

- A keret `listTools()`-a a manifest és a szerver listájának metszete; a `tools/list` az app
  MCP-naplója szerint csak a kapcsolódáskor ment ki.
- Újrapublikálás és a keret újranyitása nem segít, az app újraindítása igen.
- `notifications/tools/list_changed`-re az app 1 ms-on belül újra lekéri. A kézfogásban
  `listChanged: true`; a `restart` a `GIT_GRAPH_RESTARTED` env-vel (`RESTARTED_ENV`) szól az új
  folyamatnak, az küldi az értesítést.

**Why:** enélkül egy plugin-frissítés új toolja app-újraindításig nem hívható.

**How to apply:** új tool → a `PUBLISH_CAPS` tool-listájába is, új betöltő publikálása, és a
`list_changed` útnak működnie kell ([[server-self-update]]).
