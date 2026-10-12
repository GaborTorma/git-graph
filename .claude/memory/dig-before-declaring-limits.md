---
name: dig-before-declaring-limits
description: "A Fejlesztő nem fogadja el a \"nem lehet\" választ felszínes ellenőrzés után — előbb mérés és mélyebb utánajárás"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 4a807cd1-3c66-4a4a-8d3f-95f10b1b5b47
  modified: 2026-09-30T17:04:23.437Z
---

Mielőtt kimondod, hogy valami nem megoldható vagy nem gyorsítható, járj utána
mélyebben: CLI-kapcsolók, env-változók (akár a telepített bináris stringjeiből),
init-események, mérés idővonallal. Az eredményt számokkal add át.

**Why:** 2026-09-30, git-graph headless Artifact-publikálás: kétszer is
kimondtam egy korlátot („nem lehet megadni, mi töltődjön be", „ennél nem
gyorsabb"), a Fejlesztő mindkétszer visszatolta — és mindkétszer igaza lett
(`--strict-mcp-config` + `ENABLE_CLAUDEAI_MCP_SERVERS=false`, majd meleg
session: 20 s → 3 s).

**How to apply:** korlát kimondása előtt legalább egy kísérlet a megkerülésére;
ha tényleg korlát, mutasd meg a bizonyítékot (hibaüzenet, kódrészlet, mérés).
