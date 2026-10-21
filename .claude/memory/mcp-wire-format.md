---
name: mcp-wire-format
description: A lap MCP-kliensének alakjai — listTools() paraméter nélkül {servers:[…]}-t ad, a tools/call eredménye a payload; a GUI-ból indított szerver minimális PATH-tal fut
metadata:
  type: project
---

- `listTools()` paraméter nélkül hívandó, és `{servers: [{server, authStatus, tools}]}`-t ad, nem
  `{tools: […]}`-t. Elsőre rosszul íródott; a típusdefiníció olvasása fogta meg.
- A `tools/call` válaszban a `content[0].text` egy JSON string, `structuredContent` nincs. A
  capability `result.payload`-ja ezt parse-olja → a lapon a `payload`-ot olvasd, ne a `content`-et.
- A Claude app a szervert minimális PATH-tal indítja (`PATH=/usr/bin:/bin`-nel ellenőrizve) →
  abszolút interpreter-út kell, és a git valódi binárisa ([[git-poll-cost]]).

**Why:** a platform típusdefiníciói és a doksi itt eltérhetnek; az első implementáció ezeken bukott el.

**How to apply:** a `page/js/mcp.js` és a `page/js/types.d.ts` ezt az alakot követi; kétségnél a
runtime típusdefinícióját olvasd, ne a doksit.
