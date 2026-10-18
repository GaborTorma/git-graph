---
name: hook-publishes-mod-opens
description: A hook publikáltat, a mod nyit meg — mert modból a publish nem megy; sessionönként egyszer nyit (sessions.json); resume, /clear, compact nem zárja be a lapot
metadata:
  type: project
---

- Ha a repónak nincs Artifactja, vagy a lap hashe eltér a `git-graph.artifactHash`-től, a SessionStart
  hook a publikálás lépéseit adja a sessionnek (`publish_steps`). A meglévőt a plugin modja
  (`hooks/register.ts`) nyitja meg a modell nélkül, a session indulásakor: a `git-graph --open-url`
  dönt, a mod `$.tool.call`-lal hívja az `Artifact` `open`-t ([[mod-limits]]).
- Sessionönként egyszer: `~/.git-graph/sessions.json` (`session_id → slug`, 7 nap után törlődik), a
  `source`-tól függetlenül — a `resume`, a `/clear` és a `compact` nem zárja be a lapot; archiválásra
  nincs hook, a `SessionEnd` app-bezáráskor is fut. Publikáláskor a hook jegyzi be a sessiont: utána a
  modell nyit.
- Kapcsolók a lap fogaskerekén (`settings` tool): automatikus megnyitás repónként
  (`git-graph.autoOpen`; a 0.13 előtti `autoPublish=false` is kikapcsoltnak számít) és automatikus
  publikálás a gépen (`~/.git-graph/settings.json`).
- A hook némán kilép, ha a mappa nem repó (minden sessionben fut, zajt nem csinálhat). Ahol nem fut
  mod (régi kliens), a lap magától nem nyílik meg. Worktree-váltásra nincs hook (0.13 előtt
  `PostToolUse` futott az `Enter`/`ExitWorktree` után).

**Why:** az Artifact API-t csak a modell és a mod éri el; a mod publikálását az auto mód elutasítja,
a modellé a hook kérésére megy.

**How to apply:** publikálás → hook-lépés a sessionnek; megnyitás → mod
([[artifact-open-paths]]). A publikálást ne próbáld modba tenni.
