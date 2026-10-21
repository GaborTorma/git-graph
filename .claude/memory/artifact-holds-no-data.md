---
name: artifact-holds-no-data
description: Döntés — az Artifact csak betöltő, adat és kód nélkül; a beágyazott adatú lap frissítése nagy repón ~50 s volt
metadata:
  type: project
---

- A beágyazott adatú lap minden változásnál újra feltöltendő volt; nagy repón ~50 s, mert a feltöltő
  modell az élő és a helyi példányt is végigolvassa ([[publish-from-session]]).
- 2026-09-30 óta vékony lap: az adatot a host-hídon kéri (`graph_data`), 2026-10-02 óta a kódot is
  (`page_code`). A vékony lap feltöltése 5–8 s.
- Az appban, valódi híddal (2026-09-30): `fingerprint` 262 ms, `graph_data` 414 ms; változástól a
  kirajzolásig ~3 s (azóta a long-poll ~50 ms, [[focused-worktree-design]]).
- A betöltőt csak a saját, a repónév vagy a capability-lista változásakor kell feltölteni (a hash
  ezekből számolódik).

**Why:** ez a lényeg, nem optimalizálás: a kódfrissítés újrapublikálás nélkül él, a publikálás gyors.

**How to apply:** adatot vagy kódot ne tegyél vissza a lapba, a betöltőbe.
