---
name: graph-rows-layout
description: A gráf-SVG a sorok MÖGÖTT van — a drawGraph() a DOM-ból méri a sorok Y-ját, és a sor-kiemelés csak a .row-in-re mehet
metadata:
  type: project
---

- A `drawGraph()` a sorok Y-ját a DOM-ból olvassa (`offsetTop + offsetHeight / 2`), nem sorszám ×
  magasságból: a napfejléc és a kinyitott commit-panel az alattuk lévő sorokat lejjebb tolja, a sor
  magassága pedig a `fitRows` szerint változik (`ROW_H`, a kétsoros 52, a tördelt badge-es `.three`
  legalább 71 px). Ezért minden DOM-változás után újra kell hívni (nyitás, zárás, Escape, `render`).
- A pöttyöket az `#lanes` SVG a sorok mögé rajzolja; az átlátszatlan `:hover` / kiválasztott háttér
  eltakarta őket. Ezért a sor bal paddingje a gráf szélessége, és a háttér a belső sávra (`.row-in`)
  megy. Az SVG-t a sorok fölé emelni nem megoldás: a `.rows` (`z-index: 2`) saját rétegkontextust nyit,
  így a benne lévő `.details` sosem kerülhet a testvér `#lanes` fölé — a kinyitott panelen átlógnának
  a vonalak.
- A panel `margin-left: var(--graph-w)`: a gráf-oszlop szabadon marad, a vonal mellette fut végig.

**Why:** mindkettő valódi hiba volt (elcsúszott, illetve eltakart pöttyök).

**How to apply:** új sor-háttér a `.row-in`-re; DOM-változás után `drawGraph()`. A `tests/page/` méri
a pöttyök helyét.
