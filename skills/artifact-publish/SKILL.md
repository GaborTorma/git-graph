---
name: artifact-publish
description: Az aktuális repó élő, Git Graph stílusú Artifact oldalát publikálja, ha még nincs, vagy a lapja elavult, majd megnyitja — meglévőt frissít, nem hoz létre duplikátumot. Használd, ha a Fejlesztő a repó Artifactját frissíteni / feltölteni akarja, vagy /git-graph:artifact-publish-t ír.
allowed-tools: Bash(git-graph:*), Artifact
---

## Feladat

Az Artifact **élő**: adat nincs benne, a Claude appban megnyitva a gépen futó
`git-graph --mcp`-ből olvas. Feltölteni csak akkor kell, ha még nincs, vagy a lap
sablonja (a git-graph kódja) változott — ezt a `git-graph --publish` dönti el. A
publikálást te végzed (az Artifact API-t csak a modell éri el).

### 1. Kell-e publikálni?

Futtasd: `git-graph --publish`. Ha `HIBA:`-val tér vissza, idézd szó szerint, és állj meg.

- `✓ Az Artifact naprakész…` → a sor végén az URL; ugorj a 3. lépésre.
- `PUBLIKÁLD: …` → 2. lépés.

### 2. Publikálás

Hajtsd végre a `PUBLIKÁLD:` sor lépéseit sorban, pontosan a megadott
paraméterekkel (a `capabilities` értékét változatlanul add át). Ha a publish-t
a platform elutasítja, kövesd az elutasítás utasítását. A
`git-graph … --published <URL>` hívással írd vissza az URL-t, és a sor utolsó
lépésével nyisd meg (a publikálás magától nem nyitja meg) — ugorj a 4. lépésre.

### 3. Megnyitás

Nyisd meg az Artifact eszközzel (`action: "open"`, `url`: az URL).

### 4. Jelentsd vissza

Egy rövid mondat + a link: frissítés volt, új oldal, vagy már naprakész volt.
