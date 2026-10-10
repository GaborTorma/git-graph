---
name: artifact-open
description: Az aktuális repó élő, Git Graph stílusú Artifact oldalát megnyitja — nem publikál. Használd, ha a Fejlesztő a repó commit-gráfját, ágait, history-ját akarja látni, vagy /git-graph:artifact-open-t ír.
allowed-tools: Bash(git-graph:*), Artifact
---

## Feladat

Az Artifact **élő**: adat nincs benne, a Claude appban megnyitva a gépen futó
`git-graph --mcp`-ből olvas. Ez a parancs csak megnyitja; feltölteni a
`/git-graph:artifact-publish` tölti fel.

### 1. Van-e naprakész Artifact?

Futtasd: `git-graph --publish`. Ha `HIBA:`-val tér vissza, idézd szó szerint, és állj meg.

- `✓ Az Artifact naprakész…` → a sor végén az URL; 2. lépés.
- `PUBLIKÁLD: …` → **ne hajtsd végre a lépéseit.** Egy mondatban mondd meg: a
  repónak még nincs Artifactja, vagy a lapja elavult — a `/git-graph:artifact-publish`
  feltölti és megnyitja. Állj meg.

### 2. Megnyitás

Nyisd meg az Artifact eszközzel (`action: "open"`, `url`: az URL) — nem
publikálsz vele, csak megmutatod.

### 3. Jelentsd vissza

Egy rövid mondat + a link. Ha az oldal azt írja, hogy nem éri el a gépen futó
git-graph-ot, mondd meg: a plugin telepítése után a Claude appot egyszer újra
kell indítani (az app csak induláskor olvassa a configját).

Ne írj összegzést a gráf tartalmáról: az oldal magáért beszél.
