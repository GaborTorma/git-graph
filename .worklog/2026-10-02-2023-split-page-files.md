# A lap kódja külön fájlokban

A lap kódja kikerült a `bin/git-graph`-ból a `page/` mappába: `loader.html` (az
Artifact betöltője), `head.html`, `page.css`, `body.html` és `page.js`. A
`page_code` tool és a `build()` ezekből dolgozik, a kimenetük bájtra azonos a
korábbival, így a publikált Artifactokhoz nem kell nyúlni. A stabil másolat
(`~/.git-graph/`) és az önfrissítés a `page/` mappát is viszi. Az új verzió
indulásakor a szerver egyszer beolvassa a lap fájljait, így a saját verziójához
tartozó kódot adja akkor is, ha a hook közben már újat másolt.

A ~850 sor CSS, HTML és JS eddig Python-stringekben élt. Nem volt rá
szerkesztő-támogatás és lint, a JS-t csak kivágva lehetett szintaxis-ellenőrizni,
a diffek pedig keveredtek a szerver kódjával. A következő redesign épp ezt a
részt növeli.

Egy frissítési csapda miatt került be a `repair_page`. A már futó 0.10.x-es
szerver önfrissítéskor csak a scriptet és a manifestet másolja, a `page/`-et
nem. Az utána induló új verzió ezért a plugin mappájából pótolja a lap
fájljait, ha hiányoznak.

Új ellenőrzések kerültek be, a repóba nem kerül miattuk függőség:
- ruff 3.9-es célverzióval, mert az app `/usr/bin/python3`-mal indít;
- Biome a `page/` JS-ére, CSS-ére és HTML-jére, a pusztán stílusbeli szabályok
  nélkül;
- stdlib füstteszt az MCP szerverre: a working tree-ből, a stabil másolatból, és
  lap nélküli stabil másolatból frissítve.

A Biome két valódi hibát talált: a `body.html` utolsó `div`-je lezáratlan volt,
és a Graph-fejléc ikonjáról hiányzott a `role`.

- [`[3c56d9c8]`](https://github.com/GaborTorma/git-graph/commit/3c56d9c87c343612b5f96c4ce39dbead298c64cb) · refactor: move the page code from the script into page/ files
