---
name: artifact-forget
description: A git-graph Artifact törlése és a repó git-graph nyomainak eltakarítása (`git-graph --forget`) — az aktuális repóé vagy az összesé (a plugin eltávolítása előtt). Használd, ha a Fejlesztő egy repó Artifactját meg akarja szüntetni, a git-graph-ot el akarja távolítani, vagy /git-graph:artifact-forget-et ír.
allowed-tools: Bash(git-graph:*), Bash(git config:*), Artifact, AskUserQuestion
---

## Feladat

Az Artifactot törli a claude.ai-ról, és a `git-graph --forget`-tel a repó
`git-graph.*` kulcsait, helyi lapját és regiszterbejegyzését. A `--forget` a repó
automatikus publikálását is kikapcsolja (`git-graph.autoPublish=false` a
`.git/config`-ban): a session hookja abban a repóban nem kér új Artifactot. A kézi
`/git-graph:artifact-publish` visszakapcsolja.

A `claude plugin uninstall` a gépi részt magától leszereli, de az Artifactokat nem
törli — eltávolítás előtt ezért az összeset kell.

### 1. Lista

Futtasd: `git config --get git-graph.artifact` (az aktuális repó URL-je; üres, ha
nincs) és `git-graph --artifacts` (soronként `<repó>\t<URL>`, az összes ismert).
Ha a lista üres, mondd meg, hogy nincs mit törölni, és állj meg.

### 2. Megerősítés

Kérdezd meg az `AskUserQuestion`-nel; a kérdésben mondd ki, hogy a törlés
visszavonhatatlan:

- **Csak ez a repó** — az opció leírásában a repó neve és URL-je; csak ha az
  aktuális repónak van URL-je.
- **Mind (N)** — a leírásban: az összes ismert repóé; a plugin eltávolítása előtt ez kell.
- **Mégse**.

Csak egyértelmű választásra törölj: Mégse, elutasítás vagy bármi más → állj meg.

### 3. Törlés

A kiválasztott soronként:

1. `Artifact`, `action: "delete"`, `url`: a sor URL-je. A platform minden törlést
   külön jóváhagyat — ez rendben van.
2. Ha a törlés sikerült, vagy az Artifact már nem létezik: `git-graph --forget <repó>`.
   Ha a Fejlesztő elutasította vagy más hiba jött: hagyd ki (a kulcsai maradnak), és
   menj tovább.

### 4. Ellenőrzés

**Mind** esetén futtasd újra: `git-graph --artifacts`. Ami maradt, azt sorold fel okkal.

### 5. Jelentsd vissza

Hány Artifact törlődött, mi maradt, és hogy ezekben a repókban az automatikus
publikálás ki van kapcsolva (visszakapcsolás: `/git-graph:artifact-publish`).

**Mind** esetén utolsó sorként a plugin eltávolítása:

```bash
claude plugin uninstall git-graph@git-graph
```

Mondd meg: a Claude app által indított git-graph ~1 percen belül leszereli a
többit (ha az app nem fut, a következő indulása után), és az appot csak utána
érdemes újraindítani.
