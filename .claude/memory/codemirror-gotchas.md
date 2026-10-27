---
name: codemirror-gotchas
description: A lap CodeMirror-diffjének buktatói — margós blokk-widget elcsúsztatja a sorokat, a lap ⌘F/Esc capture-kezelője elveszi a billentyűt, a panel újrarajzolása a nézetet költözteti
metadata:
  type: project
---

Kiderült a #56 (CodeMirror-diff, WIP-szerkesztés) közben, 2026-10-27-én (CodeMirror 6.43 / merge 6.12):

- **Margó a blokk-widgeten**: a `.cm-collapsedLines`-on (a változatlan rés) álló `margin` miatt a
  CodeMirror magasságtérképe elcsúszott — a `posAtCoords` egy sorral lejjebb adott (a dupla kattintás
  a 40. sor helyett a 41.-re tette a kurzort). A CM a blokkot margó nélkül méri: a widgetre csak
  padding/border kerülhet.
- **A lap capture-kezelői**: a `filters.js` dokumentum-szintű, capture-fázisú ⌘F / Esc kezelője
  `preventDefault`-tal elvette a billentyűt a CodeMirror keresőjétől. Ami `.cm-editor`-ból jön, azt a
  lap kezelői (filters, keyboard, details) békén hagyják; a CM a sajátjait `preventDefault`-tal jelzi.
- **Újrarajzolás**: a `render()` minden adatcserénél újraépíti a commit-panelt. A kódnézet
  (`CodeDiff`) ezért kulcsonként él (`codeViews`), és a gyökere átköltözik az új dobozba; ha már ott
  van, nem nyúlunk hozzá (különben a görgetés és a fókusz elugrik).
- **Saját mentés visszhangja**: a mentés előtt indult lekérdezés régi lemezállapota nem külső
  változás — a `CodeDiff.seen` a látott / saját írású hasheket szűri.

**Why:** mindhárom órákig tartó, a tesztben egy sorral elcsúszó vagy elnyelt billentyűként jelentkező hiba volt.

**How to apply:** CM-widget stílusánál ne használj margót; új lapszintű billentyűkezelő a `.cm-editor`
célpontot hagyja ki; a kódnézetet ne építsd újra adatcserénél ([[page-modules-blob-linking]]).
