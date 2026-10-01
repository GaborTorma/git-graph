# Lenyitható fájlsorok inline diffel

A commit-részletek panel fájlsorai lenyithatók: a sorra kattintva alatta
megjelenik a fájl diffje, a Claude app diff-nézetének mintájára — sorszám,
`+`/`−`, zöld/piros háttér, a cserélt soroknál a megváltozott szavak erősebb
kiemeléssel, a hunkok közt „N változatlan sor”. Ha a diff-doboz legalább 1000 px
széles, side-by-side nézetre vált (balra a régi, jobbra az új oldal). Az
Uncommitted sornál a HEAD-hez képesti diff látszik, követetlen fájlnál a teljes
tartalom, élőben frissülve.

Eddig a panel csak a fájlok nevét és a `+/−` számot mutatta; a változás
tartalmához a GitHubra kellett menni, és ott is csak pusholt commitnál.

A diff nem került a `graph_data`-ba — az Artifact- és a Browser panel-lap
2 mp-enként tölti, a méretének kicsinek kell maradnia. A lap lenyitáskor kéri,
fájlonként: a `gg --serve` új `/diff` útvonaláról, az Artifactban az új
`file_diff` MCP toolból (felvéve a `PUBLISH_CAPS`-be is). A szó-szintű kiemelést
a Python számolja `difflib`-bel, így marad a stdlib-only elv. Mivel a bemenet a
lapról jön, a sha csak hex lehet (különben `--opció`-ként menne a gitnek), és
fájlt közvetlenül csak akkor olvasunk, ha a git követetlennek mondja. A két nézet
közti váltás CSS container query, újrarenderelés nélkül; a gráf ehhez kapott egy
`ResizeObservert` — átméretezéskor eddig sem rajzolódott újra.

Nyitva maradt: az Artifact-mód élesben, a Claude appban nincs kipróbálva — ahhoz
a merge után az app újraindítása kell (az app által indított `gg --mcp` a régi
kódot futtatja), és az Artifactok újrapublikálása (a `gg --serve` újraindításkor
megteszi). Egy fájlból legfeljebb 3000 sor látszik.

- [`[221fd4a8]`](https://github.com/GaborTorma/git-graph/commit/221fd4a862f01e01d8e0ee02405d5f4aa2289397) · feat(ui): expand file rows into inline diffs
- [`[c2eb445c]`](https://github.com/GaborTorma/git-graph/commit/c2eb445c12f023af14b858d601cb79a8b57ecc54) · feat(ui): show file diffs side by side when the panel is wide enough
