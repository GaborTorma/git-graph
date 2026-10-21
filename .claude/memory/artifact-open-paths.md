---
name: artifact-open-paths
description: Már megnyitott lapra a modell Artifact open-je csak kártyát tesz ki — a panelt az open utáni show_pane nyitja; külső folyamat az Artifact-ablakot nem nyitja meg
metadata:
  type: project
---

- Egy sessionben már egyszer megnyitott lapot sem a mod, sem a modell `open`-je nem nyit ki újra: a
  modellé csak kártyát tesz a beszélgetésbe, a modé semmit (mérve 2026-10-09).
- Bezárt artifact-panelnél (`get_layout`: `open_panes: []`) az `open` után hívott
  `mcp__ccd_view__show_pane` (`pane: "artifact"`) megnyitja a panelt, a lappal — akkor is, ha a lapot
  nem ez a session publikálta (mérve 2026-10-10, Claude Code 2.1.296).
- Külső folyamat (CLI, hook) a Claude Artifact-ablakát nem nyitja meg: a régi `--open` a rendszer
  böngészőjében nyitott, a `/artifacts` lista `o` billentyűje is.

**Why:** ezért hívja a `/git-graph:artifact-open` és az `/git-graph:artifact-publish` az `open` után a
`show_pane`-t is (csak a desktop appban van; ahol nincs, kimarad).

**How to apply:** lap megnyitása: `open` + `show_pane`. Modból csak a session indulásakor nyit
([[mod-limits]]).
