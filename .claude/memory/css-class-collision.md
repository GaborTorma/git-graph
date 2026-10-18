---
name: css-class-collision
description: A lap egyetlen stíluslapján a rövid, generikus osztálynév összeér — a .head egyszer a HEAD-badge-re ült; azóta ref-* névtér
metadata:
  type: project
---

A táblázat-fejléc `.head` szabálya ráült a `class="badge head"` elemre: a HEAD-badge `display:grid` +
`min-width:860px` + `text-transform:uppercase` értéket kapott, teljes szélességű sávvá nyúlt, és
kinyomta a commit-üzenetet. Azóta a badge-variánsok `ref-*` névtérben vannak.

**Why:** egy stíluslap van, minden modul osztálya egy térben él.

**How to apply:** új osztály névtérrel (`ref-*`, `md-*`, …); rövid, generikus név (`.head`, `.item`,
`.title`) nem.
