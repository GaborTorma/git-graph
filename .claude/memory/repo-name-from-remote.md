---
name: repo-name-from-remote
description: A repó neve az origin remote-ból jön, nem a mappanévből (auto-bpm → WristBPM) — ez adja az Artifact címét is
metadata:
  type: project
---

- `git remote get-url origin` → basename, `.git` levágva; a mappanév csak tartalék. A mappa eltérhet:
  az `auto-bpm` mappában a repó `WristBPM`.
- Ez adja az Artifact címét (`Git Graph (<repó>)`). A cím a publikált `<title>`-ből jön, a lap JS-e
  nem írja felül.

**Why:** a mappanév helyi döntés, a repó neve a remote-ban él.

**How to apply:** repónév → `origin`; minden út a fő checkoutra képződik le (`main_checkout`).
