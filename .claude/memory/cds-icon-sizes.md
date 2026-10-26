---
name: cds-icon-sizes
description: Az app ikonmérete sűrűségenként (comfortable: 20 px a menüben), és az Anthropicons-font több verziója a gyorsítótárban
metadata:
  type: reference
---

Az app Icon komponense (`shared-frame-*.js`, `NY`): xs 12 / sm 16 / md 20 px; az alapméret és az
`auto` a sűrűségtől függ (`W8()`: comfortable → `md`, különben `sm`; CSS: `--cds-icon` 1.25rem
comfortable-ben). A menütétel ikonja `size:"auto"` → comfortable-ben 20 px; a pipa
`Check`, `auto`, `bold` (strong vonal, `wght` 566,7), `fill-accent` színű. A chip (Badge) és a
gombok saját méretet adnak (16).

**Why:** a lap menüi 16 px-esek voltak, a Fejlesztő észrevette, hogy kisebbek, mint az appban;
a `wght` képlete: `E1(stroke, opsz, px)` a `x2.wght` lo/hi tábláján 400–700 közt.

**How to apply:** új menüikon a `ICONS_MD`-be (`icons.js`, az `anthropicons.json`
`icons_md` / `icons_md_bold` készletéből). A `scripts/anthropicons.py` újrafuttatásakor: a
gyorsítótárban több ikonfont-verzió van (395–418 glifa, eltérő rajzzal: a régiben pl. a `Folder`
belső vonalas, a `Filter` csúszkás). A claude.ai CSS-e (Artifact-keret) a régit hivatkozta, az
asztali app eszköztára már az újat mutatta (2026-10-26) — a legtöbb glifájú fontot válaszd, a
névtáblához a legbővebb bundle-t (amelyikben a `ListCard` is benne van). A felhős branch ikon
(`branchCloud`) ebből számolt rajz: font frissítésekor a Cloud és a GitBranch szerint újra kell
számolni. Kapcsolódik: [[artifact-no-anthropic-sans]]
