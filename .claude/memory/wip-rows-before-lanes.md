---
name: wip-rows-before-lanes
description: A WIP ál-sorok a lane-kiosztás ELŐTT kerülnek a commitok közé, mert az edges sorindexeket használ — a meta viszont a valódi commitokból készül
metadata:
  type: project
---

- Worktree-nként legfeljebb két ál-sor: felül a nem stage-elt (`*uncommitted:<slug>`, az indexhez
  mérve, a követetlen fájlokkal), alatta a stage-elt (`*staged:<slug>`, a HEAD-hez mérve). Láncban
  állnak: a felső szülője az alsó, az alsóé a worktree HEAD-je. A slugból tudja a `file_diff`, melyik
  mappát és oldalt diffelje; élő worktree-é kell legyen.
- Az `assign_lanes` magától kezeli őket, de az `edges` sorindexeket használ → az ál-sorokat a
  kiosztás előtt kell beszúrni. A `meta` a valódi commitokból készül, különben az „N commit látszik”
  hazudna.
- A szerzőjük a worktree `user.name`-je, az idejük a fájlok `mtime`-ja. A saját worktree-é a fix
  `#pending` sávban ül (`drawPending`), a többié a listában, az ideje szerint, sosem a HEAD-je alá.

**Why:** utólag beszúrt sor elcsúsztatja az élek indexeit.

**How to apply:** új ál-sortípusnál ugyanígy: beszúrás → `assign_lanes`; a számlálók a valódi
commitokból.
