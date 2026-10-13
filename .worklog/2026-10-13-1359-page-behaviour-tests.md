# A lap viselkedési tesztje és típusellenőrzése

A lapnak (page/) eddig csak összekötés-ellenőrzése volt; most a Check headless
Chromiumban is lefuttatja, és `tsc --checkJs`-sel típusellenőrzi a moduljait. A
harness (`tests/page/harness.py`) a valódi betöltőt tölti be egy kamu
`window.claude` MCP-klienssel, amely a hívásokat a valódi `git-graph --mcp`-nek adja
tovább, egy eldobható, ötnapos fixture-repóval. Az első tesztek a gráf pöttyeit mérik
a sorokhoz (napfejléc, kinyitott panel, átméretezés után), a `fitRows` töréspontjait
(480 px, a 320 px-es alsó határ, `.three`) és a `stepRows` lépését (egy kattanás egy
commit, a sor a napfejléc alá kerül).

A lap a legtöbbet változó rész, és a gráf-, töréspont- és görgetési hibák eddig csak
az appban derültek ki. Szándékosan elrontott kóddal (pötty-Y, lépésküszöb, töréspont)
a tesztek pirosra váltanak.

A Playwright és a TypeScript fejlesztői eszköz marad (`uv run --with`, `pnpm dlx`,
verzióra rögzítve), a repóba függőség nem kerül. A harness Pythonban van, mert így a
fixture és a szerver a meglévő `tests/helpers.py`-ra épül. A típusok a
`page/js/types.d.ts`-ben (a `graph_data` alakja, `GIT_GRAPH`); a lekérdezések alapból
`HTMLElement`-et adnak, máshol JSDoc-cast. A típusok két hiányzó mezőt is
megmutattak (`appBranch`, `tracks.local`). A gyökér `tsconfig.json`-t a Claude Code
írja a mod típusaihoz, ezért a lapé a `page/` alatt van.

Nyitva maradt: a `tsc` nem szigorú módban fut (`strictNullChecks`-szel ~300 hiba
lenne), és a WIP-sáv, a diff-panel, a szűrők még nincsenek lefedve.

- [`[2ad32e8b]`](https://github.com/GaborTorma/git-graph/commit/2ad32e8ba5c3f555b24cd3a5f9d29b0eaac095f0) · build(page): type-check page/js with tsc --checkJs
- [`[5cc8e472]`](https://github.com/GaborTorma/git-graph/commit/5cc8e47270dc98263520aa78c263bbe852574362) · test(page): add headless playwright harness for page behaviour
