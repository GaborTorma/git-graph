---
name: headless-publish-retired
description: Kivezetett út (2026-10-01) — Artifact-publikálás headless claude -p-vel: buktatók és időmérések, ha egyszer mégis session nélkül kellene
metadata:
  type: project
---

Mérve 2026-09-30-án (Claude Code 2.1.285); a `publish_page()` és a launchd agent 2026-10-01-én
kikerült, a session publikál ([[publish-from-session]]). Buktatók, sorrendben:

1. `-p "/git-graph"` nem fut le (`num_turns: 0`): a slash command helyi parancsként nyelődik el,
   promptként kell kérni.
2. `-p` módban az Artifact tool alapból KI (`sdk_default_off`); opt-in: `CLAUDE_CODE_ARTIFACT=1`. A
   Desktop session shelljéből `CLAUDE_CODE_ENTRYPOINT=claude-desktop` öröklődik, ezért ott nélküle is
   ment. A modell válasza a saját toolkészletéről megbízhatatlan — az init-esemény `tools` listája a
   mérvadó (`--output-format stream-json --verbose`).
3. Friss sessionben az első publish elutasítás → előbb `Artifact read`.
4. 444 toollal lassú. Karcsú: `--strict-mcp-config` + `ENABLE_CLAUDEAI_MCP_SERVERS=false` (~30 tool),
   `--setting-sources project` (init 0,3 s). A `--strict-mcp-config` egyedül az Artifactot is kivette;
   a `--tools` szűkítés MCP mellett ártott; `--tools Artifact` `Read` nélkül nem publikál.
5. Az Artifact kapuja a policy-lekérdezés után nyílik (~0,8 s); karcsú indulásnál 10-ből 6 futás
   publikált. Megoldás: `--input-format stream-json`, hiányzó toolnál `interrupt` és újrakérdezés
   0,3 s-onként ugyanabban a folyamatban.
6. Csak végigolvasott fájlt publikál.

Idők a `Published` válaszig: skill-en át 20–78 s; direkt prompt 7,5–11,5 s; karcsú + stream-json +
kapu-poll, Sonnet low 5,6–6,2 s; meleg session 2,9–3,3 s (tétlenül ~270 MB RAM). 200 KB-os lap
frissítése ~50 s. A Sonnet low a leggyorsabb megbízható modell; a `medium` effort nem gyorsabb.

**Why:** a session publikálása egyszerűbb, és nem kell hozzá háttérfolyamat.

**How to apply:** csak akkor vedd elő, ha újra session nélküli publikálás kell; előtte mérd újra, a
CLI azóta változhatott ([[dig-before-declaring-limits]]).
