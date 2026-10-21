---
name: artifact-single-frame
description: Egy Artifactnak az app egyetlen keretet tart, és minden sessionben azt mutatja; az Artifact open a #horgonyt és a ?query-t eldobja; a republish újratölt
metadata:
  type: project
---

Mérve 2026-10-04-én (Claude Code 2.1.286, contract 0.2.67), naplózó próbalappal és műszerezett
szerverrel:

- **Egy keret vándorol** a sessionök panelje között (ugyanaz a betöltés-azonosító három sessionben),
  nem töltődik újra. Csak a mérete más (a panelek szélessége), de ez törékeny jel: azonos szélesség,
  ablak-átméretezés.
- **`#horgony` és `?query` nem jut át**: az `Artifact open …#wt-x` se betöltést, se `hashchange`-et nem
  hoz, a panel bezárása (`close_pane`) után sem. Az `open` válasza és a panel URL-je is horgony nélküli.
- **Az újrapublikálás újratölti** a nyitott keretet (horgony nélkül).
- A host a hívással semmit nem küld a sessionről, a szerverpéldány app-szintű ([[host-bridge-limits]]).
- A platform a `window.name`-ben tartja a bootstrapját (`{"hot":…,"usable":…}`). A `location.reload()`-ot
  a `window.name`, a horgony (`replaceState`), a `sessionStorage` és a `history.state` túléli; egy
  újraépült keret friss `window.name`-mel indul. A `sessionStorage` a keretek között közös.

**Why:** ezért nem tudható a „saját” worktree a linkből vagy a keretből, és ezért van repónként egy
Artifact ([[focused-worktree-design]]).

**How to apply:** sessionfüggő állapotot ne a lapra, a linkbe vagy a keret méretébe építs; a forrás
az app session-fájljai és naplója ([[app-focus-sources]]).
