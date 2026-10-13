# A lap kódja ES-modulokra bontva

A lap 2600 soros `page/page.js`-e 30 valódi ES-modulra bomlott a `page/js/` alatt,
belépő a `main.js`. A modulok a régi szakaszokat követik: állapot, gráf, sorok,
commit-panel, diff, markdown-diff, szintaxis-színezés, ágválasztó, szűrők,
billentyűzet, élő frissítés stb. A legnagyobb 247 sor. A lap viselkedése nem változott.

A lap a markdown-renderrel tovább nőtt, és még bővülni fog: egy fájlban a változások
egymásra torlódtak, a részek közti függés pedig nem látszott.

A nehézség a betöltés volt: a betöltő a lap kódját `import(blob:)`-bal futtatja, és
egy blob-URL-hez a `./x.js` relatív import nem oldható fel. Ezért a `page_code` a
belépőből elérhető modulokat a függőségi sorrendjükben adja, és egy kis indító-modul
mindegyiknek blob-URL-t ad, az importjaik útját pedig a függőségük URL-jére cseréli.
A publikált betöltő és a `LOADER_API` nem változott, újrapublikálás nem kellett. Ebből
két szabály következik: körkörös import nem lehet (az alsóbb modul felfelé callbackkel
szól), és a közös állapotot a gazdamodul setterrel írja, mert az ES-modul exportja
kívülről csak olvasható.

Az összekötést a Check Node-ban ellenőrzi, futtatás nélkül (`scripts/check-page.mjs`).
A telepítés a `page/js/` minden modulját másolja, a forrásból eltűntet törli. A
kipróbálás egy böngészős próbapadon a valódi betöltővel ment, utána `--dev-install`-lal
az appban is.

Nyitva maradt: a 0.14-es szerver a `page/page.js` hiányában magától nem frissít, az
új kódot a következő session hookja telepíti. A régi `~/.git-graph/page/page.js` ott
marad, de már senki nem olvassa.

- [`[d9b43cc8]`](https://github.com/GaborTorma/git-graph/commit/d9b43cc88386e1e7941b2961fe52f108216bdb96) · refactor(page): split page.js into ES modules linked by page_code
