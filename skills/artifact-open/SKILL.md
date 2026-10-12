---
name: artifact-open
description: Az aktuális repó élő, Git Graph stílusú Artifact oldalát megnyitja, és ha elavult, előbb frissíti — újat nem hoz létre. Használd, ha a Fejlesztő a repó commit-gráfját, ágait, history-ját akarja látni, vagy /git-graph:artifact-open-t ír.
allowed-tools: Bash(git-graph:*), Artifact, mcp__ccd_view__show_pane
---

## Feladat

Az Artifact **élő**: adat nincs benne, a Claude appban megnyitva a gépen futó
`git-graph --mcp`-ből olvas. A session indulásakor a plugin modja magától
megnyitja, ha a lap beállítás-menüjében be van kapcsolva az automatikus
megnyitás; ez a parancs a kézi nyitásra való (pl. bezárt panel után, vagy ha
az automatikus megnyitás ki van kapcsolva). Új Artifactot nem hoz létre: azt a
`/git-graph:artifact-publish` teszi.

### 1. Van-e mit megnyitni?

Futtasd: `git-graph --open-url`. Ha `HIBA:`-val tér vissza, idézd szó szerint, és állj meg.

- Egy URL → a lap naprakész, 3. lépés.
- `PUBLIKÁLD: …` → a lap elavult, 2. lépés.
- Üres kimenet → egy mondatban mondd meg: a repónak még nincs Artifactja — a
  `/git-graph:artifact-publish` létrehozza és megnyitja. Állj meg.

### 2. Frissítés

Hajtsd végre a `PUBLIKÁLD:` sor lépéseit sorban, pontosan a megadott
paraméterekkel (a `capabilities` értékét változatlanul add át). Ha a publish-t
a platform elutasítja, kövesd az elutasítás utasítását. A
`git-graph … --published <URL>` hívással írd vissza az URL-t. A sor utolsó
lépése (`open`) a 3. lépés.

### 3. Megnyitás

Nyisd meg az Artifact eszközzel (`action: "open"`, `url`: az URL) — nem
publikálsz vele, csak megmutatod. Utána, ha elérhető, hívd a
`mcp__ccd_view__show_pane`-t `pane: "artifact"`-tal: egy sessionben már
megnyitott lapra az `open` csak kártyát tesz a beszélgetésbe, a `show_pane`
hozza elő a panelt.

### 4. Jelentsd vissza

Egy rövid mondat + a link (és ha frissíteni kellett, azt is). Ha az oldal azt írja, hogy nem éri el a gépen futó
git-graph-ot, mondd meg: a plugin telepítése után a Claude appot egyszer újra
kell indítani (az app csak induláskor olvassa a configját).

Ne írj összegzést a gráf tartalmáról: az oldal magáért beszél.
