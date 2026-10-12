---
name: no-commit-icon
description: "A git-graph lapon a „commit” (h-alakú, két pöttyös) ikon tilos — sehol ne használd"
metadata:
  node_type: memory
  type: feedback
  originSessionId: cf7247b5-7763-471b-afd3-48522b80fcc1
  modified: 2026-10-04T18:33:22.436Z
---

A régi `commit` ikont (függőleges vonal + kanyar, két teli pötty; a VS Code Git Graph-ból maradt) a lapon sehol nem szabad használni — se leválasztott HEAD-en, se a commit-panel hash-chipjén, se worktree-chipben.

**Why:** 2026-10-04-én a Fejlesztő kifejezetten kérte, hogy felejtsük el; a VS Code Git Graph örökség, nem illik a lap ikonkészletébe.

**How to apply:** ahol jel kellene „ág nélküli HEAD”-re vagy commitra, inkább ikon nélkül (csak `HEAD`, hash), vagy kérdezz. Kapcsolódik: [[no-gitlens-design]]
