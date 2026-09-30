---
allowed-tools: Bash(gg:*), Artifact
description: Az aktuális repó commit-gráfját Git Graph stílusú Artifact oldalként publikálja — meglévőt frissít, nem hoz létre duplikátumot.
argument-hint: "[commit-limit, alap: a teljes history]"
---

## Feladat

A publikálást a `gg --publish` végzi (headless claude, a lap a repón kívül,
`~/.git-graph/<slug>/index.html`): meglévő Artifactot frissít, ha nincs,
létrehozza, változatlan tartalomnál nem tölt fel. Te csak futtatod és
megnyitod.

> Ha fut a `gg --serve` (launchd), az Artifact magától is frissül változás
> után — ez a parancs a kézi, azonnali út.

### 1. Publikálás

Futtasd: `gg --publish` — ha a `$ARGUMENTS` egy szám, `gg --publish --limit <szám>`.
Egy nagy repó 20–50 mp is lehet (a feltöltő modell végigolvassa a lapot).

Ha `HIBA:`-val tér vissza, idézd szó szerint, és állj meg.

### 2. Megnyitás

A kimenet `✓` sorában ott az Artifact URL-je. Nyisd meg az Artifact eszközzel
(`action: "open"`, `url`: ez az URL) — nem publikálsz vele, csak megmutatod.

### 3. Jelentsd vissza

Egy rövid mondat + a link: frissítés volt, új oldal, vagy már naprakész volt
(„nincs mit feltölteni"), és hány commit van rajta.

Ne írj összegzést a gráf tartalmáról: az oldal magáért beszél.
