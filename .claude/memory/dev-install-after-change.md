---
name: dev-install-after-change
description: Kész lapváltozás (commit) után a --dev-install-t az AI futtatja, nem a Fejlesztő teendője
metadata:
  type: feedback
---

Ha egy lapot érintő változás kész (zöld tesztek, commit), a `python3 bin/git-graph --dev-install`-t
az *AI* futtatja le magától, és a válaszban kiírja a futó verziót. A lap megnézése sem Teendő:
azt a Fejlesztő magától megteszi.

**Why:** a Fejlesztő kérte (2026-11-06, #64): „ne nekem add teendőnek a dev install-t, futtasd, ha
kész egy új verzió”; és: „Nézd meg a lapot az appban — ez nem teendő, nyilván megnézem az eredményt”.

**How to apply:** minden lapváltozás commitja után futtasd; a válaszba se a dev-install, se a lap megnézése ne
kerüljön Teendőként. Részletek: [[dev-from-source]].
