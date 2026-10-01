---
allowed-tools: Bash(gg:*), Artifact
description: Az aktuális repó élő, Git Graph stílusú Artifact oldalát publikálja (ha kell) és megnyitja — meglévőt frissít, nem hoz létre duplikátumot.
---

## Feladat

Az Artifact **élő**: adat nincs benne, a Claude appban megnyitva a gépen futó
`gg --mcp`-ből olvas. Feltölteni csak akkor kell, ha még nincs, vagy a lap
sablonja (a git-graph kódja) változott — ezt a `gg --publish` dönti el
(változatlan lapnál nem tölt fel). Te csak futtatod és megnyitod.

> Ha fut a `gg --serve` (launchd), az ismert repók Artifactját magától is
> karbantartja — ez a parancs a kézi, azonnali út.

### 1. Publikálás

Futtasd: `gg --publish`. Ha `HIBA:`-val tér vissza, idézd szó szerint, és állj meg.

### 2. Megnyitás

A kimenet `✓` sorában ott az Artifact URL-je. Nyisd meg az Artifact eszközzel
(`action: "open"`, `url`: ez az URL) — nem publikálsz vele, csak megmutatod.

### 3. Jelentsd vissza

Egy rövid mondat + a link: frissítés volt, új oldal, vagy már naprakész volt
(„nincs mit feltölteni"). Ha az oldal azt írja, hogy nem éri el a gépen futó
git-graph-ot, mondd meg: az `install.sh --live` után a Claude appot egyszer újra
kell indítani.

Ne írj összegzést a gráf tartalmáról: az oldal magáért beszél.
