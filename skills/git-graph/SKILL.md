---
name: git-graph
description: Az aktuális repó élő, Git Graph stílusú Artifact oldalát publikálja (ha kell) és megnyitja — meglévőt frissít, nem hoz létre duplikátumot. Használd, ha a Fejlesztő a repó commit-gráfját, ágait, history-ját akarja látni, vagy /git-graph-ot ír.
allowed-tools: Bash(gg:*), Artifact
---

## Feladat

Az Artifact **élő**: adat nincs benne, a Claude appban megnyitva a gépen futó
`gg --mcp`-ből olvas. Feltölteni csak akkor kell, ha még nincs, vagy a lap
sablonja (a git-graph kódja) változott — ezt a `gg --publish` dönti el. A
publikálást te végzed (az Artifact API-t csak a modell éri el).

> A session indulásakor a hook ugyanezt kéri, ha kell — ez a parancs a kézi,
> azonnali út.

### 1. Kell-e publikálni?

Futtasd: `gg --publish`. Ha `HIBA:`-val tér vissza, idézd szó szerint, és állj meg.

- `✓ Az Artifact naprakész…` → a sor végén az URL; ugorj a 3. lépésre.
- `PUBLIKÁLD: …` → 2. lépés.

### 2. Publikálás

Hajtsd végre a `PUBLIKÁLD:` sor lépéseit sorban, pontosan a megadott
paraméterekkel (a `capabilities` értékét változatlanul add át). Ha a publish-t
a platform elutasítja, kövesd az elutasítás utasítását. A végén a
`gg … --published <URL>` hívással írd vissza az URL-t. Az épp publikált
Artifactot nem kell külön megnyitni — ugorj a 4. lépésre.

### 3. Megnyitás

Nyisd meg az Artifact eszközzel (`action: "open"`, `url`: az URL) — nem
publikálsz vele, csak megmutatod.

### 4. Jelentsd vissza

Egy rövid mondat + a link: frissítés volt, új oldal, vagy már naprakész volt.
Ha az oldal azt írja, hogy nem éri el a gépen futó git-graph-ot, mondd meg: a
plugin telepítése után a Claude appot egyszer újra kell indítani (az app csak
induláskor olvassa a configját).

Ne írj összegzést a gráf tartalmáról: az oldal magáért beszél.
