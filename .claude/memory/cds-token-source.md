---
name: cds-token-source
description: Az app CDS-tokenjei az ion-dist.asar `--cds-*` CSS-ében vannak, fizzy-lake felülírással; a `--fill-ghost-*` nevek csak az Artifact-keret CSS-e
metadata:
  type: reference
---

Az app pontos token-értékei: `/Applications/Claude.app/Contents/Resources/ion-dist.asar` →
`assets/v1/<hash>.css` (`--cds-*` előtag; 2026-11-ben `c6a992d55-*.css`), a komponensek a
`shared-frame-*.js`-ben. Az app a fizzy-lake témát futtatja (`data-cds-fizzy-lake="color panels type"`),
ez írja felül az alap CDS-t — ezt kell olvasni. A név nélküli `--fill-ghost-hover` stb. csak az
Artifact/widget keret CSS-ében van (más téma), az félrevezet. Kicsomagolni egy kis Python
asar-olvasóval lehet (fejléc-JSON a fájl elején), futtatás nélkül.

Mért értékek (comfortable, világos / sötét): fill-ghost-hover 5 % fekete / 7,5 % fehér,
fill-ghost-selected 10 % / 15 %; a ghost Button fizzyben hoverre és nyitva `fill-button-ghost-hover`
(10 % / 7,5 %) — a #64 spec szándékosan a ghost-hover / ghost-selected párost választotta.
Menu: gutter 6 px, sarok 14 px (a lap 4 / 12-t használ); Menu.Separator 1 px, 10 px / 4 px;
GroupLabel 13/17, 500, text-muted; Switch md 36×20, sm 32,4×18, xs 28,8×16; xs ikongomb 24 px, 6 px sarok.
Önálló `Select` komponens nincs: a lenyíló trigger ghost Button + CaretDown.

Kapcsolódik: [[cds-icon-sizes]], [[artifact-no-anthropic-sans]].
