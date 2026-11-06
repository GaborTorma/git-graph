---
name: dev-install-after-change
description: Kész lapváltozás (commit) után a --dev-install-t az AI futtatja, nem a Fejlesztő teendője
metadata:
  type: feedback
---

Ha egy lapot érintő változás kész (zöld tesztek, commit), a `python3 bin/git-graph --dev-install`-t
az *AI* futtatja le magától, és a válaszban kiírja a futó verziót. A Fejlesztőnek csak a lap
megnézése marad.

**Why:** a Fejlesztő kérte (2026-11-06, #64): „ne nekem add teendőnek a dev install-t, futtasd, ha
kész egy új verzió”.

**How to apply:** minden lapváltozás commitja után futtasd, a Teendő legfeljebb a lap megnézése az
appban. Részletek: [[dev-from-source]].
