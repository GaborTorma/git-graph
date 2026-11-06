---
name: codemirror-gotchas
description: A lap CodeMirror-diffjének buktatói — margós blokk-widget elcsúsztatja a sorokat, a widget estimatedHeight-je ≠ DOM-magasság egymás mellett végtelen újramérés, a lap ⌘F/Esc capture-kezelője elveszi a billentyűt, a panel újrarajzolása a nézetet költözteti
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
- **A merge `scanLimit`-je**: a `MergeView` és az `unifiedMergeView` alap `diffConfig`-ja
  `{scanLimit: 500}`. Ha a változások együtt ennél nagyobbak (pl. 13+/11− sor egy 450 soros fájlban),
  a diff feladja, és a fájl nagy részét egy blokkban változottnak jelöli. A `diffConfig: {scanLimit:
  1e9, timeout: 1500}` (`DIFF_CONFIG`) pontos, a 2 MB-os fájlt az időkorlát védi.
- **`estimatedHeight` ≠ a widget valódi magassága** (2026-11-06, #63): a saját rés (`Gap`) a merge
  27 px-es becslését vallotta be, a CSS-ből 26 px lett. Egymás mellett (`MergeView`) ettől az igazítás
  minden képkockában újramért (~60 frissítés/s, a lap sosem nyugodott meg); egymás alatt nem látszott.
  Javítás: a widget DOM-ja a becsült magasságot kapja (`GAP_H`). A jel: a tesztek `settle()`-je
  (`window.__quiet`) időtúllépéssel bukik.
- **Saját mentés visszhangja**: a mentés előtt indult lekérdezés régi lemezállapota nem külső
  változás — a `CodeDiff.seen` a látott / saját írású hasheket szűri.

**Why:** mind órákig tartó, a tesztben egy sorral elcsúszó vagy elnyelt billentyűként jelentkező hiba volt.

**How to apply:** CM-widget stílusánál ne használj margót, és az `estimatedHeight` a DOM-magassággal egyezzen (rögzítsd mindkettőt egy konstanssal); új lapszintű billentyűkezelő a `.cm-editor`
célpontot hagyja ki; a kódnézetet ne építsd újra adatcserénél ([[page-modules-blob-linking]]).
