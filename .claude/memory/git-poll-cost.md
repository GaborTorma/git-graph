---
name: git-poll-cost
description: A repó-állapot és a worktree-nkénti WIP mért költsége — párhuzamosan 5 worktree ~50 ms; a /usr/bin/git xcrun-shim hívásonként ~6 ms; a követetlen fájlok keresése a drága
metadata:
  type: project
---

Mérve 2026-10-04-én és 2026-10-06-án, eldobható klónokon, `--no-optional-locks`-szal (25 kör
mediánja). Egy kör: `for-each-ref` + `worktree list` + worktree-nként `status --porcelain`,
`diff --numstat HEAD`, `rev-parse`:

| Worktree-k | git-graph (~60 fájl) | 10 582 fájlos repó |
| --- | --- | --- |
| 1 | 56 ms | 148 ms |
| 3 | 127 ms | 412 ms |
| 5 | 202 ms | 678 ms |
| 5, párhuzamosan | 53 ms | 326 ms |

- A nagy repón a `status` ~90 ms, ebből ~60 ms a követetlen fájlok keresése (`-uno`: 24–26 ms).
- A `repo_state` 52 → 17 ms (git-graph, 3 worktree) és 139 → 94 ms (nagy repó) lett: a valódi git
  bináris (`git_bin`; a macOS `/usr/bin/git` `xcrun`-shim, 12 → 6 ms/hívás), a párhuzamos
  `for-each-ref` és `status`, és a `diff --numstat` elhagyása (a ns-os mtime is jelzi az újabb
  szerkesztést).
- `stat`-előszűrő (worktree-nként `HEAD`, `index`, `logs/HEAD`, a `packed-refs` és a ref-mappák):
  0,025 ms.
- Harnessben, a lapon mérve: ág létrehozása / törlése ~0,4 s, fájlszerkesztés 0,8–2,2 s alatt látszik.

**Why:** a `changes` long-poll 2 s-onként teljes állapotot számol ([[focused-worktree-design]]); a
büdzsé ebből jön.

**How to apply:** új git-hívás a pollozott úton → mérd meg nagy repón is; a git a `git_bin`-nel fusson,
ne a PATH-ról. Kapcsolódik: [[git-no-optional-locks]].
