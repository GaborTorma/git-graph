---
name: git-no-optional-locks
description: Minden git-hívás --no-optional-locks — a git status különben index.lock-ot vesz, és a Fejlesztő commitja elbukik; ezért a core.fsmonitor sem használható
metadata:
  type: project
---

- A `git status` frissíti az indexet, ehhez `index.lock`-ot vesz. A gyakori állapotlekérés így a
  Fejlesztő saját git-parancsait akasztja meg — egy commit tényleg elbukott rajta.
- A `core.fsmonitor` a nagy repó `status`-át 27 ms-ra vinné, de csak úgy, ha a tokenjét az indexbe
  írja (írás nélkül 154 ms) → az `index.lock` miatt nem járható (mérve 2026-10-06, #29).
- Buktató: friss worktree-ben vagy klónban az index stat-adatai még nem frissültek, és
  `--no-optional-locks` mellett a pollozás sosem írja vissza. Így minden kör újrahasheli a fájlokat
  (~450 ms worktree-nként), amíg egy zároló git-parancs (bármelyik `git status` a Fejlesztőtől) nem
  frissíti az indexet.

**Why:** a script sosem módosíthat repót (CLAUDE.md, „Minden git-hívás olvas”).

**How to apply:** új git-hívás a `gitio`-n át, `--no-optional-locks`-szal. Friss klónon mért
lassúság előtt egy sima `git status`. Költségek: [[git-poll-cost]].
