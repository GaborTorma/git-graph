---
name: branch-base-origin-head
description: Az ágak távolsága az origin/HEAD céljához mérve, nem a reflog forrás-ágához (szándékos); az ág gazdája a worktree-k HEAD-reflogjából; a worktree-k sorrendje a születésük
metadata:
  type: project
---

- A `branch_tracks` (`meta.tracks`) egyetlen `for-each-ref`: `base` az `origin/HEAD` céljához
  (`%(ahead-behind:…)`, git 2.41+, régebbin ágankénti `rev-list`), `up` az upstreamhez, a remote-only
  ágnak `local` a helyi párjához.
- Döntés: a forrás-ágat (reflog) szándékosan nem használjuk — az ágak alja mindig az `origin/main`-en
  van.
- Az ágválasztó a worktree-k HEAD-reflogjából csoportosít (`logs/HEAD`, `checkout: moving … to <ág>`):
  az ág azé a worktree-é, ahol utoljára ki volt véve (`branch_owners`; csak fájlt olvas). Törölt
  worktree reflogja vele megy → az ága gazdátlan, a fő checkouté. Leválasztott HEAD:
  [[app-worktrees-json]].
- A hozzáadott worktree-k a létrehozásuk sorrendjében (`worktree_created`: az admin-mappa születési
  ideje) — a git név szerinti ábécét adna.

**Why:** a workflow-ban minden branch a `main`-ből indul; a reflog forrás-ága a törlődő reflogokkal
elvész.

**How to apply:** távolság-számításnál ne vezesd be a reflogos forrás-ágat; ha mégis kellene,
kérdezz.
