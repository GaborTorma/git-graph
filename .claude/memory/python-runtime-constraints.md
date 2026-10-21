---
name: python-runtime-constraints
description: Miért 3.9-kompatibilis a Python, miért nincs függvényen belüli import, és miért gitio.REPO — az app /usr/bin/python3-mal, cserélődő zipből futtat
metadata:
  type: project
---

- Az app a `git-graph --mcp`-t `/usr/bin/python3`-mal indítja (a homebrew-s Python egy frissítéssel
  eltűnhet) → 3.9-kompatibilis kód; a ruff célverziója is 3.9.
- A csomag minden modulja induláskor betöltődik (a `cli` mindet importálja): a stabil zip a futó
  szerver alatt cserélődhet, egy későbbi import már az új zipből olvasna → függvényen belüli import a
  csomagból nem lehet ([[stable-copy-install]]).
- A `REPO` a `gitio` modulszintű globálisa, a szerver hívásonként más repót szolgálhat ki (a lap
  slugja szerint). Váltás `set_repo`-val (a `_REMOTES` cache-t is nullázza), olvasás `gitio.REPO`-ként
  — egy `from .gitio import REPO` a betöltéskori értéket tartaná meg. A stdio-kiszolgálás soros, lock
  nem kell; a `changes` szála explicit repóval dolgozik, a globálist nem érinti.

**Why:** a CLAUDE.md „Git és Python” gotchái ezekre épülnek.

**How to apply:** új modulnál: import a fájl tetején, 3.9-es szintaxis, repó-hozzáférés
`gitio.REPO`-n át.
