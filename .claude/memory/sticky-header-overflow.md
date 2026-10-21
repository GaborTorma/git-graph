---
name: sticky-header-overflow
description: overflow-x: auto a szülőn az overflow-y-t is auto-vá teszi, és a sticky fejléc a belső konténerhez tapad — ezért fix fejsáv + egyetlen görgethető régió
metadata:
  type: project
---

A `position: sticky; top: 41px` fejléc a belső konténerhez tapadt, nem a laphoz, és az első sor fölé
csúszott: a szülő `overflow-x: auto`-ja az `overflow-y`-t is `auto`-vá tette. Megoldás: VS
Code-panel elrendezés — fix fejsáv és egyetlen görgethető régió.

**Why:** a sticky elem a legközelebbi görgető őséhez tapad.

**How to apply:** ragadós elemet (pl. a `.day-group` napfejlécét) csak az egyetlen görgető régióban
használj; köztes elemre ne tegyél `overflow`-t.
