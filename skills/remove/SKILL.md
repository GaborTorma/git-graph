---
name: remove
description: A git-graph Artifactjainak törlése és a repók git-graph nyomainak eltakarítása — a plugin eltávolítása ELŐTT. Használd, ha a Fejlesztő a git-graph-ot el akarja távolítani, vagy /git-graph:remove-ot ír.
allowed-tools: Bash(gg:*), Artifact, AskUserQuestion
---

## Feladat

A `claude plugin uninstall` a gépi részt magától leszereli, de az Artifactokat
nem törli: azok a claude.ai-on maradnak, és a repók `.git/config`-jában is ott
az URL-jük. Ez a skill ezt takarítja el — a plugin eltávolítása előtt.

### 1. Lista

Futtasd: `gg --artifacts`. Soronként `<repó>\t<URL>`. Ha üres, mondd meg, hogy
nincs mit törölni, és ugorj az 5. lépésre.

### 2. Megerősítés

Mutasd a listát táblázatban (repó neve, URL), és kérdezd meg az
`AskUserQuestion`-nel: **Mind törlése** / **Mégse**. A törlés visszavonhatatlan,
ezt mondd ki. Mégse → állj meg.

### 3. Törlés

Repónként, sorban:

1. `Artifact`, `action: "delete"`, `url`: a sor URL-je. A platform minden
   törlést külön jóváhagyat — ez rendben van.
2. Ha a törlés sikerült, vagy az Artifact már nem létezik: `gg --forget <repó>`.
   Ha a Fejlesztő elutasította vagy más hiba jött: a repót hagyd ki (a
   kulcsai maradnak), és menj tovább.

A `gg --forget` a repó `git-graph.*` kulcsait, helyi lapjait és
regiszterbejegyzését törli, és kikapcsolja az automatikus publikálást — a futó
szerver így nem hoz létre új Artifactot.

### 4. Ellenőrzés

Futtasd újra: `gg --artifacts`. Ami maradt, azt sorold fel okkal.

### 5. Jelentsd vissza

Hány Artifact törlődött, mi maradt. Utolsó sorként a plugin eltávolítása:

```bash
claude plugin uninstall git-graph@git-graph
```

Mondd meg: a háttérszerver ~2 percen belül leszereli a többit, és az appot
csak utána érdemes újraindítani.
