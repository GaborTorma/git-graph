---
name: no-redundant-icons
description: "git-graph chipeken ne ismételj ikont, ami a chipből már kiderül (pl. branch-chip távolság-szakaszán nincs újabb branch-ikon)"
metadata:
  node_type: memory
  type: feedback
  originSessionId: cf7247b5-7763-471b-afd3-48522b80fcc1
  modified: 2026-10-05T08:03:14.793Z
---

Egy chipen belül ne tegyél ki olyan ikont, amit a chip maga már jelez. Példa: a branch-chip `↑a ↓b` (alapághoz mért) szakasza ikon nélküli, mert a chip már ág; a felhő-szakasz (`☁ ↑c ↓d`) kap ikont, mert az más viszonyt jelöl.

**Why:** 2026-10-05-én a Fejlesztő kérte („mivel az egy branch és amúgy is branch-et jelenítünk meg, így oda nem kell ikon — máshol is ezt az elvet használd”).

**How to apply:** új chip-elem vagy szakasz tervezésekor kérdezd meg: kiderül-e már a chip típusából / meglévő ikonjából? Ha igen, csak a szám/szöveg menjen ki. Kapcsolódik: [[no-commit-icon]]
