---
name: page-modules-blob-linking
description: A lap ES-moduljait a page_code blob-URL-ekre köti — ezért nincs körkörös és dinamikus import, az export csak olvasható; a betöltő ↔ page_code szerződés a LOADER_API
metadata:
  type: project
---

- A blob-URL-hez relatív út nem oldható fel → a modulok a függőségeik után kapnak blob-URL-t, az
  importjuk útja a függőségük URL-jére cserélődik (`page_modules`, `PAGE_BOOT`).
- Ezért: körkörös import nem lehet (az alsóbb modul felfelé callbackkel szól, pl.
  `computeFresh(render)`); csak a sor eleji `import … from './x.js'` alak, dinamikus `import()` nem; a
  lapra csak a `main.js`-ből elérhető modul kerül. Az export kívülről csak olvasható, a közös állapotot
  a gazdája setterrel írja (`setData`, `setExpanded`, …). Az eseménykezelők sorrendje a betöltésé (pl.
  a `details` Escape-je a `keyboard`-é előtt).
- A `LOADER_API` csak akkor lép, ha a betöltő és a `page_code` megállapodása változik; eltérésnél a
  `page_code` hibával adja vissza a teendőt, a betöltő kiírja. A betöltő nem írhatja felül a
  `body`-t: a platform a `<title>`-t is oda teszi.
- A telepítés a `page/js/` minden modulját másolja, a forrásból eltűntet törli (`page_files`). A
  0.14-es szerver a `page/page.js` hiányában magától nem frissít; a következő session hookja telepíti
  az újat.

**Why:** a kód élőben jön, újrapublikálás nélkül ([[artifact-csp]], [[artifact-holds-no-data]]).

**How to apply:** új modul az importjával kerül be, lista nélkül; a Check (`scripts/check-page.mjs`)
a hiányzó exportot és a szintaxist fogja.
