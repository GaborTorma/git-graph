---
name: artifact-publish
description: Az aktuális repó élő, Git Graph stílusú Artifact oldalát publikálja, ha még nincs, vagy a lapja elavult, majd megnyitja — meglévőt frissít, nem hoz létre duplikátumot. Használd, ha a Fejlesztő a repó Artifactját frissíteni / feltölteni akarja, vagy /git-graph:artifact-publish-t ír.
allowed-tools: Bash(git-graph:*), mcp__claude-artifacts__get_artifact, mcp__claude-artifacts__publish_files, mcp__claude-artifacts__read_declaration, mcp__claude-artifacts__declare_capabilities, mcp__ccd_view__show_pane
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
paraméterekkel (a `files` és a `capabilities` értékét változatlanul add át). Ha a publish-t
a platform elutasítja, kövesd az elutasítás utasítását. A
`git-graph … --published <URL>` hívással írd vissza az URL-t. A sor utolsó
lépése (`show_pane`) a 3. lépés: a publikálás magától nem nyitja meg.

### 3. Megnyitás

Hívd a `mcp__ccd_view__show_pane`-t `pane: "artifact"`-tal: ez a sessionben
publikált Artifactot hozza elő. Ha ebben a sessionben nem publikáltál, és van
`Artifact` eszközöd, előbb nyisd meg azzal (`action: "open"`, `url`: az URL);
ha nincs, a válaszban a link nyitja meg.

### 4. Jelentsd vissza

Egy rövid mondat + a link: frissítés volt, új oldal, vagy már naprakész volt.
