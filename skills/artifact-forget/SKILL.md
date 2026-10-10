---
name: artifact-forget
description: Az aktuális repó git-graph Artifactjának törlése és a repó git-graph nyomainak eltakarítása (`git-graph --forget`). Használd, ha a Fejlesztő ennek a repónak az Artifactját meg akarja szüntetni, vagy /git-graph:artifact-forget-et ír. Az összes repóé, eltávolítás előtt: /git-graph:forget-all-artifacts.
allowed-tools: Bash(git-graph:*), Bash(git config:*), Artifact, AskUserQuestion
---

## Feladat

Az aktuális repó Artifactját törli a claude.ai-ról, és a `git-graph --forget`-tel
a repó `git-graph.*` kulcsait, helyi lapját és regiszterbejegyzését. A
`--forget` a repó automatikus publikálását is kikapcsolja
(`git-graph.autoPublish=false` a `.git/config`-ban): a session hookja ebben a
repóban nem kér új Artifactot. A kézi `/git-graph:artifact-publish`
visszakapcsolja.

### 1. URL

Futtasd: `git config --get git-graph.artifact`. Ha üres, a repónak nincs ismert
Artifactja: ugorj a 4. lépésre.

### 2. Megerősítés

Mutasd az URL-t, és kérdezd meg az `AskUserQuestion`-nel: **Törlés** / **Mégse**.
A törlés visszavonhatatlan — ezt mondd ki. Mégse → állj meg.

### 3. Törlés

`Artifact`, `action: "delete"`, `url`: az URL. Ha a Fejlesztő elutasította vagy
más hiba jött (kivéve: az Artifact már nem létezik), állj meg — a kulcsok maradnak.

### 4. Felejtés

Futtasd: `git-graph --forget`.

### 5. Jelentsd vissza

Egy rövid mondat: törlődött-e Artifact, és hogy ebben a repóban az automatikus
publikálás ki van kapcsolva (visszakapcsolás: `/git-graph:artifact-publish`).
