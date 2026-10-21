---
name: scroll-step-rows
description: Görgetés commitonként (stepRows), animáció nélkül — a CSS scroll-snap egy kattanással több sort ugrott, az animáció darabos volt; a coasting a simító egérszoftverek lendületét szűri
metadata:
  type: project
---

- Görgetni commitonként lehet (`stepRows`): egy kattanás egy commit, animáció nélkül, a sor a
  napfejléc alá igazodik.
- A CSS scroll-snap ezt nem tartotta: egy kattanással több sort ugrott. Az animált lépés darabosnak
  tűnt.
- A simító egérszoftverek (BetterMouse) fordulás után még a régi irányú lendületet küldik. A
  `coasting` ezt szűri, különben fordulásnál ide-oda ugrál.

**Why:** a két egyszerűbb út (scroll-snap, animáció) kipróbálva rossz volt.

**How to apply:** görgetésnél ne térj vissza scroll-snapre vagy animációra; a `tests/page/` méri a
`stepRows` lépését.
