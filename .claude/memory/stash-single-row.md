---
name: stash-single-row
description: A stash egy sor a bázisán (mint a VS Code Git Graph-ban) — ezért ALL_BUT_STASH a log, és a stash-ek a git stash list-ből jönnek, egyetlen szülővel
metadata:
  type: project
---

- A `refs/stash` commitja merge-szerű (szülők: bázis, index-commit, `-u`-nál a követetlen fájlok
  gyökér-commitja); a `log --all` mindhármat sorként, külön sávval hozta.
- Ezért a `log` és a `rev-list` `ALL_BUT_STASH`-sel fut (`--exclude=refs/stash --all`). A stash-ek a
  reflogjukból jönnek (`git stash list`, a régebbiek is), egyetlen szülővel (`^1`), a dátumuk szerint,
  de legkésőbb a bázisuk elé beszúrva (`insert_stashes`).
- Fájllista és diff a bázishoz (`--diff-merges=first-parent`). A `-u`-val félretett követetlen fájlok
  a `^3`-ban vannak, új fájlként kerülnek mellé (`untracked_stashed`; a `file_diff` is onnan olvas).
- A gazdája az a worktree, amelyik az ágát kivette (az üzenetből: `On <ág>: …`), különben a fő
  checkout. Az ágszűrőben akkor marad, ha az ága a szűrtek közt van és a bázisa látszik. A hozzáadott
  worktree stash-ei a worktree oszlopai után kerülnek (`worktree_lanes_last`).
- Egy régebbi stash eldobása a `refs/stash`-t nem mozdítja: az ujjlenyomatban a `stash list`, az
  előszűrőben a `logs/refs/stash` jelez.

**Why:** a VS Code Git Graph elrendezését követjük; a nyers stash-commit három sort és sávot csinált.

**How to apply:** új `log` / `rev-list` hívás `ALL_BUT_STASH`-sel, nem `--all`-lal.
